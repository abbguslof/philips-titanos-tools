# Network telemetry

Status: **VERIFIED** from a Pi-hole DNS audit and a local packet capture. Raw
captures are not published; this page contains the aggregate findings and
sanitized domain names.

## What the TV talks to

A 1,000-query sample from an idle/home-screen session showed four main groups:

| Group | Examples | What it is |
| :--- | :--- | :--- |
| Connected-TV ad bidding | `tiles.springserve.com`, `creatives.bidtheatre.com`, `tv.springserve.com`, `ads.viralize.tv`, `*.adnxs.com` | Real-time programmatic ad auctions as focus moves over the home UI. |
| FAST/SSAI | `*.titan.wurl.tv`, `*.mediatailor.us-east-1.amazonaws.com` | Free ad-supported channels and server-side ad insertion. |
| Telemetry/ACR | `dac-api-prod.tpv-analytics.com`, `events-prod01.eu.prod.titanos.tv`, `platform.cid.samba.tv`, `api.rollbar.com` | Device analytics, Titan events, Samba TV audio fingerprinting, frontend errors. |
| Connectivity watchdogs | `www.google.com`, `www.yahoo.com`, `clients3.google.com` | Captive-portal / online checks every 10–20 seconds. |

The smart launcher is a cloud-loaded web application (`app.titanos.tv`,
`eu.app.titanos.tv`). Blocking that origin breaks the launcher and the input
field that invokes the keyboard. The browser still ships local keyboard assets;
the failure is the missing cloud UI, not a missing keyboard binary. See
[webview, launcher, and IPC](13-webview-launcher-ipc.md#local-keyboard-and-offline-launcher).

## LAN port surface

Active probing from the LAN and from the TV's own browser showed:

| Port | LAN result | Notes |
| :--- | :--- | :--- |
| 22/tcp | filtered | No SSH listener. |
| 23/tcp | filtered | No telnetd by default. |
| 80/tcp | filtered | No HTTP listener. |
| 443/tcp | filtered | No HTTPS listener. |
| 1925/tcp | open | JointSpace HTTP. |
| 1926/tcp | open | JointSpace HTTPS. |
| 2323/tcp | filtered | No listener until the autoroot payload starts one. |
| 4725/tcp | filtered | No listener. |
| 7001/tcp | closed | RST, no service. |
| 7788/tcp | **open** | Opera/Chromium DevTools (CDP) on `0.0.0.0:7788`; the browser runs with `--remote-debugging-port=7788`. |
| 8008/tcp | open | Google Cast / Eureka. |
| 8009/tcp | open | Google Cast TLS. |
| 8080/tcp | filtered | No HTTP proxy/listener. |
| 9222/tcp | closed | No Chrome DevTools endpoint. |

Inbound non-standard ports are dropped by the boot firewall
(`iptables_conf.sh`: `-P INPUT DROP` plus an allowlist). Loopback is not
filtered, but a closed port still returns an immediate RST. This is why the
browser can reach `127.0.0.1:1925` but not a devtools port.

## OTA endpoints

Static analysis of `libnettvp.so` / `libapp.so` and the live traffic identify:

1. **DevicePortal ICP handler**
   `https://www.ecdinterface.philips.com/DevicePortalICPRequestHandler/RequestHandler.ashx`
2. **Domain discovery** `https://<dm-server>/v1/domains`
3. **Authentication** `https://<dm-server>/v1/authenticate` with a `DM key`
   header; returns a Bearer JWT.
4. **Potamoi component query**
   `https://<potamoi>/potamoi/v1/components/updates?interactive=<bool>`
   returns `component_id`, `name`, `latest_version`, `url`, `size`, `crc`.
5. **Download and execution** the updater hands the package to
   `/tmp/sys_run/run.sh` and `nvt_eburner`.

The update check itself is visible in the [firmware acquisition guide](../guides/firmware-acquisition.md).

## Update capture observations

A capture during `Settings -> Update Software -> Search for Updates` showed:

- mDNS hostname `n22074_linux_tk.local`.
- AirPlay advertisement on `_airplay._tcp` (port 7000).
- Google Cast advertisement on `_googlecast._tcp` (port 8009).
- DNS/TLS to Philips support/CDN and Titan endpoints.

The raw capture is not published because it contains the TV's device identifiers
and the local network layout.

## Blocking

[`tools/pihole/blocklist.txt`](../../tools/pihole/blocklist.txt) and
[`whitelist.txt`](../../tools/pihole/whitelist.txt) are a starting point for
network-level debloating. The blocklist is a compiled list of public smart-TV
telemetry/ad domains; verify upstream licenses before redistributing it. The
Titan OS cloud-shell domains (`app.titanos.tv`, `titanos.tv`) are commented out
by default because blocking them breaks the launcher and the on-screen keyboard.
Uncomment them only after you have a local UI replacement. The whitelist keeps
connectivity checks and streaming apps working.

Blocking is not a substitute for the on-device root path. It is useful for
reducing background load and telemetry while you plan deeper changes.

## TLS interception

Redirecting `eu.app.titanos.tv` to a local server with a self-signed certificate
failed with `DP_203` ("Cannot connect TV"). The webview rejects the private CA
and/or pins the core UI origin. Breaking that origin also breaks the virtual
keyboard. Do not expect a DNS hijack to be a transparent MITM on this build.
