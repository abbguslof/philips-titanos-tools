#!/usr/bin/env python3
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
import build_carrier  # noqa: E402

SHT_PROGBITS = 1
SHT_SYMTAB = 2
SHT_STRTAB = 3
SHT_RELA = 4
SHF_ALLOC_EXEC = 0x6
STB_GLOBAL = 1
STT_FUNC = 2


def _cstr(*names):
    blob = bytearray(b"\0")
    offsets = {}
    for name in names:
        offsets[name] = len(blob)
        blob += name.encode() + b"\0"
    return bytes(blob), offsets


def _make_elf(with_reloc=False):
    section_names = [
        "",
        ".init.text",
        ".exit.text",
        ".rela.init.text",
        ".rela.exit.text",
        ".symtab",
        ".strtab",
        ".shstrtab",
    ]
    shstrtab, shnames = _cstr(*section_names[1:])
    strtab, strnames = _cstr("init_module", "cleanup_module")

    init_text = bytes(range(16))
    exit_text = bytes(range(16, 32))
    reloc = b""
    if with_reloc:
        reloc = struct.pack("<QQq", 4, 1 << 32, 0)
    symtab = b"".join(
        [
            struct.pack("<IBBHQQ", 0, 0, 0, 0, 0, 0),
            struct.pack(
                "<IBBHQQ",
                strnames["init_module"],
                (STB_GLOBAL << 4) | STT_FUNC,
                0,
                1,
                4,
                0,
            ),
            struct.pack(
                "<IBBHQQ",
                strnames["cleanup_module"],
                (STB_GLOBAL << 4) | STT_FUNC,
                0,
                2,
                4,
                0,
            ),
        ]
    )

    data = bytearray(b"\0" * 64)
    offsets = {}

    def place(name, blob, align=1):
        while len(data) % align:
            data.append(0)
        offsets[name] = len(data)
        data.extend(blob)

    place(".init.text", init_text, 4)
    place(".exit.text", exit_text, 4)
    place(".rela.init.text", reloc, 8)
    place(".rela.exit.text", b"", 8)
    place(".symtab", symtab, 8)
    place(".strtab", strtab)
    place(".shstrtab", shstrtab)
    while len(data) % 8:
        data.append(0)
    shoff = len(data)

    entries = [
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (shnames[".init.text"], SHT_PROGBITS, SHF_ALLOC_EXEC, 0, offsets[".init.text"],
         len(init_text), 0, 0, 4, 0),
        (shnames[".exit.text"], SHT_PROGBITS, SHF_ALLOC_EXEC, 0, offsets[".exit.text"],
         len(exit_text), 0, 0, 4, 0),
        (shnames[".rela.init.text"], SHT_RELA, 0, 0, offsets[".rela.init.text"],
         len(reloc), 5, 1, 8, 24),
        (shnames[".rela.exit.text"], SHT_RELA, 0, 0, offsets[".rela.exit.text"],
         0, 5, 2, 8, 24),
        (shnames[".symtab"], SHT_SYMTAB, 0, 0, offsets[".symtab"],
         len(symtab), 6, 2, 8, 24),
        (shnames[".strtab"], SHT_STRTAB, 0, 0, offsets[".strtab"],
         len(strtab), 0, 0, 1, 0),
        (shnames[".shstrtab"], SHT_STRTAB, 0, 0, offsets[".shstrtab"],
         len(shstrtab), 0, 0, 1, 0),
    ]
    for entry in entries:
        data.extend(struct.pack("<IIQQQQIIQQ", *entry))

    ident = b"\x7fELF" + bytes([2, 1, 1]) + b"\0" * 9
    header = ident + struct.pack(
        "<HHIQQQIHHHHHH",
        1,
        183,
        1,
        0,
        0,
        shoff,
        0,
        64,
        0,
        0,
        64,
        len(entries),
        7,
    )
    data[:64] = header
    return bytes(data)


def _write_fixture(directory, with_reloc=False):
    path = Path(directory) / "fixture.ko"
    path.write_bytes(_make_elf(with_reloc=with_reloc))
    return path


class TestElf(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = _write_fixture(self.tmp.name)
        self.elf = build_carrier.Elf(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sections_and_symbols(self):
        self.assertEqual(self.elf.section(".init.text").size, 16)
        self.assertEqual(self.elf.find_symbol("init_module").value, 4)
        self.assertEqual(self.elf.find_symbol("cleanup_module").shndx, 2)
        self.assertEqual(self.elf.undefined_symbols(), set())

    def test_patch_entry(self):
        self.elf.patch_entry("init_module", build_carrier.NOOP_RET)
        self.assertEqual(
            self.elf.symbol_bytes("init_module", len(build_carrier.NOOP_RET)),
            build_carrier.NOOP_RET,
        )
        sec = self.elf.section(".init.text")
        self.assertEqual(bytes(self.elf.raw[sec.offset:sec.offset + 4]), bytes(range(4)))
        self.assertEqual(
            bytes(self.elf.raw[sec.offset + 12:sec.offset + 16]), bytes(range(12, 16))
        )

    def test_patch_entry_refuses_relocation_overlap(self):
        path = _write_fixture(self.tmp.name, with_reloc=True)
        elf = build_carrier.Elf(path)
        with self.assertRaises(build_carrier.BuildError):
            elf.patch_entry("init_module", build_carrier.NOOP_RET)

    def test_noop_encoding(self):
        self.assertEqual(build_carrier.NOOP_RET.hex(), "00008052c0035fd6")


class TestRealModule(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("PHILIPS_NDP_LOGO_KO")
        and shutil.which("clang")
        and shutil.which("ld.lld"),
        "set PHILIPS_NDP_LOGO_KO and install clang/ld.lld",
    )
    def test_build_carrier(self):
        module = Path(os.environ["PHILIPS_NDP_LOGO_KO"]).resolve()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "ndp_logo_carrier.ko"
            rc = build_carrier.main(["--module", str(module), "--output", str(output)])
            self.assertEqual(rc, 0)
            merged = build_carrier.Elf(output)
            self.assertEqual(
                merged.symbol_bytes("init_module", len(build_carrier.NOOP_RET)),
                build_carrier.NOOP_RET,
            )
            self.assertEqual(
                merged.symbol_bytes("cleanup_module", len(build_carrier.NOOP_RET)),
                build_carrier.NOOP_RET,
            )
            for name in build_carrier.CARRIER_SYMBOLS:
                merged.find_symbol(name)


if __name__ == "__main__":
    unittest.main()
