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

## Model and firmware variance

The verified rows above are from the lab `55PUS8000/12` (`TPA256E`/`TPN256E`,
`TPA256E_V056.002.236.191`). Do not assume the same keys, ports, or endpoints on
another build.

A `70PUS8108/60` (`TPN236E`, `TPN236E_V236.004.269.01`) field report recorded:

- `GET /6/audio/volume` works; `GET /6/audiodata` is 404.
- `GET /1/system` on `1925` returns the same JSON as `/6/system`;
  `/5/system` is 404, and `/` and `/6/` are 403.
- `GET /6/sources`, `/6/volume`, `/6/applications`, and `/6/notify` are
  hard-blocked on `1926`: `403` with no credentials and with valid Basic
  credentials. No `401` or `WWW-Authenticate` is issued. This is feature
  removal, not an auth gate.
- `GET /6/debug`, `/6/devtools`, and `/6/timer` return 403; `GET /6/pair` and
  `GET /6/activities` return 404 on `1926`.
- On `1926`, the tested GETs and `POST /6/input/key` worked with **no
  credentials**, and no `401`/`WWW-Authenticate` challenge was ever issued.
  Basic auth with valid, wrong, or garbage credentials all returned `200`. The
  advertised digest pairing is not enforced on this build.
- `POST /6/input/key` with a JSON body returned `200` (`text/html` "Ok") and
  executed: volume changed 1 -> 2. `POST /6/audio/volume` with a body also
  executed: 12 -> 15 -> 12. A bodyless POST returned `503`. The first report's
  `503` was a `curl --digest` bodyless-probe artifact, not a TV-side refusal.
- The client now accepts a non-JSON 2xx body and returns
  `{"status_code": ..., "body": ...}`. Pairing is not required for control on
  this build.
- `8883` and DevTools `:7788` were closed on that unit; both are open on the lab
  unit. `:7788` stayed closed while the browser was running, and the same was
  seen on the `43PUS7608/12` TPN236E unit. The lab's `:7788` is model-specific.
- `58012` is silent to HTTP and waits for client data. SSDP discovery returned
  no response from the TV; the `49153` DMR description paths returned 404. See
  [the field report](33-tpn236e-70pus8108-network-surface-2026-11-14.md).
- A completed pairing was not demonstrated. After an unconfirmed grant,
  `/6/pair/request` returned `CONCURRENT_PAIRING` for about 20-30 s before a
  retry succeeded.

See [the TPN236E field report](33-tpn236e-70pus8108-network-surface-2026-11-14.md).
Status: **REPORTED**.

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
not included. See [SECURITY.md](https://github.com/abbguslof/philips-titanos-tools/blob/main/SECURITY.md).
