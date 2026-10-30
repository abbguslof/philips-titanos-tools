# Persist through `customer_env.sh`, not the rootfs

The rootfs is a read-only SquashFS inside an RSA/SHA-256 `NFSB` wrapper. `run.sh` sources `/mtd_apdat/customer_env.sh` from the writable `apdat` partition on every boot. We will persist by adding one hook line there and running a delayed `root_boot.sh`, rather than modifying the rootfs or bootloader.

**Status:** accepted

**Consequences:** The change survives reboot but not a full factory data wipe, and it must delay the firewall rule until after `iptables_conf.sh`. Restore is deleting the hook. The authority boundary is `apdat`, not the secure boot chain.
