# Persist through `customer_env.sh`, not the rootfs

The rootfs is a read-only SquashFS inside an RSA/SHA-256 `NFSB` wrapper. `run.sh` sources `/mtd_apdat/customer_env.sh` from the writable `apdat` partition on every boot. We will persist by adding one hook line there and running a delayed `root_boot.sh`, rather than modifying the rootfs or bootloader.

**Status:** accepted; amended 2026-11-11 for a firmware variant

**Consequences:** The change survives reboot but not a full factory data wipe, and it must delay the firewall rule until after `iptables_conf.sh`. Restore is deleting the hook. The authority boundary is `apdat`, not the secure boot chain.

**Amendment:** On a later `TPN256E` firmware, `run.sh` no longer sources `customer_env.sh`. The vendor `run_custom_impl.sh` still executes `/swdl/telnet/telnetd` if it is executable, so the installer detects that seam and writes a one-line wrapper there instead. The payload still lives on `apdat`; `/swdl` becomes a second authority boundary on those units. An external contributor reported this variant; this repo has not reproduced it. See `docs/research/24-swdl-telnet-persistence-2026-11-11.md`.
