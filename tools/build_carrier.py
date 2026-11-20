#!/usr/bin/env python3
"""Build the reusable ndp_logo kernel carrier (Level 3.5).

The carrier is a patched copy of the shipped `ndp_logo.ko`. It keeps the
vendor module identity, vermagic and symbol versions, adds a small sysfs
parameter (`/sys/module/ndp_logo/parameters/carrier`), and replaces the
module init/cleanup entries with safe no-ops so the logo driver is not
initialised. The result is non-persistent: unload the module or cold boot.

This tool does not ship or fetch vendor firmware. Pass the `ndp_logo.ko` that
belongs to the TV under test (for example from
`/mtd_apexe/board/modules/ndp_logo.ko` or an extracted `ap0` image).

Requirements: clang with the aarch64 backend, a compatible `ld.lld`, and the
vendor module. The build is refused if the merged module gains an unresolved
symbol, loses a required section, or if clang's KCFI hash does not match the
vendor module's own hash for a known indirect-call prototype.

Examples:
  python3 tools/build_carrier.py --module /path/to/ndp_logo.ko
  python3 tools/build_carrier.py --module /path/to/ndp_logo.ko \
      --output dist/carrier/ndp_logo_carrier.ko
  python3 tools/build_carrier.py --module /path/to/ndp_logo.ko \
      --keep-driver-init
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

NOOP_RET = bytes.fromhex("00008052c0035fd6")
KPARAM_SIZE = 40
KPARAM_OPS_SIZE = 32
KPARAM_PERM_OFFSET = 0x18
KPARAM_PERM_0644 = b"\xa4\x01"
CARRIER_SYMBOLS = ("carrier_set", "carrier_get", "carrier_ops", "__param_carrier")
REQUIRED_SECTIONS = (
    ".text",
    ".init.text",
    ".exit.text",
    ".symtab",
    ".strtab",
    ".gnu.linkonce.this_module",
    "__versions",
    ".modinfo",
    "__param",
)
CFLAGS = [
    "--target=aarch64-linux-gnu",
    "-O2",
    "-ffreestanding",
    "-fno-builtin",
    "-fno-pic",
    "-fno-stack-protector",
    "-fno-asynchronous-unwind-tables",
    "-fno-unwind-tables",
    "-fno-addrsig",
    "-mno-outline-atomics",
]

SHT_SYMTAB = 2
SHT_RELA = 4
SHN_UNDEF = 0
STB_GLOBAL = 1


class BuildError(Exception):
    """A carrier build or validation failure."""


@dataclass(frozen=True)
class Section:
    index: int
    name: str
    type: int
    flags: int
    offset: int
    size: int
    link: int
    info: int
    addralign: int
    entsize: int


@dataclass(frozen=True)
class Symbol:
    index: int
    name: str
    info: int
    shndx: int
    value: int
    size: int


@dataclass(frozen=True)
class Relocation:
    offset: int
    sym_index: int
    type: int
    addend: int


class Elf:
    """Minimal little-endian ELF64 relocatable reader and byte patcher."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.raw = bytearray(self.path.read_bytes())
        self.sections: list[Section] = []
        self._symbols: list[Symbol] | None = None
        self._parse()

    def _parse(self) -> None:
        raw = self.raw
        if len(raw) < 64 or raw[:4] != b"\x7fELF":
            raise BuildError(f"{self.path}: not an ELF file")
        if raw[4] != 2 or raw[5] != 1:
            raise BuildError(f"{self.path}: expected ELF64 little-endian")
        shoff = struct.unpack_from("<Q", raw, 0x28)[0]
        shentsize = struct.unpack_from("<H", raw, 0x3A)[0]
        shnum = struct.unpack_from("<H", raw, 0x3C)[0]
        shstrndx = struct.unpack_from("<H", raw, 0x3E)[0]
        if shentsize < 64 or shnum == 0 or shstrndx >= shnum:
            raise BuildError(f"{self.path}: unsupported section table")
        if shoff + shnum * shentsize > len(raw):
            raise BuildError(f"{self.path}: section table outside file")

        headers = []
        for i in range(shnum):
            headers.append(struct.unpack_from("<IIQQQQIIQQ", raw, shoff + i * shentsize))
        strhdr = headers[shstrndx]
        strtab = raw[strhdr[4]:strhdr[4] + strhdr[5]]

        def cstr(blob: bytes, off: int) -> str:
            if off >= len(blob):
                return ""
            end = blob.find(b"\0", off)
            if end < 0:
                end = len(blob)
            return blob[off:end].decode("utf-8", "replace")

        for i, h in enumerate(headers):
            self.sections.append(
                Section(
                    index=i,
                    name=cstr(strtab, h[0]),
                    type=h[1],
                    flags=h[2],
                    offset=h[4],
                    size=h[5],
                    link=h[6],
                    info=h[7],
                    addralign=h[8],
                    entsize=h[9],
                )
            )
        if len(self.sections) <= 1 or self.sections[0].name != "":
            raise BuildError(f"{self.path}: malformed section table")

    def section(self, name: str) -> Section:
        for sec in self.sections:
            if sec.name == name:
                return sec
        raise BuildError(f"{self.path}: missing section {name!r}")

    def symbols(self) -> list[Symbol]:
        if self._symbols is not None:
            return self._symbols
        symsec = self.section(".symtab")
        strsec = self.section(".strtab")
        if symsec.entsize == 0:
            raise BuildError(f"{self.path}: empty symbol entry size")
        blob = self.raw[strsec.offset:strsec.offset + strsec.size]
        out = []
        for i in range(symsec.size // symsec.entsize):
            off = symsec.offset + i * symsec.entsize
            st_name, st_info, _st_other, st_shndx, st_value, st_size = struct.unpack_from(
                "<IBBHQQ", self.raw, off
            )
            out.append(
                Symbol(
                    index=i,
                    name=self._cstr(blob, st_name),
                    info=st_info,
                    shndx=st_shndx,
                    value=st_value,
                    size=st_size,
                )
            )
        self._symbols = out
        return out

    @staticmethod
    def _cstr(blob: bytes, off: int) -> str:
        if off >= len(blob):
            return ""
        end = blob.find(b"\0", off)
        if end < 0:
            end = len(blob)
        return blob[off:end].decode("utf-8", "replace")

    def find_symbol(self, name: str) -> Symbol:
        matches = [s for s in self.symbols() if s.name == name and s.shndx != SHN_UNDEF]
        if not matches:
            raise BuildError(f"{self.path}: symbol {name!r} not found")
        if len(matches) == 1:
            return matches[0]
        global_matches = [s for s in matches if (s.info >> 4) == STB_GLOBAL]
        if len(global_matches) == 1:
            return global_matches[0]
        raise BuildError(f"{self.path}: ambiguous symbol {name!r}")

    def undefined_symbols(self) -> set[str]:
        return {
            s.name
            for s in self.symbols()
            if s.shndx == SHN_UNDEF and s.name
        }

    def relocations_for(self, section_name: str) -> list[Relocation]:
        target = self.section(section_name).index
        out = []
        for sec in self.sections:
            if sec.type != SHT_RELA or sec.info != target:
                continue
            if sec.entsize == 0:
                raise BuildError(f"{self.path}: empty relocation entry size")
            for i in range(sec.size // sec.entsize):
                off = sec.offset + i * sec.entsize
                r_offset, r_info, r_addend = struct.unpack_from("<QQq", self.raw, off)
                out.append(
                    Relocation(
                        offset=r_offset,
                        sym_index=r_info >> 32,
                        type=r_info & 0xFFFFFFFF,
                        addend=r_addend,
                    )
                )
        return out

    def symbol_bytes(self, name: str, length: int) -> bytes:
        sym = self.find_symbol(name)
        sec = self.sections[sym.shndx]
        start = sec.offset + sym.value
        return bytes(self.raw[start:start + length])

    def kcfi_prefix(self, name: str) -> int:
        sym = self.find_symbol(name)
        if sym.value < 4:
            raise BuildError(f"{self.path}: {name!r} has no KCFI prefix")
        sec = self.sections[sym.shndx]
        off = sec.offset + sym.value - 4
        return struct.unpack_from("<I", self.raw, off)[0]

    def patch_entry(self, name: str, data: bytes) -> None:
        sym = self.find_symbol(name)
        if sym.shndx == SHN_UNDEF:
            raise BuildError(f"{self.path}: {name!r} is undefined")
        sec = self.sections[sym.shndx]
        if sym.value + len(data) > sec.size:
            raise BuildError(f"{self.path}: patch for {name!r} exceeds {sec.name}")
        start = sec.offset + sym.value
        end = start + len(data)
        for rel in self.relocations_for(sec.name):
            if start <= sec.offset + rel.offset < end:
                raise BuildError(
                    f"{self.path}: {name!r} entry overlaps a relocation at "
                    f"{rel.offset:#x} in {sec.name}"
                )
        self.raw[start:end] = data

    def sha256(self) -> str:
        return hashlib.sha256(bytes(self.raw)).hexdigest()


def run(cmd: list[str], what: str) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise BuildError(f"{what} failed ({result.returncode}):\n{detail}")


def find_tool(explicit: str | None, env_name: str, default: str) -> str:
    for candidate in (explicit, os.environ.get(env_name), default):
        if not candidate:
            continue
        found = shutil.which(candidate)
        if found:
            return found
        if Path(candidate).is_file():
            return candidate
    raise BuildError(f"{default} not found; pass it explicitly or set {env_name}")


def compile_object(clang: str, source: Path, output: Path, kcfi: bool) -> None:
    cmd = [clang, *CFLAGS]
    if kcfi:
        cmd.append("-fsanitize=kcfi")
    cmd += ["-c", str(source), "-o", str(output)]
    run(cmd, f"compiling {source.name}")


def link_module(lld: str, module: Path, objects: list[Path], output: Path) -> None:
    cmd = [lld, "-r", "-o", str(output), str(module), *(str(obj) for obj in objects)]
    run(cmd, "linking the carrier into the vendor module")


def verify_kcfi(clang: str, workdir: Path, vendor: Elf, merged: Elf) -> int:
    probe = workdir / "kcfi_probe.c"
    probe.write_text(
        "struct file;\n"
        "long probe_ioctl(struct file *f, unsigned int c, unsigned long a);\n"
        "void *volatile probe_keep = (void *)probe_ioctl;\n"
        "long probe_ioctl(struct file *f, unsigned int c, unsigned long a)\n"
        "{ (void)f; (void)c; (void)a; return 0; }\n",
        encoding="utf-8",
    )
    probe_obj = workdir / "kcfi_probe.o"
    compile_object(clang, probe, probe_obj, kcfi=True)
    expected = Elf(probe_obj).kcfi_prefix("probe_ioctl")
    vendor_hash = vendor.kcfi_prefix("ndp_logo_ioctl")
    if expected != vendor_hash:
        raise BuildError(
            "clang KCFI hash mismatch: "
            f"vendor ndp_logo_ioctl=0x{vendor_hash:08x}, clang=0x{expected:08x}. "
            "Use the vendor toolchain for this firmware."
        )
    for name in ("carrier_set", "carrier_get"):
        if merged.kcfi_prefix(name) == 0:
            raise BuildError(f"carrier {name!r} has no KCFI prefix")
    return expected


def verify_merge(vendor: Elf, merged: Elf) -> None:
    for name in REQUIRED_SECTIONS:
        merged.section(name)

    vendor_undef = vendor.undefined_symbols()
    merged_undef = merged.undefined_symbols()
    added = merged_undef - vendor_undef
    removed = vendor_undef - merged_undef
    if added:
        raise BuildError(f"merged module gained unresolved symbols: {sorted(added)}")
    if removed:
        raise BuildError(f"merged module lost unresolved symbols: {sorted(removed)}")

    vendor_param = vendor.section("__param")
    merged_param = merged.section("__param")
    if merged_param.size != vendor_param.size + KPARAM_SIZE:
        raise BuildError(
            "unexpected __param size: "
            f"vendor={vendor_param.size} merged={merged_param.size}"
        )
    entry = vendor_param.size
    perm_off = merged_param.offset + entry + KPARAM_PERM_OFFSET
    if bytes(merged.raw[perm_off:perm_off + 2]) != KPARAM_PERM_0644:
        raise BuildError("carrier parameter is not mode 0644")

    ops_offset = entry + 0x10
    ops_symbol = None
    for rel in merged.relocations_for("__param"):
        if rel.offset == ops_offset:
            ops_symbol = merged.symbols()[rel.sym_index].name
            break
    if ops_symbol != "carrier_ops":
        raise BuildError(f"carrier parameter ops relocation is {ops_symbol!r}")

    text = merged.section(".text")
    for name in ("carrier_set", "carrier_get"):
        sym = merged.find_symbol(name)
        if sym.shndx != text.index:
            raise BuildError(f"{name!r} is not in .text")
        if sym.size == 0:
            raise BuildError(f"{name!r} has zero size")
    if merged.find_symbol("carrier_ops").size != KPARAM_OPS_SIZE:
        raise BuildError("carrier_ops has an unexpected size")
    if merged.find_symbol("__param_carrier").size != KPARAM_SIZE:
        raise BuildError("__param_carrier has an unexpected size")
    merged.find_symbol("init_module")
    merged.find_symbol("cleanup_module")


def verify_patched(vendor: Elf, merged: Elf) -> None:
    if merged.symbol_bytes("init_module", len(NOOP_RET)) != NOOP_RET:
        raise BuildError("init_module was not patched")
    if merged.symbol_bytes("cleanup_module", len(NOOP_RET)) != NOOP_RET:
        raise BuildError("cleanup_module was not patched")
    if merged.kcfi_prefix("init_module") != vendor.kcfi_prefix("init_module"):
        raise BuildError("init_module KCFI prefix changed")


def build(args: argparse.Namespace) -> int:
    module = Path(args.module).resolve()
    if not module.is_file():
        raise BuildError(f"vendor module not found: {module}")
    source_dir = Path(args.source_dir).resolve()
    carrier_c = source_dir / "carrier.c"
    raw_c = source_dir / "carrier_raw.c"
    for path in (carrier_c, raw_c):
        if not path.is_file():
            raise BuildError(f"carrier source not found: {path}")

    clang = find_tool(args.clang, "CARRIER_CLANG", "clang")
    lld = find_tool(args.lld, "CARRIER_LLD", "ld.lld")
    output = Path(args.output).resolve()

    workdir = Path(tempfile.mkdtemp(prefix="ptv-carrier-"))
    try:
        carrier_obj = workdir / "carrier.o"
        raw_obj = workdir / "carrier_raw.o"
        merged_path = workdir / "merged.ko"
        compile_object(clang, carrier_c, carrier_obj, kcfi=True)
        compile_object(clang, raw_c, raw_obj, kcfi=False)
        link_module(lld, module, [carrier_obj, raw_obj], merged_path)

        vendor = Elf(module)
        merged = Elf(merged_path)
        verify_merge(vendor, merged)
        kcfi_hash = verify_kcfi(clang, workdir, vendor, merged)

        if not args.keep_driver_init:
            merged.patch_entry("init_module", NOOP_RET)
            merged.patch_entry("cleanup_module", NOOP_RET)
            verify_patched(vendor, merged)
            merged_path.write_bytes(merged.raw)

        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_name(output.name + ".tmp")
        tmp.write_bytes(merged.raw)
        os.replace(tmp, output)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print(f"vendor      {module}  sha256 {hashlib.sha256(module.read_bytes()).hexdigest()}")
    print(f"output      {output}  sha256 {hashlib.sha256(output.read_bytes()).hexdigest()}")
    print(f"kcfi        vendor/clang {kcfi_hash:#010x}")
    print("carrier     /sys/module/ndp_logo/parameters/carrier  mode 0644")
    print(f"init        {'vendor (driver init runs)' if args.keep_driver_init else 'no-op (pure carrier)'}")
    print("install     insmod the output, then use tools/carrier_ctl.py")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--module", required=True, help="path to the vendor ndp_logo.ko")
    parser.add_argument("--output", default="dist/carrier/ndp_logo_carrier.ko", help="output module path")
    parser.add_argument(
        "--source-dir",
        default=str(Path(__file__).resolve().parent.parent / "payloads" / "carrier"),
        help="directory holding carrier.c and carrier_raw.c",
    )
    parser.add_argument("--clang", help="clang binary (default: $CC or clang)")
    parser.add_argument("--lld", help="ld.lld binary (default: $LLD or ld.lld)")
    parser.add_argument(
        "--keep-driver-init",
        action="store_true",
        help="keep the vendor logo init/cleanup instead of no-ops",
    )
    args = parser.parse_args(argv)
    try:
        return build(args)
    except BuildError as exc:
        print(f"build_carrier: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
