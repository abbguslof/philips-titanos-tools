# SELinux runtime control: permissive v33 policy

Status: **VERIFIED / WORKING** on `55PUS8000/12`, firmware
`TPA256E_V056.002.236.191`, 2026-11-01. User report after a cold boot: Settings
and native menus work; the only remaining gap is the intentional Pi-hole block
on `titanos.tv`.

A persistent kernel carrier now also clears `selinux_state.initialized` at boot
(`/mtd_rwarea/apdat/ndp_logo_seloff_boot.ko`); see
[16-kernel-and-hardware-control.md](16-kernel-and-hardware-control.md). It
causes SELinux context/audit log errors. The permissive policy remains the
stable fallback; create `no_kernel_module` and cold boot to skip the carrier.

## Summary

The global switch is still not runtime-reachable: `setenforce 0` and
`/sys/fs/selinux/disable` return `EINVAL`, and `/etc/selinux/config` is
read-only. But SELinux enforcement has been disabled with a **version-33
policy in which every type is permissive**. The policy is built on the host from
the TV's own policy and loaded at boot from
`/mtd_rwarea/apdat/customer_env.sh`.

`getenforce` still reports `Enforcing` because the kernel's global enforcing
flag remains 1. The loaded policy puts all 1120 types in permissive mode, so
AVC denials are allowed and `mounton` over `appmgr_t`/`tpvopera_t` succeeds.
This is a permissive policy, not a global `enforcing=0`.

## Why the earlier policy load failed

`cat > /sys/fs/selinux/load` writes the policy in 128 KiB chunks. The kernel's
`sel_write_load` expects one whole-policy write; the second chunk was parsed as
a new policy and failed with:

```text
SELinux: ebitmap: truncated map
SELinux: failed to load policy
cat: write error: Invalid argument
```

A single write of the whole file works:

```sh
dd if=/path/policy of=/sys/fs/selinux/load bs=1048576 count=1
```

The previous "version 30 vs kernel `policyvers` 33" diagnosis was wrong. The
stock v30 policy loads with `dd`; the version mismatch was not the blocker.

## Build the permissive v33 policy

On the host, using the TV policy copy (`/swdl/policy33.bin`, sha256
`d18f4196ef0b8089c71bacc770f231872e4f9062f672f7cf5fc3051ad9716d60`):

```sh
checkpolicy -b -C -c 33 -o policy.cil /tmp/opencode/policy33.bin

# One line per type; the CIL export has 1120 (type NAME) lines.
sed -nE 's/^\(type ([^)]*)\)$/(typepermissive \1)/p' \
  policy.cil > permissive.cil

secilc -c 33 -o policy.33.perm.bin policy.cil permissive.cil
```

Result:

```text
policy.33.perm.bin   252,211 bytes
sha256               3ef09aa693f7486c6667461da4e2ad1ad8e406c02bb3915c9f9f1b9cddf1dc2d
Policy Version       33 (MLS disabled)
Types                1120
Permissives          1120
```

The CIL round-trip drops a few allow/dontaudit rules and some empty attributes
relative to the enforcing policy. That does not matter for this use: every type
is permissive. Do not reuse this binary as an enforcing policy without diffing
it first.

## Load and persist

Runtime load (works immediately, no reboot):

```sh
dd if=/mtd_rwarea/apdat/policy.33.perm.bin \
   of=/sys/fs/selinux/load bs=1048576 count=1
```

Persistent boot hook, appended to `/mtd_rwarea/apdat/customer_env.sh` (sourced
early by `/mtd_apexe/board/run.sh`):

```sh
# Load permissive SELinux policy (v33) early.
[ -f /mtd_rwarea/apdat/policy.33.perm.bin ] && \
  /bin/dd if=/mtd_rwarea/apdat/policy.33.perm.bin \
  of=/sys/fs/selinux/load bs=1048576 count=1 2>/dev/null || true
```

The TV was cold-rebooted with `reboot -f`; the hook survived and the permissive
policy was active after boot:

```text
uptime                       56 s
getenforce                   Enforcing
/sys/fs/selinux/enforce      1
sha256 /sys/fs/selinux/policy b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2
```

The kernel export hash differs from the file hash because the kernel serializes
the loaded policy.

## Verify mounton

After reboot, mount over a directory relabeled to the previously denied type:

```sh
mkdir -p /tmp/mnttest3
chcon system_u:object_r:appmgr_t /tmp/mnttest3
mount --bind /tmp /tmp/mnttest3
# mounton_rc=0
umount /tmp/mnttest3
```

This is the permission that denied the stock appmgr/FreeTitan overlay. The
`bin_t` `unconfined_t` workaround is no longer needed for `mounton`.

## Post-change check

- A cold boot (`reboot -f`) kept the permissive policy active. A second check at
  82 s uptime showed the same policy export hash, `mounton_rc=0` over an
  `appmgr_t` target, and no `avc: denied` lines.
- The user reports the TV is otherwise fully working: Settings and native menus
  open, installed apps work, and the TV survives a cold restart.
- The only reported failure is the Pi-hole block on `titanos.tv`, which is
  intentional. Remove `app.titanos.tv`/`eu.app.titanos.tv` from the block list
  if cloud services are wanted; keep it if the local/privacy posture is wanted.

## What still does not work

- `setenforce 0` and `/sys/fs/selinux/disable`: `EINVAL`. The kernel's global
  enforcing flag is not writable on this build.
- `getenforce` still prints `Enforcing`; only the policy's per-type permissive
  state disables enforcement.
- Two v33 kernel permissions absent from the v30 policy
  (`nlmsg_readpriv`, `nlmsg_getneigh` in `netlink_route_socket`) remain
  unknown and are denied. The stock policy had the same limitation.
- `kexec`, `/dev/mem`, `/dev/kmem`, `/proc/kcore`, `/lib/modules`, and a
  matching kernel build tree are absent. The module route is still blocked.
- The boot chain is untouched. FDT/ATF/boot-image `selinux=0`/`enforcing=0`
  remains a brick-risk path with no proven recovery.

## Rollback

The stock policy remains at `/etc/selinux/targeted/policy/policy.30` and the
pre-change hook is at `/mtd_rwarea/apdat/customer_env.sh.bak-20261101`.

1. Remove the "Load permissive SELinux policy" line from
   `/mtd_rwarea/apdat/customer_env.sh`.
2. Reboot with `reboot -f`, or reload the stock policy immediately:

```sh
dd if=/etc/selinux/targeted/policy/policy.30 \
   of=/sys/fs/selinux/load bs=1048576 count=1
```

The permissive policy file can stay on `/mtd_rwarea/apdat`; it is inert without
the hook.

## Evidence

| Fact | Value |
| :--- | :--- |
| Stock on-disk policy | `b006903773993f56000a4207b193b7784b63ca5211699cb872b9964311780ccb` |
| Stock running export | `d18f4196ef0b8089c71bacc770f231872e4f9062f672f7cf5fc3051ad9716d60` |
| Permissive v33 file | `3ef09aa693f7486c6667461da4e2ad1ad8e406c02bb3915c9f9f1b9cddf1dc2d` |
| Permissive v33 size | 252,211 bytes |
| Permissive types | 1120 |
| After boot, policy export | `b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2` |
| Hook backup | `/mtd_rwarea/apdat/customer_env.sh.bak-20261101` |

## Safety

- No boot-chain, eMMC, or FDT writes.
- No firmware flash; the available package is the same `V056.002.236.191`.
- Remove the policy-load hook before any firmware update; the policy is matched
  to this kernel/policy generation.
- The change is userspace-loaded and reversible by removing the hook.
- Keep `policy.33.perm.bin` and the hook backup for rollback.
