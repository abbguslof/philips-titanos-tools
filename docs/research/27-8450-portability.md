# 55PUS8450/12 portability notes

Status: **REPORTED** for USB autoroot and `/swdl` persistence. **PLAN** for the
read-only comparison.

The 8450 is a field unit owned by another person. It is not the lab. Use it to
prove what is portable, not to test boot-chain writes or risky kernel payloads.

## Known differences

| Property | 55PUS8000/12 lab | 55PUS8450/12 field |
| :--- | :--- | :--- |
| Firmware | `TPA256E_V056.002.236.191` | `TPN256E_V056.010.032.001` |
| Root partition | `mmcblk0p20` | `mmcblk0p19` (reported) |
| `customer_env.sh` sourced by `run.sh` | Yes | No |
| Persistence hook | `customer_env.sh` | `/swdl/telnet/telnetd` (REPORTED) |
| USB autoroot | VERIFIED | VERIFIED (external logs) |
| USB-less persistence | VERIFIED | REPORTED; missing `root_boot.log` |

The 8450 confirms that partition numbers and boot hooks are firmware-specific.
Do not copy the 8000 bootchain assumptions to it.

## Read-only comparison

Run only `tools/deep_probe.py` on the 8450, with the owner's agreement:

```sh
python3 tools/deep_probe.py --host <8450_IP>
```

Compare the redacted report with the 8000 report:

- kernel version and command line;
- root partition and mount layout;
- `customer_env.sh` / `/swdl/telnet/telnetd` detection;
- `/proc/modules`, `modules_disabled`, module hashes;
- SELinux policy version and hash;
- device nodes (`ntk*`, `ndp*`, `tee*`);
- boot-area flags and sizes;
- listeners and CDP exposure.

This is enough to decide whether the 8000 kernel/carrier work can be ported.

## Persistence verification

To move `/swdl` persistence from REPORTED to VERIFIED:

1. Install the `/swdl/telnet/telnetd` hook with the owner's agreement.
2. Remove the USB stick.
3. Cold boot the 8450.
4. Capture `root_boot.log` with a fresh uptime and the listener state.
5. Add a redacted excerpt to `evidence/tpn256e-variant/`.

Do not load the 8000 `ndp_logo` carrier on the 8450. Do not write its boot
areas.

## What a match would mean

If the 8450 shares the same kernel family, unsigned module policy, SELinux
policy version, and NFSB header layout, the kernel carrier and raw-mount work
is likely portable. If not, the 8450 needs its own module carrier and verifier
map. Either way, the 8000 remains the lab for boot-chain work.
