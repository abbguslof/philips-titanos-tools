# 2026-11-14 recovery backup

Status: **VERIFIED read-only backup**. Restore not tested.

Target: `55PUS8000/12`, chassis `TPA256E` / `TPN256E`, firmware
`TPA256E_V056.002.236.191`.

## Method

The TV was live and rooted at `:2323` / `:2222`. The media drive available on
the workstation is exFAT; the TV has no exFAT driver. The images were pulled
read-only over SSH instead of using the TV-side `emmc_backup.sh` path.

## Images

| Image | Source | Size | SHA-256 |
| :--- | :--- | ---: | :--- |
| `emmc-user.img` | `/dev/mmcblk0` | 7,818,182,656 | `db13bd953f6fbb20cdb34b7337f75c527740dd8f27fc1e9b3a256e803eca2fef` |
| `mmcblk0boot0.img` | `/dev/mmcblk0boot0` | 4,194,304 | `eee415012095a8c51be032d1e713ac120211408aeebe029b8791526bbe4d30bd` |
| `mmcblk0boot1.img` | `/dev/mmcblk0boot1` | 4,194,304 | `eee415012095a8c51be032d1e713ac120211408aeebe029b8791526bbe4d30bd` |

`sha256sum -c SHA256SUMS` passes for all three.

## Boot and metadata pull

`tools/bootchain_dump.py --full-boot` pulled the boot areas and metadata to
`dist/bootchain/2026-11-14` (gitignored). Selected hashes:

| Item | Size | SHA-256 |
| :--- | ---: | :--- |
| `boot0` / `boot1` | 4,194,304 | `eee415012095a8c51be032d1e713ac120211408aeebe029b8791526bbe4d30bd` |
| `p1-vendor-boot0` | 25,165,824 | `e7698f8f509074edad327ef26a13e97d2baa60624d43abb685d3b04faa8388b4` |
| `p2-vendor-boot1` | 25,165,824 | `756355f8f105d48a6fef07e62ae1dc29b7ad114386955f58abaef844030255b5` |
| `p9-misc` | 8,388,608 | `c32f354f0d4869a0c53b6f66eb1dc6b4dcc80293d6bbdbc32a740e917a857f39` |
| `p11-nvm` | 1,048,576 | `7e02cf786704994e881a24ed16006817ffdcc468971c8acf2912f7a0cdc89993` |
| `p36-pstore` | 2,097,152 | `90d958cc4fb7641e9ab87fb3226431c1438e4751ed61e751ca6d10235c7459db` |

The full manifest is in `dist/bootchain/2026-11-14/manifest.json`. It stays
out of the repo.

## Storage and redaction

The images and the bootchain dump are on a local media drive, not in this
repository. This note contains sizes and hashes only. No raw partition bytes,
serial numbers, MAC addresses, SSIDs, or credentials are published.

## Next

Keep a second copy off the TV. The restore test is the next gate and is not
tested here. See [the recovery gate](../../docs/guides/recovery-gate.md) and
[recovery engineering](../../docs/research/26-recovery-engineering.md).
