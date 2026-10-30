# What you can do once you have root

Status: **VERIFIED** for the root path; the items below are capabilities, not
guarantees that every firmware build exposes the same files.

The USB autoroot path gives an interactive `uid=0` shell in the vendor
`initrc_t` domain. From there you can:

## Inspect the live system

- Read `/proc/cmdline`, `/proc/mounts`, `/proc/tty/driver/serial`, and the
  partition map.
- Dump or verify the NVM environment (`p9`), EDID, and channel maps before you
  change anything.
- Inspect the read-only `ap0`/`apext0` filesystems, the native `idtv` UI, the
  Opera/Chromium browser, the local keyboard assets, and the `/swdl` partition.
- Read the vendor startup scripts (`S21idtv.sh`, `run.sh`, `run_custom_impl.sh`)
  and the app manifest (`nvt.app.ini`).

## Back up and restore

- Dump `SAM/nvm_ubootdat.data`, `SAM/nvm_edid.data`, and
  `PhilipsChannelMaps/`.
- Verify the dual CRC32 NVM container and the CRC-16/MODBUS channel index.
- Restore NVM/EDID through SAM if an experiment goes wrong.

## Parse and inspect firmware

- Walk the `TIMG`/`PIMG` container, verify component MD5s, decompress
  `enc=gzip`, strip the `NFSB` header, and mount the SquashFS filesystems.
- Inspect the rootfs, `mtd_apexe`, and the browser/UI partition without
  flashing anything.

## Control the TV locally

- Use JointSpace for keys, volume, input switching, screen state, and storage.
- Use Ambilight `expert` mode for per-LED RGB injection and
  `/6/ambilight/processed` for live color telemetry.
- Explore the Titan OS webview, OIPF objects, loopback behaviour, and the
  developer D-pad sequences.

## Run your own code at boot

- Start a one-shot root shell from a USB cold boot.
- Install a reversible `customer_env.sh` persistence hook that starts your own
  userspace service.
- Use the vendor `/swdl` overlay or `/mtd_rwarea/apdat` for local UI/config
  experiments.

## Build on it

- Add a local dashboard, a local keyboard path, input remapping, telemetry
  sinks, or a service supervisor.
- Keep the stock panel, tuner, HDMI, picture/audio pipeline, Widevine L1, and
  Novatek VPU path intact.

The public repo stops at research and root. Product/custom-OS work is a separate
project; this repo gives you the verified starting point and the recovery path.
