#!/usr/bin/env python3
"""Verify and rebuild the dm-verity tree inside an NFSB filesystem image.

The first 0x1000 bytes of an NFSB image are the header, then the data blocks,
then the hash tree. The header carries the SHA-256 salt and root digest; the
tree is stored at `hash_start_block` with the highest level first. With a single
data block dm-verity has zero hash levels: the root is `H(salt || data)` and
there is no tree block.

`verify` recomputes the tree from the data and compares both the root digest and
the stored tree. `rebuild` writes a new image with a recomputed tree and header
root digest, so a modified data block can pass dm-verity.

Local files only. It never opens the TV, a block device, or the network, and it
does not modify the input image. The header is checked against the fields
reversed in docs/research/43-nfsb-dm-mapping-2026-11-22.md.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

HEADER_SIZE = 0x1000
MAGIC = b"NFSB"
START_SECTOR = 0x06
DATA_LEN_SECTORS = 0x0A
DATA_BLOCKS = 0x12
DATA_BLOCK_SIZE = 0x16
ALGORITHM = 0x1A
HASH_BLOCK_SIZE = 0x2A
SALT = 0x2E
DIGEST = 0x6F
DIGEST_BYTES = 64
SIGNATURE = 0xB0
SECTOR = 512


class NfsbError(Exception):
    """A malformed image or an unsupported header."""


@dataclass(frozen=True)
class Header:
    version: int
    verity_version: int
    start: int
    data_len: int
    data_blocks: int
    data_block_size: int
    hash_block_size: int
    algorithm: str
    salt: bytes
    digest_hex: str


def _u32be(buf: bytes, offset: int) -> int:
    return struct.unpack_from(">I", buf, offset)[0]


def _ascii(buf: bytes, offset: int, length: int) -> str:
    raw = buf[offset : offset + length].split(b"\0", 1)[0]
    try:
        return raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise NfsbError(f"non-ASCII header field at 0x{offset:x}") from exc


def _hex_field(buf: bytes, offset: int, name: str) -> bytes:
    text = _ascii(buf, offset, DIGEST_BYTES)
    if len(text) != DIGEST_BYTES:
        raise NfsbError(f"{name} at 0x{offset:x} is not {DIGEST_BYTES} hex chars")
    try:
        return bytes.fromhex(text)
    except ValueError as exc:
        raise NfsbError(f"{name} at 0x{offset:x} is not hex") from exc


def parse_header(buf: bytes) -> Header:
    if len(buf) < HEADER_SIZE:
        raise NfsbError("image is smaller than the 0x1000 header")
    if buf[:4] != MAGIC:
        raise NfsbError("not an NFSB image (magic mismatch)")
    algorithm = _ascii(buf, ALGORITHM, 16)
    if algorithm not in hashlib.algorithms_available:
        raise NfsbError(f"unsupported hash algorithm {algorithm!r}")
    header = Header(
        version=buf[0x04],
        verity_version=buf[0x05],
        start=_u32be(buf, START_SECTOR) * SECTOR,
        data_len=_u32be(buf, DATA_LEN_SECTORS) * SECTOR,
        data_blocks=_u32be(buf, DATA_BLOCKS),
        data_block_size=_u32be(buf, DATA_BLOCK_SIZE),
        hash_block_size=_u32be(buf, HASH_BLOCK_SIZE),
        algorithm=algorithm,
        salt=_hex_field(buf, SALT, "salt"),
        digest_hex=_hex_field(buf, DIGEST, "root digest").hex(),
    )
    if header.data_block_size == 0 or header.hash_block_size == 0:
        raise NfsbError("zero data or hash block size")
    if header.data_len != header.data_blocks * header.data_block_size:
        raise NfsbError(
            "data length does not equal data_blocks * data_block_size"
        )
    digest_size = len(hashlib.new(header.algorithm).digest())
    if header.hash_block_size % digest_size:
        raise NfsbError("hash block size is not a multiple of the digest size")
    if len(header.salt) != digest_size:
        raise NfsbError(f"salt is {len(header.salt)} bytes, expected {digest_size}")
    return header


def build_tree(image: bytes, header: Header) -> tuple[bytes, bytes, list[int]]:
    """Return (root_digest, on-disk_tree, blocks_per_level)."""
    expected = header.data_blocks * header.data_block_size
    data = image[header.start : header.start + expected]
    if len(data) != expected:
        raise NfsbError(
            f"image has {len(data)} bytes of data, expected {expected}"
        )
    digest_size = len(hashlib.new(header.algorithm).digest())
    per_block = header.hash_block_size // digest_size

    def hash_block(block: bytes) -> bytes:
        return hashlib.new(header.algorithm, header.salt + block).digest()

    digests = [
        hash_block(data[i * header.data_block_size : (i + 1) * header.data_block_size])
        for i in range(header.data_blocks)
    ]
    if not digests:
        raise NfsbError("no data blocks")
    # With a single data block dm-verity has zero hash levels: the root is the
    # data-block hash and there is no tree block (confirmed with veritysetup).
    if len(digests) == 1:
        return digests[0], b"", []
    levels: list[list[bytes]] = []
    while True:
        blocks = []
        for offset in range(0, len(digests), per_block):
            chunk = digests[offset : offset + per_block]
            blocks.append(b"".join(chunk).ljust(header.hash_block_size, b"\0"))
        levels.append(blocks)
        if len(blocks) == 1:
            break
        digests = [hash_block(block) for block in blocks]

    root = hash_block(levels[-1][0])
    # The kernel stores the highest level first and the data level last.
    tree = b"".join(block for level in reversed(levels) for block in level)
    return root, tree, [len(level) for level in levels]


@dataclass(frozen=True)
class VerifyResult:
    header: Header
    computed_root: str
    root_ok: bool
    tree_ok: bool
    blocks_per_level: list[int]

    @property
    def ok(self) -> bool:
        return self.root_ok and self.tree_ok


def verify(image: bytes) -> VerifyResult:
    header = parse_header(image)
    root, tree, blocks = build_tree(image, header)
    tree_offset = header.start + header.data_blocks * header.data_block_size
    stored = image[tree_offset : tree_offset + len(tree)]
    return VerifyResult(
        header=header,
        computed_root=root.hex(),
        root_ok=root.hex() == header.digest_hex,
        tree_ok=stored == tree,
        blocks_per_level=blocks,
    )


def rebuild(image: bytes) -> bytes:
    header = parse_header(image)
    root, tree, _ = build_tree(image, header)
    digest_size = len(hashlib.new(header.algorithm).digest())
    if digest_size != 32:
        raise NfsbError("only 32-byte digests fit the header field")
    tree_offset = header.start + header.data_blocks * header.data_block_size
    updated = bytearray(image)
    end = tree_offset + len(tree)
    if end > len(updated):
        updated.extend(b"\0" * (end - len(updated)))
    updated[tree_offset:end] = tree
    updated[DIGEST : DIGEST + DIGEST_BYTES] = root.hex().encode("ascii")
    return bytes(updated)


def _cmd_verify(args: argparse.Namespace) -> int:
    image = Path(args.image).read_bytes()
    result = verify(image)
    header = result.header
    tree_offset = header.start + header.data_blocks * header.data_block_size
    tree_len = sum(result.blocks_per_level) * header.hash_block_size
    print(f"NFSB verity: {args.image}")
    print(
        f"data: {header.data_blocks} x {header.data_block_size} at 0x{header.start:x}"
    )
    print(
        f"tree: start block {header.data_blocks} at 0x{tree_offset:x}, "
        f"{tree_len} bytes, levels {result.blocks_per_level}"
    )
    print(f"computed root: {result.computed_root}")
    print(f"header root:   {header.digest_hex} {'OK' if result.root_ok else 'MISMATCH'}")
    print(f"stored tree:   {'OK' if result.tree_ok else 'MISMATCH'}")
    print("result:", "OK" if result.ok else "FAILED")
    return 0 if result.ok else 1


def _cmd_rebuild(args: argparse.Namespace) -> int:
    source = Path(args.image)
    output = Path(args.output)
    if source.resolve() == output.resolve():
        raise NfsbError("refusing to overwrite the input image")
    if output.exists() and not args.force:
        raise NfsbError(f"{output} exists; use --force to overwrite")
    updated = rebuild(source.read_bytes())
    result = verify(updated)
    if not result.ok:
        raise NfsbError("rebuilt image did not verify")
    output.write_bytes(updated)
    print(f"wrote {output} ({len(updated)} bytes)")
    print(f"root: {result.computed_root}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    verify_parser = sub.add_parser("verify", help="recompute and compare the tree")
    verify_parser.add_argument("image")
    verify_parser.set_defaults(func=_cmd_verify)
    rebuild_parser = sub.add_parser(
        "rebuild", help="write a copy with a recomputed tree and root digest"
    )
    rebuild_parser.add_argument("image")
    rebuild_parser.add_argument("--output", required=True)
    rebuild_parser.add_argument("--force", action="store_true")
    rebuild_parser.set_defaults(func=_cmd_rebuild)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (NfsbError, OSError) as exc:
        print(f"nfsb_verity: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
