# JointSpace API (ports 1925 / 1926)

Status: **VERIFIED** on hardware for discovery, pairing, keys, volume, and
Ambilight. Engineering routes are **TESTED-NEGATIVE**.

## Overview

JointSpace is the local Philips REST API:

- `http://<TV_IP>:1925` — unauthenticated device/system endpoints.
- `https://<TV_IP>:1926` — HTTPS with Digest auth after pairing.

`tools/jointspace_client.py` implements discovery, pairing, key injection,
volume, screen state, storage, and Ambilight. The TV's daemon is lightweight;
use a persistent `requests.Session` and do not open a new TLS connection per
request. The client already does this.

## Pairing

The v6 handshake uses HMAC-SHA1 over `timestamp + PIN`, with a base64 raw digest
(not the hex string) and exact casing `"auth_appId": "1"`.

The vendor application secret is **not** shipped in this repository. Supply it
for your own research:

```bash
export PHILIPS_APP_SECRET='<base64 vendor app secret>'
# or
export PHILIPS_APP_SECRET_FILE="$HOME/.philips-app-secret"
```

```bash
./tools/jointspace_client.py --host <TV_IP> pair
```

The TV displays a 4-digit PIN. Credentials are saved to
`.jointspace_credentials.json` (gitignored). Do not publish that file.

## Useful endpoints

| Endpoint | Auth | What it does |
| :--- | :--- | :--- |
| `/1/system`, `/6/system` | no | Model, serial, software version, API version. |
| `/6/network/devices` | Digest | Interfaces and MACs. |
| `/6/system/storage` | Digest | USB storage state. |
| `/6/screenstate` | Digest | Screen state; `"Off"` can mean eco screen-off while audio plays. |
| `/6/audio/volume` | Digest | Volume 0–60 and mute. |
| `/6/input/key` | Digest | Remote key injection. |
| `/6/ambilight/topology` | Digest | LED layout. |
| `/6/ambilight/processed` | Digest | Live RGB values from the video pipeline. |
| `/6/ambilight/mode` | Digest | `internal`, `expert`, `lounge`. |
| `/6/ambilight/cached` | Digest | Direct per-LED RGB injection in `expert` mode. |
| `/6/activities/browser` | Digest | Stub on Titan OS; does not launch a browser. |

## The `tvtype: consumer` wall

`/6/system` reports:

```json
"systemfeatures": {
  "tvtype": "consumer",
  "pairing_type": "digest_auth_pairing",
  "secured_transport": true,
  "os_type": "Linux"
}
```

The engineering routes (`/6/debug`, `/6/devtools`, `/6/diagnostics`,
`/6/applications`, `/6/directfb`) return **HTTP 403** from the LAN *and* from
`127.0.0.1`, with or without a `debug` pairing scope. This is not an IP ACL.
It is a userspace `tvtype` gate. Injecting `mds_mode=1` into NVM does not change
it; that was tested.

The loopback path is still useful for unauthenticated `/1/system` and for
observing that the firewall does not filter `lo`, but it does not unlock the
engineering routes.

## Ambilight

The TV has 16 LEDs: left 4, top 8, right 4, bottom 0. `expert` mode disables the
internal video override so you can address each LED through
`/6/ambilight/cached`. `internal` mode overwrites custom frames on the next
video tick.

See `tools/ambilight_controller.py` for the CLI and the local web studio. The
studio is a convenience UI; it is not required for the root path.

## Secrets and identifiers

The public repo uses placeholders for the TV IP, serial, MAC, and PIN. The
pairing credentials file, real device identifiers, and the vendor app secret are
not included. See [SECURITY.md](../../SECURITY.md).
