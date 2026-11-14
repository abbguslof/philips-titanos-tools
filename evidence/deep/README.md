# Deep boot-chain evidence

These are redacted summaries of read-only collections made with
`tools/deep_probe.py`, `tools/bootchain_dump.py` and
`tools/bootchain_inspect.py`. Raw partitions, NVM, pstore, and boot images are
kept under the gitignored `dist/` tree and are not published.

| Set | What it proves |
| :--- | :--- |
| [2026-11-12 boot-chain map](2026-11-12-8000-bootchain.md) | The 8000 secure slot images are protected; `p21` is the plain arm64 `kerupm` upgrade kernel; `p1/p2` are two boot slots; `p9` carries the slot map; the package components match the live partitions byte-for-byte; the RAM update environment and MD5-only burner are the next lead. |
| [2026-11-14 update path](2026-11-14-update-path.md) | The component map, MD5-only burner checks, live slot matches, and the prepared dump-only package. |
| [2026-11-14 app-layer gate](2026-11-14-app-update-gate.md) | The USB trigger, `/swdl/autorun.upg` is `TIMGPKGVER40`, the RSA verifier, no private key, and the direct staging test results. |
| [2026-11-14 eMMC backup](2026-11-14-emmc-backup.md) | Full eMMC and boot-area backup hashes, the second copy, and the same-byte restore and cold-boot proof. |
| [2026-11-14 NDAL V4L2 reset](2026-11-14-ndal-v4l2-reset.md) | The paused-appmgr eburner retry, the corrected NDAL V4L2 control and `/dev/video24` target, the full AC-on wrapper consuming the package, and the vendor/p9 cleanup. |

Method and limits: [boot image map](../../docs/research/28-boot-image-map.md),
[deep roadmap](../../docs/research/25-deep-jailbreak-roadmap.md), and
[recovery engineering](../../docs/research/26-recovery-engineering.md).

Rules: hashes and signatures only; no real MACs, serials, SSIDs, IPs, NVM
dumps, pstore contents, or boot-image bytes.
