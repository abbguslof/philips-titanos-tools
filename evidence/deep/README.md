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
| [2026-11-14 NDAL V4L2 reset](2026-11-14-ndal-v4l2-reset.md) | The paused-appmgr retry, the corrected NDAL V4L2 control and `/dev/video24` target, the classic eburner USB-image initramfs, the p9 metadata layout, the tested reset/entry attempts, the vendor VER40 USB update/A-B activation (active slot 0/boot0; recovery slot 1/boot1), and the vendor/p9 cleanup. |
| [2026-11-20 kernel carrier](2026-11-20-kernel-carrier.md) | The Level 3.5 carrier loads, exposes the `carrier` parameter, passes the KCFI set/get check, writes and reads its own scratch buffer, resolves symbols, and reads live kernel symbols. The live `param_ops_int` hashes match the carrier. Rollback and reboot restored the seloff module and policy. |
| [2026-11-20 runtime verifier patch](2026-11-20-runtime-verifier-patch.md) | Direct `nfsb_verify` patch: pristine header accepted, modified signature rejected, patched function accepts it; both instructions patched via `aarch64_insn_patch_text_nosync`; reboot restores the original. The full NFSB dm mapping is verified in the 2026-11-22 evidence. |
| [2026-11-20 ndp_led backlight](2026-11-20-ndp-led-backlight.md) | Exported `KER_LED_PWM_HWFR_Get_Duty`/`Set_Duty`: channel 0 duty 20000/offset 105, dim to 10000, restore; reboot returns the default. |
| [2026-11-20 NFSB mount check](2026-11-20-nfsb-mount-check.md) | `nvt_dm_check_nfsb` rejects a modified loop copy unpatched and accepts it after the `nfsb_verify` patch (`NFSB header found and verified`); the full dm mapping is verified in the 2026-11-22 evidence. |
| [2026-11-22 NFSB dm mapping](2026-11-22-nfsb-dm-mapping.md) | `nvt_dm_setup_linear` and `nvt_dm_setup_nfsb` build the `linear` and `verity` targets on a loop copy; the verity node mounts the stock SquashFS read-only; reboot restores the live state. The dm-verity data path is verified in the next row. |
| [2026-11-22 NFSB verity data path](2026-11-22-nfsb-verity-data-path.md) | A modified data block returns EIO with the stock tree/digest and reads successfully after the tree is recomputed and the header root digest is replaced; the rebuilt block matches the local bytes. Reboot restores the live state. |
| [2026-11-22 custom NFSB mount](2026-11-22-custom-nfsb-mount.md) | A host-built SquashFS + NFSB header/tree (1 MiB, two-level tree) mounts read-only through the runtime setup; a marker file reads back. The one-data-block case is explained (dm-verity zero levels, root `H(salt\|\|data)`). |
| [2026-11-22 Level 4 boot-chain map](2026-11-22-level4-boot-chain-map.md) | Live A/B hashes, the static NVHC/VTBL/U-Boot slots, the encrypted XBoot pair, the 260-byte component trailers, and the eMMC boot-part switch. Read-only; no boot-area writes. |

Method and limits: [boot image map](../../docs/research/28-boot-image-map.md),
[deep roadmap](../../docs/research/25-deep-jailbreak-roadmap.md), and
[recovery engineering](../../docs/research/26-recovery-engineering.md).

Rules: hashes and signatures only; no real MACs, serials, SSIDs, IPs, NVM
dumps, pstore contents, or boot-image bytes.
