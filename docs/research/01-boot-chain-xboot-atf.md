# Boot chain: XBoot -> ATF -> Linux

Status: **VERIFIED** on `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`.

## Why this matters

The retail TV does not expose an interactive U-Boot prompt. It runs Novatek
**XBoot**, hands off to ARM Trusted Firmware (`a64m`), and enters the Linux
kernel at EL1 in roughly 90 ms. There is no countdown to interrupt, so
`bootdelay` in the NVM environment does not give you a shell.

## Observed chain

```text
XBoot rev: 2a4184c
  -> ARM Trusted Firmware a64m Rev: a6de2e4
  -> Linux kernel at EL1, entry 0x2800000
  -> init / Titan OS userspace
```

The serial capture in [`evidence/hardware/xboot-serial.log`](../../evidence/hardware/xboot-serial.log)
shows the early hardware init, panel power, DDR training, the `UMFG` signature
check, and the handoff. A representative excerpt:

```text
Novatek XBoot rev: 2a4184c
kconfig: n22074_tk_linux_sec_defconfig
build time: Aug 26 2025 17:54:05
NT72690 0
boot_area: 1
...
ADC8:0xb3
adc5:0x0
adc1:0xf5
...
[Secure] RPMB: 1, mode: 0
fdt_id_str = N22074_LINUX_TPV_4K_TC_2G
[DEBUG]uart mode:0, sign:UMFG
lnikauth pass !
...
Boottime: 90ms A64 Core1

B0
a64m Rev: a6de2e4
cpu0 el1_entry=2800000
B2
B3
cpu2 el1_entry=35cd290
cpu3 el1_entry=35cd290
```

`boot_area` and the ADC readings vary between boots (`ADC8` was observed across
`0xb1`–`0xb4`). Do not treat a single sample as a fixed strap value.

## `uart mode:0` and the kernel command line

The live kernel command line is:

```text
console=ttynull,115200 rootfstype=squashfs quiet maxcpus=4 rootwait
no_console_suspend earlycon=uart8250,mmio32,0xfd099000,baudrate=115200
nvt_pstore_mmc.blkdev=/dev/mmcblk0p36 page_pinner=on page_owner=on
root=/dev/mmcblk0p20 ro
```

The retail build replaces `console=ttyS0` with `console=ttynull`. The kernel
does not bind an interactive console to `ttyS0`, and the userspace getty on
`ttyS0` cannot be answered because RX never receives a byte (see
[Hardware SERV.U](07-hardware-serv-u.md)). `ttyS0` transmit still works: the
kernel and userspace write logs, and `tx` increments while `rx` stays 0.

## No interactive U-Boot

The NVM partition contains a U-Boot-style environment, but the boot chain does
not run an autoboot countdown. The practical consequences:

- Serial break, `Ctrl-C`, and character spam during power-on do not stop XBoot.
- `bootdelay=5` was accepted into NVM and survived a reboot, but it is inert for
  an interactive prompt.
- The `sign:UMFG` string is a vendor signature/mode marker; it is not a U-Boot
  prompt.

The `UMFG` offset and the distinction between the eMMC boot partitions and the
vendor `boot0` partition are covered in
[flash layout](02-flash-layout-and-partitions.md).

## Open question

The exact input that makes XBoot print `uart mode:0` is **not conclusively
proven**. The vendor script reads `UMFG` from `/dev/nvt-part-name/boot0` at
`0x1A0200` and exports `DEBUG_FUNC_LEVEL`, but the p1 slice contains value `0`
and the p2 slice contains value `1`; XBoot still reports mode 0. Treat hardware
ADC strapping and the vendor boot partition as candidates, not solved paths.
See [dead ends](12-verified-findings-and-dead-ends.md).
