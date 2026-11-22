# Deep jailbreak roadmap: the 8000 lab and field units

Status: **PLAN / STARTED 2026-11-12; updated 2026-11-22**. Level 3 is verified
on the lab. The Level 3.5 carrier, verifier patch, mount-path check, backlight,
full NFSB dm mapping, dm-verity data path, and a custom NFSB mount are verified.
The Level 4 boot chain is mapped; the A/B switch to slot 0 is TESTED-NEGATIVE
(slot 0 is not licensed). The old slot 1/boot1 is the licensed pair; the
recovery is p9 DBFG 2 and `EXT_CSD 0x50`. No boot-chain writes.

This page changes the unit model:

- The `55PUS8000/12` is the maintained **lab**. It is owned, physically
  accessible, and already has the deepest verified results: USB root,
  persistence, permissive SELinux, unsigned vendor-module kernel code execution,
  and the runtime raw NFSB mount.
- The `55PUS8450/12`, `77OLED760/12`, `70PUS8108/60`, and `43PUS7608/12` are
  **field units** owned by other people. They are useful for read-only
  fingerprinting and portability validation. Do not run boot-chain writes or
  risky kernel payloads on them. Other models are field units too.

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
| 3.5 | Runtime kernel primitives: kallsyms, verifier patching, hardware control | VERIFIED (partial) | NOT APPROPRIATE |
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

The 2023 `TPN236E` `169.001` package adds its own barriers: signed 8051
`stbc_emmc`, an 8051 loader in `xboot`, and a second boot-ROM/OTP-encrypted
`xboot` bulk. It also has no `eburner`/`sys_run`/`kerupm`. See
[the 169.001 follow-up](35-tpn236e-169001-static-2026-11-15.md). This does not
change the 8000 block.

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
not write a boot image. The 2026-11-14 same-byte restore on `mmcblk0boot0` and
`mmcblk0boot1` passed; the deliberately corrupted case and the boot-area
selection/ISP path remain open.

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
kernel read/write. The current carrier is a one-shot hardcoded seloff payload,
not a reusable interface. Turn it into a framework:

- no hardcoded module base or offsets;
- runtime `kallsyms` resolution;
- no-op carrier first, then a controlled read/write interface;
- targeted primitives: clean SELinux control, verifier inspection/patching,
  eMMC/boot-area reads, device ioctls;
- every payload non-persistent until it survives cold-boot testing.

The carrier is verified on the lab (2026-11-20): it builds from the TV's own
`ndp_logo.ko`, loads, exposes the parameter, passes the live KCFI check, writes
and reads kernel memory, and reads live symbols. Rollback and reboot restored
the seloff path. The direct `nfsb_verify` patch is verified in
[38](38-runtime-verifier-patch-2026-11-20.md). The mount-path check
(`nvt_dm_check_nfsb`) accepts a modified loop copy after the patch, the
`ndp_led` PWM backlight dims and restores, and the full `linear` + `verity` dm
mapping mounts a loop copy read-only. See
[39](39-ndp-led-pwm-backlight-2026-11-20.md),
[40](40-nfsb-mount-check-2026-11-20.md), and
[43](43-nfsb-dm-mapping-2026-11-22.md). The dm-verity data path is verified in
[44](44-nfsb-verity-data-path-2026-11-22.md), and a custom NFSB image mounts
read-only in [45](45-custom-nfsb-mount-2026-11-22.md). The live A/B pair, the
static VTBL/NVHC/U-Boot slots, the encrypted XBoot, the component trailers, and
the eMMC boot-part switch are mapped in
[46](46-level4-boot-chain-map-2026-11-22.md). The A/B recovery switch is the
next test. See
[Level 3.5: reusable kernel carrier](37-kernel-carrier-level-3-5.md).

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
- 2023 `TPN236E` field units: read-only network probes, plus the owner-run
  physical path in [the RPC-injection note](42-tpn236e-43pus7608-rpc-injection-root-2026-11-21.md).
  No network entry exists. A physical USB `nbrowser_log_to_file` flag opens
  `:7788`; the launcher RPC bridge then reaches `idtv` and root. Do not apply
  the 8000 eburner/carrier paths.

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
  [deep/2026-11-12](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/deep/2026-11-12-8000-bootchain.md).

The first probes were the `p9` table parser, the `p1/p2` U-Boot/FIT metadata,
and whether `p21` can be selected as the `kerupm` update kernel. The `p9`
parser is complete; the `p1/p2` metadata and `p21` selection remain open. No
writes until Phase R.

## Later results (2026-11-14/15)

- The genuine vendor VER40 USB update loaded, validated, and programmed active
  slot 0 (`p15`/`p17`/`p19`). The live boot stayed slot 1/boot1 with
  `lnikauth pass`; slot 0 fails `lnikauth` (48). Root and persistence ran on
  slot 1. The app-layer RSA
  verifier remains the barrier for a modified package. See
  [the app-layer update gate](31-app-update-gate-2026-11-14.md).
- The 2023 `TPN236E` `169.001` package was verified externally: hashes, 19/19
  stored MD5s, and PIMG offsets. It has no `eburner`/`sys_run`/`kerupm`; its
  `stbc_emmc` is 8051 firmware and its `xboot` bulk is a second
  boot-ROM/OTP-encrypted layer. See
  [the 169.001 follow-up](35-tpn236e-169001-static-2026-11-15.md).
- The 2023 field units have no CDP endpoint on the default boot. The
  `CDP -> idtv` candidate is open through a physical USB
  `nbrowser_log_to_file` flag, and the 43PUS7608/12 unit was taken to root:
  the launcher RPC bridge injects a shell command as `idtv`, then
  `customer_env.sh` runs as root on reboot. Physical only, not remote.
  `msg_server` and the active `cmd_daemon` remain local root `system()` queues;
  `msg_server` runs as `initrc_t`; they need a local sender and are not initial
  entries. See
  [the RPC-injection note](42-tpn236e-43pus7608-rpc-injection-root-2026-11-21.md).
- Issue #8 corrected the doc 35 `msg_server`/`cmd_daemon` labels and recorded
  the physical serial, USB-gated CDP, and factory-console paths. The default
  network surface and Level 3.5 status are unchanged at the time of that note.
- The reusable Level 3.5 carrier, verifier patch, mount-path check, `ndp_led`
  backlight, full NFSB dm mapping, dm-verity data path, and a custom NFSB mount
  are verified on the lab (2026-11-20/22). The next step is the Level 4
  recovery/boot-chain gate.

## Current status

- [x] 8000 lab ladder and blockers documented.
- [x] Read-only probe, bootchain dump and inspect tools.
- [x] Fresh 8000 read-only inventory.
- [x] 8000 boot-area and metadata collection.
- [x] First boot-image map (protected slots + plain `p21`).
- [x] `p9` `PPCH`/`STBC`/`VTBL` parsing and package-to-live mapping.
- [x] Update environment mapped (`eburner`/`sys_run`/`nvt_eburner`).
- [x] Full eMMC/boot-area backup (recovery gate). See
  [2026-11-14 backup](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/deep/2026-11-14-emmc-backup.md).
- [x] Same-byte restore test: both boot areas written, read-back verified, both
  cold boots returned root. A deliberately corrupted boot area is still
  untested.
- [x] App-layer update trigger, package-loader mapping, and genuine vendor
  VER40 update: slot 0/boot0 written; the live boot stayed slot 1/boot1 with
  `lnikauth pass`; slot 0 fails `lnikauth`. See
  [the app-layer update gate](31-app-update-gate-2026-11-14.md).
- [x] 2023 `TPN236E` `169.001` external artifact and live follow-up; no CDP on
  the default boot and no network entry. The physical USB flag path was
  live-verified to root. See
  [the 169.001 follow-up](35-tpn236e-169001-static-2026-11-15.md) and
  [the RPC-injection note](42-tpn236e-43pus7608-rpc-injection-root-2026-11-21.md).
- [ ] Dump-only `sys_run` package test.
- [ ] `kerupm` update-mode verification and boot selection.
- [ ] `p1/p2` U-Boot/FIT metadata and secure-chain verifier.
- [ ] 8450 read-only inventory and `/swdl` persistence proof. The read-only
  comparison is still PLAN; `/swdl` persistence is REPORTED.
- [ ] Recovery engineering (Phase R). Backup and same-byte restore are done;
  corrupted-image restore, ISP/JTAG, and UART RX remain open.
- [ ] Boot-chain verifier and key map (Phase B). Partial maps exist in docs
  28, 29, 31, and 32.
- [x] Reusable kernel carrier (Phase K). The carrier is verified on the lab:
  load, KCFI set/get, self-buffer write/read, symbol reads, rollback, and
  reboot. See [Level 3.5: reusable kernel carrier](37-kernel-carrier-level-3-5.md).
- [x] First Level 3.5 payload: direct `nfsb_verify` patch. The pristine header
  returns 0, a modified signature returns `0xffffbf00`, and the patched
  function returns 0. Reboot restores the original. See
  [38](38-runtime-verifier-patch-2026-11-20.md).
- [x] NFSB mount-path check: `nvt_dm_check_nfsb` rejected a modified loop copy
  unpatched and accepted it after the patch (`NFSB header found and verified`).
  See [40](40-nfsb-mount-check-2026-11-20.md).
- [x] ndp_led PWM backlight: channel 0 duty dimmed and restored; reboot returns
  the default. See [39](39-ndp-led-pwm-backlight-2026-11-20.md).
- [x] Full `nvt_dm_setup_nfsb` dm mapping: `nvt_dm_setup_linear` and
  `nvt_dm_setup_nfsb` build the `linear` and `verity` targets; a loop copy
  mounts the stock SquashFS read-only. See
  [43](43-nfsb-dm-mapping-2026-11-22.md).
- [x] dm-verity data path: a modified data block verifies after a recomputed
  tree and header root digest; the stock tree/digest still returns EIO. See
  [44](44-nfsb-verity-data-path-2026-11-22.md).
- [x] Custom NFSB image: a host-built SquashFS + header/tree mounts read-only
  through the runtime setup. See
  [45](45-custom-nfsb-mount-2026-11-22.md).
- [x] Level 4 boot-chain map (read-only): the A/B pair, static
  VTBL/NVHC/U-Boot, encrypted XBoot, component trailers, and the eMMC
  boot-part switch. See [46](46-level4-boot-chain-map-2026-11-22.md).
- [x] A/B switch to slot 0: **TESTED-NEGATIVE.** Slot 0 fails `lnikauth`; the
  old slot 1/boot1 is the licensed pair; the recovery is p9 DBFG 2 and
  `EXT_CSD 0x50`. See [48](48-ab-switch-failure-2026-11-22.md).
- [ ] eMMC boot-selection recovery: write p9 DBFG 2 and `EXT_CSD 0x50`
  (programmer or shop). The TV remains in the XBoot loop.
- [ ] Corrupted-image restore (Phase R), the gate for a modified boot-area
  write.
- [ ] Dual-boot recovery slot (Phase D).
- [ ] Boot-chain write, only after R (Phase 4).
