# Hardware `SERV.U`

Status: **VERIFIED** electrically and on the live TV. Interactive serial is
**TESTED-NEGATIVE** on this build.

## Connector

The external service connector is a white 3-pin header silkscreened `SERV.U`,
next to the 3.5 mm jack on the I/O cluster. It provides **no VCC**:

```text
[ 1 ]  UART RX   (input to TV; pulled up / electrically live)
[ 2 ]  GND
[ 3 ]  UART TX   (output from TV)
```

- Logic level: **3.3 V LVTTL**. Never connect 5 V TTL or RS-232 levels.
- Baud: **115200 8N1**, no flow control. 38400 produces framing noise.
- Pin 1 measured **3.3 V DC** to GND while powered idle. That proves the line is
  electrically live, not that the software consumes bytes.

## Raspberry Pi bridge

A Pi Zero 2 W works as a stable 3.3 V bridge. Disable Bluetooth so `serial0`
maps to the PL011 UART:

```bash
echo "dtoverlay=disable-bt" | sudo tee -a /boot/firmware/config.txt /boot/config.txt
echo "enable_uart=1"       | sudo tee -a /boot/firmware/config.txt /boot/config.txt
sudo systemctl disable --now serial-getty@ttyAMA0.service
sudo reboot
```

Wiring:

```text
TV SERV.U Pin 2 (GND)  <-> Pi Pin 6  (GND)
TV SERV.U Pin 3 (TX)   <-> Pi Pin 10 (GPIO15 / RXD)
TV SERV.U Pin 1 (RX)   <-> Pi Pin 8  (GPIO14 / TXD)
```

Read with `picocom -b 115200 /dev/serial0` or any raw reader. Do not run a
blocking terminal in an automated agent session; hand it to a human.

## What the serial port can and cannot do

**Can:** capture the full XBoot/ATF/kernel/userspace boot log. TX works. The
kernel and userspace write to it even when the console is `ttynull` in some
stages.

**Cannot:** give an interactive shell on this build. The live `ttyS0` counters
were `tx:4534 rx:0` before and after a 25-second raw read window while a human
typed. `rx` never moved. The inittab getty is present, but no byte reaches the
SoC.

## Break test

The Pi held TX low before AC power-on, released at 1.5 s, and spammed `\r`,
`\x1b`, `s`, space, and `Ctrl-C` for the first 200 ms. XBoot still handed off in
90 ms with no prompt. There is no serial break trap in retail mode.

## Boot log

See [`evidence/hardware/xboot-serial.log`](../../evidence/hardware/xboot-serial.log)
for the sanitized capture. The chain and the `uart mode:0` line are explained in
[boot chain](01-boot-chain-xboot-atf.md).

## Safety

- The logic board is low-voltage; mains is on a separate PSU board.
- Never inject 5 V or RS-232 levels into `SERV.U`.
- Do not attempt `init=` injection or bootloader experiments without a proven
  recovery path. Serial cannot rescue this build.
