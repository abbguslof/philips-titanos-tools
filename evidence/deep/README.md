# Deep boot-chain evidence

These are redacted summaries of read-only collections made with
`tools/deep_probe.py`, `tools/bootchain_dump.py` and
`tools/bootchain_inspect.py`. Raw partitions, NVM, pstore, and boot images are
kept under the gitignored `dist/` tree and are not published.

| Set | What it proves |
| :--- | :--- |
| [2026-11-12 boot-chain map](2026-11-12-8000-bootchain.md) | The 8000 secure slot images are protected; `p21` is the plain arm64 `kerupm` upgrade kernel; `p1/p2` are two boot slots; `p9` carries the slot map; the package components match the live partitions byte-for-byte; the RAM update environment and MD5-only burner are the next lead. |

Method and limits: [boot image map](../../docs/research/28-boot-image-map.md),
[deep roadmap](../../docs/research/25-deep-jailbreak-roadmap.md), and
[recovery engineering](../../docs/research/26-recovery-engineering.md).

Rules: hashes and signatures only; no real MACs, serials, SSIDs, IPs, NVM
dumps, pstore contents, or boot-image bytes.
