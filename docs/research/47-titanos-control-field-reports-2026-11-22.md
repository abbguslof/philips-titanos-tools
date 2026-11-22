# Titan OS local control field reports: 55PML9019/12 and 77OLED759/12

Status: **REPORTED** (2026-11-22). External contributors tested these units.
This repo did not reproduce the results and draws no root conclusion from them.

Two community projects document local control on Titan OS firmware that the
lab unit does not run. The useful material is the control-surface map, the
pairing sequence, and the firmware quirks. The macOS project is MIT licensed;
the UC integration has no license file, so this note summarizes its public
findings without copying code.

- [daCream87/uc-philips-titanos](https://github.com/daCream87/uc-philips-titanos):
  Unfolded Circle Remote 3 integration for **77OLED759/12**, JointSpace 6.1.0,
  HTTPS/Digest pairing, power/volume/mute polling, and direct key commands.
- [bedirhanyildirim/philips-titan-os-55pml9019-remote](https://github.com/bedirhanyildirim/philips-titan-os-55pml9019-remote):
  macOS menu bar remote for **55PML9019/12** (`TPN248E`,
  `248.010.000.121`, Poland), with a Titan OS API reference, Titan OS MQTT,
  DIAL, YouTube Lounge, Wake-on-LAN, and DNS ad blocking.

## Reported units

| Model | Chassis | Firmware | Reported facts |
| :--- | :--- | :--- | :--- |
| 77OLED759/12 | not reported | not reported | JointSpace 6.1.0; HTTPS/Digest pairing; power, volume, mute; direct IP keys. |
| 55PML9019/12 | `TPN248E` | `248.010.000.121` | JointSpace 6.1; Nagra DRM, not Widevine; DMR/DLNA and WoWLAN enabled; Titan OS MQTT, DIAL, and YouTube Lounge available. |

Neither report covers root, persistence, boot-chain access, or recovery. Treat
them as control-surface reports only.

## Local endpoints

| Surface | Port | Use |
| :--- | :--- | :--- |
| JointSpace v6 | 1926 HTTPS, 1925 HTTP | Pairing, keys, power state, Ambilight, pointer. |
| Titan OS MQTT | 8883 MQTT v5 over TLS | App launch, keys, keyboard, installed apps, home state. |
| DIAL | 56789 HTTP, 56790 description | YouTube, YouTube Kids, Netflix, Amazon Instant Video. |
| Wake-on-LAN | UDP 9 | Power on from deep standby. |

The 55PML9019 report also lists 9013, 10108-10120 (DTS Play-Fi), 49152/49153
(UPnP DMR), and 58012 as open. Ports and services vary by firmware.

## JointSpace

- Pairing on the 77OLED759/12 uses `/6/system` discovery, `POST /6/pair/request`,
  a PIN, then `POST /6/pair/grant` with the HMAC-SHA1 signature and HTTP Digest.
  The 55PML9019 report describes the same sequence and notes that the
  `ha-philipsjs` shared key works while the older `pylips` key does not.
- Do not probe with the new Digest credentials immediately after `pair/grant`.
  The 77OLED759/12 report found that Titan OS may not accept them at once.
- `GET /6/system/reboot`, then `GET /6/system/restart`, is the reported restart
  path. Availability is firmware-dependent; the fallback is standby plus
  Wake-on-LAN.
- `/6/applications`, `/6/apps`, `/6/sources`, and `/6/favoritelist` return 403
  on the 55PML9019; `/6/activities/launch` returns 405. `POST
  /6/activities/browser {"url": ...}` returns 200 but does not open the URL.
- `GET /6/context` reports `level1` as `NetTv` on the home or app surface,
  `WatchExtension` on any HDMI input, and `WatchSatellite` on satellite.
- `GET /6/powerstate` can report `On` while the TV is in quick standby. Use
  reachability, `channels/state`, or Wake-on-LAN instead of power state alone.
- `POST /6/audio/volume` can reflect a dead internal speaker on a soundbar
  setup. Volume keys over HDMI-CEC worked on the reported unit.

### Ambilight Off

The 55PML9019 report found that `POST /6/ambilight/power {"power":"Off"}`,
`currentconfiguration {"styleName":"OFF"}`, and the `AmbilightOnOff` key are
accepted but ignored. The working path is the settings tree:

```json
POST /6/menuitems/settings/update
{"values":[{"value":{"Nodeid":300,"Controllable":true,"Available":true,
  "string_id":"MLM_PHM_KEY_MAIN_AMBILIGHT_STYLE","data":{"activenode_id":310}}}]}
```

Node 300 children reported: 310 Off, 320 Follow video, 330 Follow audio,
340 Follow colour, 360 Follow app. Read the current tree with `POST
/6/menuitems/settings/current {"nodes":[{"nodeid":300}]}` before writing.

### Stability

The 55PML9019 report documents two failure modes:

- JointSpace wedges under bursts of requests and large list dumps. Space calls
  out, reuse the Digest challenge, and do not poll it for routine state.
- The server can answer 404 to every path while MQTT and DIAL keep working.
  Only a power cut restored it in the report.

Home Assistant users report similar behaviour in
[home-assistant/core#156776](https://github.com/home-assistant/core/issues/156776).

## Titan OS MQTT

The 55PML9019 report reverse-engineered the Titan OS Mobile app protocol. It is
MQTT v5 over TLS on 8883, with a server certificate chaining to a TitanOS root
CA; no client certificate is used. Pairing is anonymous, `pairing/start` with
`{"type":"mobile"}`, a 4-digit PIN, then `pairing/finish` with
`hex(HMAC-SHA256(PIN, challenge))`.

Requests subscribe to `<topic>/<uuid>` and publish with MQTT 5 `ResponseTopic`
and `CorrelationData`. Useful topics:

| Topic | Payload | Use |
| :--- | :--- | :--- |
| `deeplink` | `{"app_code":"<code>","url":"<url>"}` | Launch an installed app. |
| `rc` | `{"key_code":<linux keycode>}` | Remote keys. |
| `keyboard` | `{"opcode":0,"text":"a"}` | Type one character; opcode 1 is backspace. |
| `proxy` | `/v1/me/user_apps`, `/v1/me/favorites`, `/v1/me/watchlists` | TV-side account and app list. |
| `channels/state` | retained | `launcher` on the home screen, `inactive` otherwise. |

Reported keycodes: OK 352, Back 158, Home 102, Up 103, Down 108, Left 105,
Right 106, Volume+ 115, Volume- 114, Mute 113, Power 116, Play 207, Pause 119,
Play/Pause 164, Stop 128, Options 357, Quick menu 139, Sources 394, TV guide
365, Channel+ 402, Channel- 403, colour keys 398-401, and KEY_TV 377.

The `settings` topic only implements `tvname.get/set` and `wowlan.get/set` on
the reported unit. `automation/set` and `screenshot` did not reply for a
mobile-paired client.

## DIAL

`GET http://<tv>:56789/apps/<Name>` reports state; `POST` launches. Registered
apps on the reported unit: `YouTube`, `YouTubeKids`, `Netflix`, and
`AmazonInstantVideo`. The TV enforces a per-app `Origin` header: YouTube uses
`https://www.youtube.com`, Netflix uses `https://www.netflix.com`, and Prime
needs none. Without the header the request returns 403.

## Sources and inputs

Neither report found a source API. The 55PML9019 report walks the Sources
drawer with MQTT `rc` keys instead. The drawer order was Satellite, Antenna,
Streaming, Screen mirroring, USB, Network, HDMI 1-4; focus starts on the
current source and does not wrap. The macro is Home, wait, Sources, wait, then
Down/Up and OK. Do not confirm Screen mirroring: the TV leaves the network in
Miracast mode.

## Network and DRM

- The 55PML9019 report lists `smartadserver.com`, `sascdn.com`, `equativ.com`,
  and `thinkanalytics.com` as ad or recommendation endpoints, plus legacy
  NetTV portal domains. It recommends not blanket-blocking `titanos.tv`, which
  also serves the app store and updates.
- The 55PML9019 uses Nagra DRM, not Widevine. Do not assume Widevine on a
  TPN248E unit.
- Wake-on-LAN to the Ethernet or Wi-Fi MAC powers the TV from deep standby in
  about five seconds on the reported unit.

## What this does not establish

- Root, persistence, boot-chain access, or a recovery path on either model.
- A universal endpoint set. Titan OS firmware differs; probe your own unit.
- A source, channel, or app API. The reports use macros and fallbacks.
