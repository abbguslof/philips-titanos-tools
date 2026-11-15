# 70PUS8108/60 (TPN236E): network surface and JointSpace 6.1

Status: **REPORTED** on hardware by an external owner on 2026-11-14, including
a same-day correction. The maintainer has not reproduced it. Read-only probes,
plus owner-approved `VolumeUp` executions.

This note records a field report for a 2023 Titan OS unit that is not the lab.
It tests the rest of the family against the `55PUS8000/12` reference. It is not
a root path and does not claim a remote exploit.

> **Correction (2026-11-14).** The first version of this note said every `POST`
> returned `503` and did not execute, and that `/6/pair/grant` succeeded despite
> a `503`. The follow-up retracts both. The `503` was a `curl --digest` artifact:
> curl sends a bodyless, unauthenticated probe first; this TV never issues a
> `401` challenge and answers a bodyless POST with `503`, so curl aborts before
> sending the body. With a body, `POST /6/input/key` returns `200` and executes.
> Pairing was not demonstrated, and this build does not enforce it on `1926`.

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

- GET/HEAD requests, TCP connect scans, and owner-approved `VolumeUp` POSTs from
  a Windows 11 LAN client.
- No firmware was flashed, no USB stick was used, no settings were changed.
- The owner approved the `VolumeUp` executions used to prove POST behavior.
- The original PIN pairing was not confirmed to complete. The follow-up treats
  pairing as not required on this build; see [Pairing](#pairing).

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

The follow-up re-tested these GETs on `1926` with **no credentials**; all
worked. On `1925`, only `/6/system` worked unauthenticated; other GETs returned
`403`.

### Blocked and missing

| Endpoint | Result |
| :--- | :--- |
| `/6/applications`, `/6/sources`, `/6/volume`, `/6/notify` | `403` (first pass) |
| `/6/audiodata` | `404` |
| `/6/ambilight/lampsettings`, `/6/ambilight/processedlayerinformation`, `/6/ambilight/measuredlayerconfiguration`, `/6/ambilight/speed`, `/6/ambilight/brightness` | `404` |
| `GET /6/menuitems/settings/current` | `404` |

The `403` row is from the first pass. The follow-up re-tested only the working
GETs above on `1926`; it did not re-test `/6/sources`, `/6/volume`,
`/6/applications`, or `/6/notify`, so their `403` status stands as reported.
`/6/applications` is an engineering route behind the same `tvtype: consumer`
gate as the lab unit. Do not assume the lab client's source switching works
there.

### POST behavior and the 503 artifact

The first report concluded that POSTs returned `503` and did not execute. That
was wrong. The `503` was a client artifact from `curl --digest`: curl sends a
bodyless, unauthenticated probe first and waits for a `401` plus
`WWW-Authenticate` challenge. This TV never sends that challenge; it answers a
bodyless POST with `503`, so curl aborts before sending the body.

With a plain POST (no `--digest`) on `1926` and the JSON body, the request is
accepted and executes:

```http
POST /6/input/key HTTP/1.1
Host: <TV_IP>:1926
User-Agent: curl/8.13.0
Accept: */*
Content-Type: application/json
Content-Length: 18

{"key":"VolumeUp"}
```

```http
HTTP/1.1 200 OK
Date: Sat, 14 Nov 2026 19:56:39 GMT
Content-type: text/html; charset=utf=8
Cache-Control: no-cache
Access-Control-Allow-Origin: *
Content-Length: 58

<html><head><title>Ok</title></head><body>Ok</body></html>
```

`GET /6/audio/volume` returned `current: 1` before the POST and `current: 2`
after. No `Server` header and no `WWW-Authenticate` were observed on any
response. The `charset=utf=8` value is reproduced as reported, not corrected.

The failing probe, for contrast:

```http
POST /6/input/key HTTP/1.1
Host: <TV_IP>:1926
User-Agent: curl/8.13.0
Accept: */*
Content-Type: application/json
Content-Length: 0
```

```http
HTTP/1.1 503 Service Unavailable
Content-type: text/html; charset=utf-8
Content-Length: 92
```

The same empty-body `503` appeared for `POST /6/audio/volume`,
`POST /6/pair/grant`, and `POST /6/menuitems/settings/current` in the first
pass. Those paths were not re-tested with a body. `POST /6/input/key` is the
verified execution.

An invalid key (`{"key":"Invalid"}`) also returns `200` "Ok"; the TV ignores
the key.

`tools/jointspace_client.py` now treats a non-JSON 2xx body as success and
returns the body text. It does not require a completed pairing to send a key on
this build.

### Authentication is not enforced

On `1926`, the tested GETs and `POST /6/input/key` work with no credentials.
The follow-up compared a harmless no-op POST (`{"key":"Invalid"}`):

| Request on `1926` | Result |
| :--- | :--- |
| No `Authorization` header | `200` "Ok" |
| `Authorization: Basic <valid pairing creds>` | `200` "Ok" |
| `Authorization: Basic <wrong user:pass>` | `200` "Ok" |
| `Authorization: ZZZZ garbage-token` | `200` "Ok" |

No `401` and no `WWW-Authenticate` were observed. On `1925`, GETs other than
`/6/system` and POSTs with a body return `403`, with or without credentials.

So the advertised `pairing_type: digest_auth_pairing` and
`secured_transport: true` are not enforced on the tested build. The `1926`
control surface is open on the LAN. This is not a root path; it is an
unauthenticated local control surface. The owner should treat the LAN as
trusted. The repo's threat model assumes local JointSpace needs pairing; this
build is an exception.

### Pairing

The first report's "pairing succeeded despite `503`" is withdrawn. The grant's
first request was a bodyless probe and got `503`; a completed handshake was not
demonstrated. Because `1926` does not enforce authentication, later requests
working does not prove pairing. Whether a body-bearing `/6/pair/grant` completes
is untested.

After an expired or unconfirmed grant, a new `/6/pair/request` returned
`CONCURRENT_PAIRING` for 20-30 s before the session cleared; a later retry
succeeded. That is recorded as observed, but it does not prove a completed
pairing.

### DIAL

`GET /apps/<Name>` returned `200` for `YouTube`, `YouTubeKids`, and
`AmazonInstantVideo`, with the same origin enforcement as the lab unit:
`Netflix` returns `403` without the correct `Origin`, and unregistered names
such as `Disney` and `Max` return `404`.

## Entry-vector assessment

- No **root** entry vector was found in the tested set. The open `1926` API can
  send keys, change volume, and read Ambilight state; it does not provide a
  shell, file access, or code execution.
- The first report's "no network entry surface" was too broad. The control
  surface is open; it is not a root path.
- This does **not** prove that the USB `quick_debug/menu auto` autoroot chain is
  absent. The reporter expects that chain to be absent on the 2023 family based
  on the earlier TPN236E static analysis (issue #3); this report did not insert
  a USB stick or test the boot hook.
- The closed `8883` removes the MQTT mobile-control listener as an alternative
  control surface on this unit. If it holds across the family, it narrows the
  options; it does not create an entry vector.
- The closed `7788` removes the browser CDP debug surface on this unit.
- The engineering routes tested (for example `/6/applications`) still returned
  `403`. The open `1926` surface is the consumer control API, not engineering.
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
- Re-test `POST /6/audio/volume` with a body and `POST /6/pair/grant` with a
  body. The first shows whether the body rule is general; the second shows
  whether a completed pairing is possible at all.
- Confirm the unauthenticated `1926` surface and `8883`/`:7788` on another
  `TPN236E`/`TPN237E`/`TPN238E` unit before treating either as a family fact.
- The second TPN236E field report in
  [research/34](34-tpn236e-43pus7608-2026-11-14.md) has `:8883` and `:9080`
  open, uses `:49152`, and has `:7788` closed. The port surface varies within
  the family.
- Do not expose this unit to an untrusted LAN while `1926` accepts control
  requests without authentication. If the gap matters to the vendor, use the
  private-disclosure path in [SECURITY.md](https://github.com/abbguslof/philips-titanos-tools/blob/main/SECURITY.md), not this note.
- Test the USB hook only with the owner's agreement and the autoroot stick;
  record whether `quick_debug/menu auto` runs and stop before any boot-area
  write.
- A second external contributor parsed the public
  `TPN236E_236.006.135.001` VER40 package with 19/19 component MD5s OK on a
  fresh copy. See [the firmware container](03-firmware-container-timg-pimg-nfsb.md).
  Do not publish vendor firmware.

## Related

- [Firmware container](03-firmware-container-timg-pimg-nfsb.md)
- [43PUS7608/12 field scan and static notes](34-tpn236e-43pus7608-2026-11-14.md)
- [43PUS7608/12 169.001 artifact and static follow-up](35-tpn236e-169001-static-2026-11-15.md)
- [JointSpace API](08-jointspace-api.md)
- [Verified findings and dead ends](12-verified-findings-and-dead-ends.md)
- [Deep jailbreak roadmap](25-deep-jailbreak-roadmap.md)
- [55PUS8450/12 portability](27-8450-portability.md)

## Credit

Reported by an external owner on 2026-11-14; the report redacted the unit's
identifiers. Thanks for the read-only probes, the correction, and the precise
failure modes.
