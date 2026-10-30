# Security Policy

## What this project is

This repository documents and implements a **physical-access** jailbreak for a
television you own. The verified path is:

1. Format a USB stick as unlabelled FAT32 with an `autoscript.txt`.
2. Cold boot the TV with the stick inserted.
3. The vendor `quick_debug/menu auto` hook evaluates the script as root.
4. The script starts `telnetd` on `:2323` and opens one firewall rule.
5. Optionally install a persistent `customer_env.sh` hook on the writable
   `apdat` partition.

The root path does **not** exploit a remote network service. It requires the
attacker to have physical access, the ability to plug in a USB device, and the
ability to power-cycle the TV. The persistent hook requires root first.

## Supported scope

- **Verified:** Philips `55PUS8000/12`, chassis `TPA256E` / `TPN256E`, mainboard
  `715GD542`, firmware `TPA256E_V056.002.236.191`.
- **Not claimed:** other models, other firmware versions, remote exploitation,
  bypassing Widevine/DRM, or defeating hardware secure boot.

## Threat model

| Capability | Required access |
| :--- | :--- |
| Ephemeral root shell (`:2323`) | Physical USB + cold boot |
| Persistent root | Ephemeral root first, then write to `apdat` |
| Local JointSpace control | LAN access + pairing (or the vendor app secret) |
| Firmware inspection | Local copy of a package you obtained for your own device |

The USB autorun is a vendor diagnostic feature, not a remote vulnerability. The
persistent hook is a normal writable-partition startup hook.

## Responsible use

- Use this only on hardware you own or are authorised to modify.
- Keep a recovery stick and a known-good NVM/EDID backup.
- Do not deploy this against third-party devices, rental units, or shared
  displays.
- Do not use the tooling to bypass content protection or to build a botnet.

## Disclosure

This is independent right-to-repair research, not a vendor security advisory.
The project does not claim that Philips or TP Vision were contacted before
publication. If you are a vendor representative and want to discuss the
findings, open a private security report or contact the maintainer through the
repository profile.

If you find a **remote** vulnerability in a Philips/Titan OS device, report it
to the vendor first. This repository is about physical-access research.

## Reporting a problem in this repository

Please report:

- accidentally committed credentials or real device identifiers;
- a payload that can damage hardware outside the documented restore path;
- a documentation error that could make a reader brick a device;
- a security issue in the tooling itself (for example, a USB builder path
  traversal or an unsafe format target).

Open a private security advisory on GitHub, or contact the maintainer through
the profile linked on the repository. Do not paste real serial numbers, MAC
addresses, SSIDs, pairing credentials, or private IP addresses into a public
issue.

## Secrets and redaction

The public tree must not contain:

- real TV serial numbers, MAC addresses, SSIDs/BSSIDs, pairing PINs, or
  `.jointspace_credentials.json`;
- real home/public IP addresses or workstation usernames;
- private keys or generated TLS certificates;
- raw packet captures or multi-megabyte logs with device identifiers;
- vendor firmware packages or extracted vendor filesystems.

Examples use documentation addresses (`192.0.2.0/24`), documentation MACs
(`02:00:00:00:00:00`), and placeholder serials. See
[`evidence/REDACTION.md`](evidence/REDACTION.md).

## Restore and recovery

The ephemeral path is restored by removing the USB stick and cold booting. The
persistent path is restored by removing the hook (see
[`docs/guides/restore-to-stock.md`](docs/guides/restore-to-stock.md)). The
documented paths do not write to the read-only rootfs or to bootloader
partitions. A malformed `init=` or bootloader experiment can still brick a unit;
do not attempt one without a proven recovery path.
