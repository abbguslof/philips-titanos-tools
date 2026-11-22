# Security Policy

## What this project is

This repository documents and implements a **physical-access** jailbreak for a
television you own. The tested path is:

1. Format a USB stick as unlabelled FAT32 with an `autoscript.txt`.
2. Cold boot the TV with the stick inserted.
3. The vendor `quick_debug/menu auto` hook evaluates the script as root.
4. The script starts `telnetd` on `:2323` and opens one firewall rule.
5. Optionally install a persistence hook (`customer_env.sh`, or
   `/swdl/telnet/telnetd` on newer firmware) on a writable partition.

The root path does **not** exploit a remote network service. It requires the
attacker to have physical access, the ability to plug in a USB device, and the
ability to power-cycle the TV. The persistent hook requires root first.

## Supported scope

- **Tested:** Philips `55PUS8000/12`, chassis `TPA256E` / `TPN256E`, mainboard
  `715GD542`, firmware `TPA256E_V056.002.236.191`.
- **Not claimed:** that every other Philips model or firmware uses the same
  hooks, partitions, or firmware layout. The toolkit targets Titan OS on the
  Novatek NT72690 platform; verify each model before use.
- **Welcome:** reports and PRs for other models and firmware versions.
- **Not claimed:** remote exploitation, bypassing Widevine/DRM, or defeating
  hardware secure boot.

## Threat model

| Capability | Required access |
| :--- | :--- |
| Ephemeral root shell (`:2323`) | Physical USB + cold boot |
| Persistent root | Ephemeral root first, then write to `apdat` |
| Root via the USB flag, CDP, and RPC injection | One physical USB write (flag-file name only) + one warm reboot |
| Local JointSpace control | LAN access + pairing (or the vendor app secret) |
| Firmware inspection | Local copy of a package you obtained for your own device |

Pairing is not a security boundary on every build. A `70PUS8108/60`
(`TPN236E_V236.004.269.01`) field report found that `1926` accepted JointSpace
control requests without authentication, despite advertising
`digest_auth_pairing`. Treat the TV's LAN as trusted and verify the live build
before relying on pairing. See [the field report](docs/research/33-tpn236e-70pus8108-network-surface-2026-11-14.md).

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

## Vendor debug ports

The tested lab runs the Opera/Chromium browser with
`--remote-debugging-port=7788` and the boot firewall allows 7788. That is a
local debugging surface. Do not expose it to the internet; if you do not need
it, block it at the router or in the TV firewall. It is not a remote root path
by itself.

The `70PUS8108/60` and `43PUS7608/12` TPN236E field units had `:7788` closed
on the default boot, including while the browser was running. On the 169.001
image a physical USB `nbrowser_log_to_file` flag can enable it on the next
browser launch; that is local/physical, not remote. The same unit was then
live-verified through the launcher RPC bridge: an unquoted advertising-ID value
runs a shell command as `idtv`, and `customer_env.sh` grants root on reboot.
A later boot with the stick removed reproduced root and both listeners, so the
physical USB step is needed once, not every boot. See
[the corrections note](docs/research/36-tpn236e-169001-corrections-2026-11-16.md)
and [the RPC-injection note](docs/research/42-tpn236e-43pus7608-rpc-injection-root-2026-11-21.md).
Do not assume the lab's debug port is present on another build.

## Reporting a vulnerability

Private vulnerability reporting is enabled for this repository. Use the
[private report form](https://github.com/abbguslof/philips-titanos-tools/security/advisories/new).
Do not open a public issue or Discussion for a security report. For setup or
model questions, use Q&A instead.

Please report:

- accidentally committed credentials or real device identifiers;
- a payload that can damage hardware outside the documented restore path;
- a documentation error that could make a reader brick a device;
- a security issue in the tooling itself (for example, a USB builder path
  traversal or an unsafe format target).

Include:

- the repository version or commit;
- the affected file, tool, or path;
- reproduction steps and impact;
- the closest [CWE](https://cwe.mitre.org/). GitHub requires a CWE on the
  private report. Pick the nearest match; if none fits, choose the closest
  general class and explain why in the description. Do not delay the report
  over the classification.
- the model, chassis, and firmware if the issue is device-specific. Redact
  serials, MACs, SSIDs, pairing credentials, and private IPs unless they are
  necessary for the private report.

This is a volunteer project. Triage happens through the private advisory.
Security fixes target the current `main` branch and the latest release; older
tags are not backported by default.

GitHub may rate-limit report submissions (currently 10 per day for this
repository). If the form is unavailable or rate-limited, contact the
maintainer through the profile linked on the repository. Do not put real
serial numbers, MAC addresses, SSIDs, pairing credentials, or private IP
addresses in a public issue.

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
