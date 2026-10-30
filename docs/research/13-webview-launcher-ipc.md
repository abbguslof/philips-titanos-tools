# Webview, launcher, and native IPC

Status: **VERIFIED** for the runtime identity, OIPF objects, loopback behaviour,
BrowserIpcPluginClass from a plain HTTP origin, and the Developer Actions menu.
The other D-pad sequences are **INFERRED** from the launcher bundle.

## Runtime identity

The Titan OS UI is a Chromium webview, not a native Qt/C++ shell. The live
User-Agent was:

```text
Mozilla/5.0 (Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko)
Chrome/112.0.4147.62 Safari/537.36 OPR/46.0.2207.0 OMI/4.24,
TV_NT72690_2025_4K/056.002.236.191 (Philips, PUS8000, wireless) CE-HTML/1.0
NETTV/4.6.0.8 SignOn/2.0 SmartTvA/5.0.0 WhaleTV/2.0 TitanOS/3.0 en Ginga
```

That means:

- Chromium 112 / Opera 46 / OMI 4.24 on a 32-bit `armv7l` userspace.
- 1920x1080 viewport with `devicePixelRatio` 1.
- The launcher and virtual keyboard are cloud components from
  `app.titanos.tv` / `eu.app.titanos.tv`.

The sanitized capture summary is
[`samples/webview/webview-telemetry-summary.json`](../../samples/webview/webview-telemetry-summary.json).

## OIPF / HbbTV objects

A probe from a plain HTTP origin found:

- `application/oipfApplicationManager` — active; exposes `getOwnerApplication`,
  `onApplicationLoadError`, `onLowMemory`.
- `application/oipfConfiguration` — active.
- `application/oipfDrmAgent` — active; exposes `sendDRMMessage`.

`getOwnerApplication(window.document)` returned `null` outside an authorized
broadcast/AIT context. That is the normal OIPF isolation behaviour, not a bug.

## Loopback and SOP

From inside the TV browser:

| Port | Result |
| :--- | :--- |
| `127.0.0.1:1925` | open; JointSpace HTTP responds |
| `127.0.0.1:2323` | closed, immediate TCP RST (not firewall-dropped) |
| `127.0.0.1:4725` | closed, RST |
| `127.0.0.1:8080` | closed, RST |
| `127.0.0.1:9222` | closed, RST |

The firewall does not filter loopback, but a closed port still returns RST. This
is why the loopback bridge reaches unauthenticated JointSpace `/1/system` and
`/6/system`, but not the engineering routes.

A page loaded from `http://` cannot read `file:///proc/*` or `file:///etc/*`
(Same-Origin Policy). A `file://` page loaded from USB is a different origin and
was used for local diagnostics.

## Native `BrowserIpcPluginClass`

The launcher embeds:

```html
<object id="BrowserIpcPluginClass" type="application/browser-ipc-2"></object>
```

From a plain HTTP origin (`http://192.0.2.44:8080/ipc`), the object instantiated
as a normal `HTMLObjectElement`: 344 standard keys, **0 extra native methods**.
The OIPF objects were active, but the browser IPC plugin was inert. Native
plugin bindings are restricted to authorized origins; a plain HTTP page is not
one.

The sanitized reflection summary is
[`samples/webview/ipc-telemetry-summary.json`](../../samples/webview/ipc-telemetry-summary.json).

Do not assume the plugin is a shell bridge from an arbitrary origin. It is not,
on this build.

## Local keyboard and offline launcher

The smart launcher is cloud-loaded, but the browser and the native TV UI are not
empty shells. The `apext0` application partition contains:

| Component | What it is |
| :--- | :--- |
| `com.nvt.opera/browser_dir/virtual_keyboard_v2.pak` | Local virtual-keyboard assets used by the Opera/Chromium browser. |
| `com.nvt.opera/browser_dir/browser_ui/imeui.html` | Local IME UI. |
| `com.nvt.opera/browser_dir/jsplugins/liblocalui.so` | Local HTML UI plugin. |
| `com.nvt.opera/browser_dir/jsplugins/liblauncher.so` | Launcher plugin. |
| `com.nvt.opera/browser_dir/jsplugins/libbrowser_ipc_plugin2.so` | Browser IPC plugin. |
| `com.tpv.opera/browser_dir/pages/offlinelauncher/` | Local offline launcher (Home/TV Guide/Sources/Settings tiles). |
| `mframework/webui/PHI/page/pages/oskb/oskb.js` | Native TV UI on-screen keyboard. |
| `mframework/webui/PHI/page/pages/main/launcher.js` | Native TV UI launcher page. |

The earlier `DP_203` test blocked the cloud launcher origin; the launcher and the
input field that invokes the keyboard failed to render. The keyboard assets
themselves are local. A local UI replacement therefore has a local keyboard
path; the problem is making the local UI the primary UI, not inventing a
keyboard from scratch.

### Vendor `/swdl` overlay

`board/run_custom_impl.sh` checks `/swdl` early in boot and bind-mounts vendor
update payloads over the read-only application partition:

```sh
if [ -d "/swdl/UI/page" ]; then
    mount -o bind /swdl/UI/page /mtd_apexe/board/mframework/webui/PHI/page
fi
if [ -d "/swdl/com.tpv.opera" ]; then
    mount -o bind /swdl/com.tpv.opera /mtd_apexe/board/com.tpv.opera
fi
if [ -d "/swdl/com.nvt.opera" ]; then
    mount -o bind /swdl/com.nvt.opera /mtd_apexe/board/com.nvt.opera
fi
```

`/swdl` is a writable ext4 partition. This is a persistent, non-DNS injection
path for a local UI or browser configuration. The full list also includes
`framework-daemon`, `libnettvp.so`, `rpc_plugins`, and a telnetd/FTP update
service. Treat it as a vendor update surface; use it only with a recovery path.

## Developer Actions menu and sequences

The six-key launcher sequences all start with RED and end with BLUE. The
Developer Actions menu was verified on hardware:

```text
RED -> LEFT -> LEFT -> LEFT -> LEFT -> BLUE
```

It opens a modal with Launcher info, Toggle onscreen logs, Toggle player debug,
Reload launcher, and Service worker. The other 11 sequences are reversed from the
bundle but were not all exercised on hardware. See
[remote sequences](../reference/remote-sequences.md) for the full table and
status.

## TLS pinning and the cloud-shell dependency

Redirecting `eu.app.titanos.tv` to a local HTTPS server with a private CA
produced `DP_203` ("Cannot connect TV"). The webview rejects the private CA
and/or pins the core UI origin. While the origin was blocked, the launcher
stalled and the keyboard did not appear because the launcher/input field never
rendered. The local keyboard assets were still on disk; restoring DNS restored
the UI. This is a cloud-UI dependency, not a missing-keyboard problem.

Consequences:

- A DNS/TLS hijack is not a transparent MITM on this build.
- Breaking the cloud shell breaks text input, including in third-party apps that
  use the system keyboard.
- A local UI replacement has to solve the keyboard/input path, not just the
  visual launcher.

## Legacy tokens

`TPVisionDebug.cookie` and `enable_log2usb` are Android-era/legacy names. No
daemon on this Titan OS build references them; they produced no output. The
working diagnostic tokens are `need_usb_log`, `enable_usr_prinf`, and
`cert.pem`, which trigger the USB log dump described in
[USB autorun](05-usb-autorun-hook.md).

## Open questions

- Whether a trusted user CA can be injected from USB to defeat `DP_203`.
- Whether the browser IPC plugin can be reached from an authorized
  `https://*.titanos.tv` origin without breaking the UI.
- How to make the native `idtv` launcher or the browser's local
  `offlinelauncher` the primary home without the cloud app list.
- Which local UI the `liblocalui.so` / `liblauncher.so` plugins will accept, and
  whether `/swdl/UI/page` is the cleanest injection point.
