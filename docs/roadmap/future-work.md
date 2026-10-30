# Future work (NOT VERIFIED)

> **Status: DESIGN ONLY.** Nothing below is implemented or verified on hardware.
> It is a direction list for future experiments. Do not treat it as a feature
> list or a support promise.

## Why this file exists

The verified root path makes persistent userland changes possible. The original
research notes contained two aspirational blueprints (custom OS/dashboard and a
Titan OS enhancement shim). They are merged here so the verified research stays
separate from the wishlist.

## Candidate directions

| Area | Idea | Prerequisite |
| :--- | :--- | :--- |
| Local UI | Serve a minimal local dashboard on `127.0.0.1` and map the Home key to it. | Replace/redirect the cloud launcher without breaking input. |
| Telemetry | Add on-device `/etc/hosts` or firewall sinks for known ad/ACR domains. | A persistent read-write layer; the rootfs is read-only. |
| Input remap | Intercept sponsored remote keys and map them to local actions. | A stable input event path and a userspace daemon. |
| Media | Run a local streaming service and point a kiosk webview at it. | Hardware decode integration and a browser/kiosk path. |
| Ambilight | Forward edge colors to WLED/Hyperion over UDP. | A stable color source and network output. |
| Companion | AirPlay/HomeKit/Moonlight bridges. | Extra binaries, licenses, and a persistent service manager. |
| Recovery | USB `RECOVERY_DISABLE_MODS.txt` bypass for custom shims. | A boot script that runs before the shims. |
| Overlay | Use `apol`/`fsol` overlayfs for a read-write rootfs. | Devicetree `ap_overlay` support and a recovery plan. |

## Constraints

- The rootfs is SquashFS read-only; persistent changes currently go to
  `/mtd_rwarea/apdat`.
- The `NFSB` RSA/SHA-256 layer is the secure-boot boundary. Do not assume a
  modified rootfs can be flashed back.
- There is no serial recovery on this build. Any boot-chain experiment needs a
  proven unbrick path first.
- The cloud launcher and virtual keyboard are remote components. Breaking their
  origin breaks input.

## What would make a direction "verified"

A future change should ship with:

1. a reproducible procedure;
2. the exact firmware/model it was tested on;
3. a redacted evidence log;
4. a restore path that does not require desoldering;
5. a note on what still does not work.
