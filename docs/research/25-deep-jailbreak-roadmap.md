# Deep jailbreak roadmap: the 8000 lab and field units

Status: **PLAN / STARTED 2026-11-12**. Read-only inventory and boot-chain
collection are the first steps. No boot-chain writes.

This page changes the unit model:

- The `55PUS8000/12` is the maintained **lab**. It is owned, physically
  accessible, and already has the deepest verified results: USB root,
  persistence, permissive SELinux, unsigned vendor-module kernel code execution,
  and the runtime raw NFSB mount.
- The `55PUS8450/12` is a **field unit** owned by another person. It is useful
  for read-only fingerprinting and portability validation. Do not run
  boot-chain writes or risky kernel payloads on it.
- Other models are field units too.

The goal is not DRM or Widevine bypass. The goal is full control of owned
hardware: boot chain, kernel, rootfs, and hardware surfaces, while preserving
the certified media stack.

## The ladder

| Level | Capability | 8000 lab | Field units |
| :--- | :--- | :--- | :--- |
| 0 | Ephemeral `uid=0` via USB + cold boot | VERIFIED | 8450 VERIFIED (external) |
| 1 | Persistent root after USB removal | VERIFIED (`customer_env.sh`) | 8450 REPORTED (`/swdl`) |
| 2 | Permissive SELinux, SSH, custom chroot userspace | VERIFIED | UNMEASURED |
| 3 | Unsigned vendor-module carrier, kernel code execution, arbitrary R/W | VERIFIED (`ndp_logo`) | UNMEASURED |
| 3.5 | Runtime kernel primitives: kallsyms, verifier patching, hardware control | REACHABLE | NOT APPROPRIATE |
| 4 | Boot-time control: custom XBoot/ATF/kernel/FDT/initramfs or bootable modified NFSB | BLOCKED | NOT APPROPRIATE |
| 5 | Secure world / DRM keys | OUT OF SCOPE | OUT OF SCOPE |

Level 3.5 is the deepest **reversible** target. Level 4 is the deepest
jailbreak, and it remains a research project until a recovery path exists.

## Why Level 4 is blocked

The 8000 boot chain is `XBoot -> ATF a64m -> Linux`. There is no interactive
U-Boot, no serial RX, and no proven unbrick. The kernel command line lives in
the FDT/ATF path, not in NVM. The NFSB filesystem layer uses SHA-256 + RSA-2048
and dm-verity; the kernel/ATF images are encrypted and covered by `NVHC` and
`UMFG`/`lnikauth` checks.

A bootable modified NFSB or custom kernel therefore needs one of:

1. a recovery slot (second eMMC boot area, external programmer, JTAG/ISP);
2. a working vendor-update path that accepts modified raw boot components;
3. a verifier/signature bypass that survives the boot chain;
4. a hardware console or recovery protocol.

None is proven today. Until one exists, boot-image writes are a one-way bet.

## Phase R: Recovery first

Needed before any boot-chain write:

- full eMMC image and boot-area dumps;
- a restored, tested eMMC boot area;
- eMMC ISP/JTAG and UART RX research;
- boot-area switching and restore;
- a second known-good boot slot if the hardware supports it.

Tools and evidence:

- `tools/bootchain_dump.py` (read-only; local output under `dist/`).
- `docs/research/26-recovery-engineering.md`.

Stop condition: if a deliberately corrupted boot area cannot be restored, do
not write a boot image.

## Phase B: Boot-chain reverse engineering (read-only)

On the 8000:

- pull `mmcblk0boot0/1`, vendor `p1/p2`, `p3/p4`, `p7/p8`, `p9`, `p11`,
  `p13–p18`, `p21`, `p36`, and NFSB headers from `p19/p20/p32–p35`;
- parse the firmware package and compare its `xboot`, ATF, kernel, FDT, and
  NFSB components;
- locate `nfsb_verify`, `nvt_dm_check_nfsb`, `dm_check_nfsb`, the dm-verity
  parameters, `NVHC`, `UMFG`, and `lnikauth`;
- map what is signed, what is encrypted, and where the public key or verifier
  lives;
- inspect the eMMC boot-area selection (`boot_area`, `EXT_CSD`) without writing.

First run:

```sh
python3 tools/deep_probe.py --host <TV_IP> --hash-large-partitions
python3 tools/bootchain_dump.py --host <TV_IP>
```

Keep the raw output under `dist/` (gitignored). Publish only hashes and
non-identifying observations.

## Phase K: Reusable kernel carrier

The `ndp_logo` carrier proved unsigned kernel code execution and arbitrary
kernel read/write. Turn it into a framework:

- no hardcoded module base or offsets;
- runtime `kallsyms` resolution;
- no-op carrier first, then a controlled read/write interface;
- targeted primitives: clean SELinux control, verifier inspection/patching,
  eMMC/boot-area reads, device ioctls;
- every payload non-persistent until it survives cold-boot testing.

This layer gives runtime control. It does not make a modified boot image
bootable.

## Phase D: Dual-boot / recovery slot

If Phase R proves a restorable second boot area:

- keep one eMMC boot area stock;
- put an experimental XBoot/ATF/kernel stage in the other;
- verify the boot ROM selection and restore;
- only then attempt a custom early boot stage.

This route is the most plausible safe route to Level 4 on the owned lab.

## Phase H: Harden the current root

Before adding privilege:

- close or restrict `:2323` and `:7788`;
- keep key-only SSH;
- verify payload hashes at boot;
- account for the vendor `chmod 777 -R /mtd_apdat`;
- keep the USB autoroot stick and NVM/EDID backups.

## Field units (8450 and others)

Read-only only:

- `tools/deep_probe.py` (redacted report);
- hook detection (`customer_env.sh` vs `/swdl/telnet/telnetd`);
- persistence verification with the owner's agreement;
- comparison of kernel, modules, SELinux, partitions, NFSB headers, and device
  nodes.

No boot-chain writes, no 8000 carrier modules, no `insmod` experiments on a
field unit.

## First results (2026-11-12)

- Fresh 8000 inventory: kernel 6.1.124, root p20, permissive v33 policy hash
  `b43297...`, `modules_disabled=0`, both boot hooks present, boot areas
  identical and `force_ro=1`.
- Boot images mapped: `p1/p2` U-Boot slots, `p13/p14` ATF, `p15/p16` FDT,
  `p17/p18` current kernel, `p19/p20` rootfs, `p21` plain `kerupm` upgrade kernel.
- The secure slot payloads (`p1/p2`, `p13–p18`) are high-entropy and their
  stored bytes do not match the uImage data CRCs; the plain `p21` kernel
  (`6.1.84-gfd8d77599fee`) matches both CRCs.
- `p1`/`p2` differ only at `0x1a0034` and the `UMFG` slot byte `0x1a0204`;
  `p9` holds the `secos0/1`, `fdt0/1`, `ker0/1`, `fs0/1` and `kernel` map.
- `p9` decodes into `DBFG`, two `PPCH` slot tables (60-byte entries:
  name/device/offset/flag/slot), `FWVR`, two `NVHC` hash/partition tables,
  `UPST`, and the last package name. The `PPCH` slot 0/1 tables point `uboot`
  to `0x100000` and `vertbl` to `0xe7ee00` inside `p1/p2`.
- `p1/p2` carry a plaintext `STBC` boot-control block at `0x1a0000`, the
  `UMFG` slot marker, and a `VTBL` verification table at `0xe7ee00`
  (`0x224` bytes). The readable `STBC` slot is `p1=0`, `p2=1`.
- The local firmware package maps byte-for-byte to the live partitions. The
  secure components carry a 260-byte trailer; `kerupm` (19,841,096 bytes,
  target `/dev/nvt-part-name/kerupm`, live `p21`) is a **plain uImage with no
  component signature** and a valid data CRC. It is the vendor's kernel
  upgrade manager image.
- The package also carries a RAM update environment: `eburner` (plain
  Linux/arm64 kernel), `sys_run` (gzip tar with `run.sh` and `nvt_eburner`),
  and the static `nvt_eburner` burner. The burner strings show MD5 verification
  and partition/boot-flag writes, but no RSA/SHA strings. The update environment
  is a potential update-mode code-execution path; the first safe test is a
  dump-only `sys_run/run.sh` that skips the burner.
- Details: [boot image map](28-boot-image-map.md),
  [update package map](29-update-package-map.md), evidence
  [deep/2026-11-12](../../evidence/deep/2026-11-12-8000-bootchain.md).

The immediate next probes are the `p9` table parser, the `p1/p2` U-Boot/FIT
metadata, and whether `p21` can be selected as the `kerupm` update kernel. No
writes until Phase R.

## Current status

- [x] 8000 lab ladder and blockers documented.
- [x] Read-only probe, bootchain dump and inspect tools.
- [x] Fresh 8000 read-only inventory.
- [x] 8000 boot-area and metadata collection.
- [x] First boot-image map (protected slots + plain `p21`).
- [x] `p9` `PPCH`/`STBC`/`VTBL` parsing and package-to-live mapping.
- [x] Update environment mapped (`eburner`/`sys_run`/`nvt_eburner`).
- [ ] Full eMMC/boot-area backup (recovery gate).
- [ ] Update trigger and package-loader mapping.
- [ ] Dump-only `sys_run` package test.
- [ ] `kerupm` update-mode verification and boot selection.
- [ ] `p1/p2` U-Boot/FIT metadata and secure-chain verifier.
- [ ] 8450 read-only inventory and `/swdl` persistence proof.
- [ ] Recovery engineering (Phase R).
- [ ] Boot-chain verifier and key map (Phase B).
- [ ] Reusable kernel carrier (Phase K).
- [ ] Dual-boot recovery slot (Phase D).
- [ ] Boot-chain write, only after R (Phase 4).
