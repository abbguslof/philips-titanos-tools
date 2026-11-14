# 70PUS8108/60 (TPN236E): network surface and JointSpace 6.1

Status: **REPORTED** on hardware by an external owner on 2026-11-14. Not
independently reproduced by this repo's maintainer. Read-only probes only.

This note records a field report for a 2023 Titan OS unit that is not the lab.
It tests the rest of the family against the `55PUS8000/12` reference and records
a JointSpace `POST` anomaly. It is not a root path and does not claim a remote
exploit.

## Target

| Field | Value |
| :--- | :--- |
| Model | Philips `70PUS8108/60` (Russia market) |
| Chassis | `TPN236E` from the firmware string; the API does not report a chassis |
| Firmware | `TPN236E_V236.004.269.01` (owner-reported from the TV UI) |
| Platform | 2023 Titan OS family; the earlier TPN236E package analysis is [here](03-firmware-container-timg-pimg-nfsb.md) |
| JointSpace | `6.1.0`, `os_type: Linux`, `tvtype: consumer`, `secured_transport: true`, `pairing_type: digest_auth_pairing` |
| DIAL | `dialVer 2.2`; device description on `:56790/dd.xml` |

The unit's LAN address, serial, MAC, PIN, and pairing credentials are redacted.
This note uses `<TV_IP>`.

## Scope

- GET/HEAD requests and TCP connect scans from a Windows 11 LAN client.
- No writes to the TV. No firmware was flashed, no USB stick was used, no
  settings were changed.
- The only state change was the standard JointSpace PIN pairing: request,
  on-screen PIN, HMAC-SHA1 grant, then Digest auth.

## Network surface

The report's targeted TCP connect scan:

| Port | Field unit | Lab `55PUS8000/12` | Notes |
| :--- | :--- | :--- | :--- |
| `1925` | open | open | JointSpace HTTP |
| `1926` | open | open | JointSpace HTTPS |
| `49153` | open | `49152` open | UPnP/DMR; the port differs by build |
| `56789`, `56790` | open | open | DIAL |
| `58012` | open | not reported | No HTTP response to `GET`; unidentified |
| `7788` | **closed** | open | Chromium/Opera DevTools |
| `8883` | **closed** | open | The `mqttv` listener on the lab unit |
| `8008`, `8009` | closed | open | |
| `9013`, `10108`-`10120` | closed | not reported | No DTS Play-Fi listener observed |
| `5555`, `55000` | closed | not reported | No ADB or service listener |
| `2222`, `2323` | closed | open | The lab ports are the persistent SSH/telnet payload, not stock |

Caveats:

- The lab unit runs a persistent root payload, so its `2222`/`2323`/`8088`
  listeners are not a stock baseline.
- A closed port on the tested address is not proof that a service is absent on
  every interface. The report lists a targeted scan, not a full inventory.
- Port `58012` answered the TCP connect but not HTTP; its protocol is unknown.
  Do not treat it as an entry vector.

## JointSpace 6.1 behavior

### Working GETs

- `/6/system` (also unauthenticated on plain-HTTP `1925`).
- `/6/powerstate` -> `{"powerstate": "On"}`.
- `/6/context` -> `{"level1": "WatchTv", ...}`.
- `/6/ambilight/topology` ->
  `{"layers": 1, "left": 4, "top": 11, "right": 4, "bottom": 0}`. This topology
  differs from the lab unit; record it, do not infer a universal LED count.
- `/6/ambilight/power` and `/6/ambilight/currentconfiguration`.
- `/6/audio/volume` -> `{"muted": false, "current": N, "min": 0, "max": 60}`.

`GET /6/audiodata` is **404** on this build. Volume is at
`/6/audio/volume`, which is also the path this repo documents.

### Blocked and missing

| Endpoint | Result |
| :--- | :--- |
| `/6/applications`, `/6/sources`, `/6/volume`, `/6/notify` | `403` |
| `/6/audiodata` | `404` |
| `/6/ambilight/lampsettings`, `/6/ambilight/processedlayerinformation`, `/6/ambilight/measuredlayerconfiguration`, `/6/ambilight/speed`, `/6/ambilight/brightness` | `404` |
| `GET /6/menuitems/settings/current` | `404` |

`/6/applications` is an engineering route behind the same `tvtype: consumer`
gate as the lab unit. The report does not explain the `403` on `/6/sources` or
`/6/volume`; do not assume the lab client's source switching works there.

### POST returns 503

Every tested `POST` returned HTTP `503 Service Unavailable`:

- `POST /6/input/key {"key":"VolumeUp"}`: `503`, no volume change on screen
  across 8 attempts spaced 1 s apart.
- `POST /6/audio/volume {"current":12}`: `503`, no effect; a later `GET`
  reported the old value.
- The other tested POST paths also returned `503`.

The exception is `POST /6/pair/grant`: it returned `503`, but the pairing
succeeded and the issued credentials authenticate correctly on later Digest
requests. On this build, `503` is therefore **not** a reliable indicator that a
POST did not execute. The cause is unknown and recorded as **OPEN**.

The repo's `tools/jointspace_client.py` raises on a non-2xx control response, so
a control command such as `key` will report an error on this build unless the
cause is understood. The pairing path already parses the grant body without
requiring a 2xx status.

### Pairing

The standard v6 flow works: `/6/pair/request` -> on-screen PIN ->
`/6/pair/grant` with the HMAC-SHA1 signature -> Digest auth.

After an expired or unconfirmed grant, a new `/6/pair/request` returns
`CONCURRENT_PAIRING` for roughly 20-30 s before the session clears; a later
retry succeeds.

### DIAL

`GET /apps/<Name>` returned `200` for `YouTube`, `YouTubeKids`, and
`AmazonInstantVideo`, with the same origin enforcement as the lab unit:
`Netflix` returns `403` without the correct `Origin`, and unregistered names
such as `Disney` and `Max` return `404`.

## Entry-vector assessment

- No network entry surface was found in the tested set.
- This does **not** prove that the USB `quick_debug/menu auto` autoroot chain is
  absent. The reporter expects that chain to be absent on the 2023 family based
  on the earlier TPN236E static analysis (issue #3); this report did not insert
  a USB stick or test the boot hook.
- The closed `8883` removes the MQTT mobile-control listener as an alternative
  control surface on this unit. If it holds across the family, it narrows the
  options; it does not create an entry vector.
- The closed `7788` removes the browser CDP debug surface on this unit.
- No engineering JointSpace route was reachable.
- The owner keeps the unit on its current build. Boot-chain or USB tests need a
  proven entry vector and the lab rules; they were out of scope.

## Regional note

The installed firmware `TPN236E_236.004.269.01` does not appear in the public
TPN236E changelog the reporter checked (which lists `236.004.169.001` as the
last `004.x` build). It looks like a Russia-market branch. That is
owner/community-reported, not verified here.

The owner reports that OTA updates are not offered even though newer builds
exist. Community context about the RU region, missing apps, and USB rollback is
unverified and is not a repo claim.

## Limits and next probes

- The report supplied no raw capture; the observations above are its summary.
  Only the maintainer can move a row to VERIFIED, and only on the same unit and
  firmware.
- Confirm `8883`/`:7788` on another `TPN236E`/`TPN237E`/`TPN238E` unit before
  treating the closed ports as a family fact.
- Characterize the `503`: capture the exact request and response headers
  (`WWW-Authenticate`, `Server`, body), compare `1925` and `1926`, and repeat a
  harmless POST after pairing. Do not assume execution from a `503`.
- Test the USB hook only with the owner's agreement and the autoroot stick;
  record whether `quick_debug/menu auto` runs and stop before any boot-area
  write.
- Parse a public `autorun.upg` for this model with
  `tools/firmware/parse_timg.py`. The VER40 parser is static and does not
  decrypt; do not publish vendor firmware.

## Related

- [Firmware container](03-firmware-container-timg-pimg-nfsb.md)
- [JointSpace API](08-jointspace-api.md)
- [Verified findings and dead ends](12-verified-findings-and-dead-ends.md)
- [Deep jailbreak roadmap](25-deep-jailbreak-roadmap.md)
- [55PUS8450/12 portability](27-8450-portability.md)

## Credit

Reported by an external owner on 2026-11-14; the report redacted the unit's
identifiers. Thanks for the read-only probes and the precise failure modes.
