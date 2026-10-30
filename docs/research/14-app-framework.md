# App framework and startup surface

Status: **VERIFIED** statically from the extracted `ap0` and `apext0`
partitions. This page describes how the stock software is put together; it does
not propose a custom UI.

## `run.sh` and `appmgr`

`/mtd_apexe/board/run.sh` prepares the environment, starts background daemons,
and eventually runs:

```sh
LD_PRELOAD=liberrLib.so /mtd_apexe/board/com.nvt.appmgr/com.nvt.appmgr \
  --applist=/mtd_apexe/board/data/nvt.app.ini
```

`nvt.app.ini` is the app manifest. Relevant entries:

| App | Program | Role |
| :--- | :--- | :--- |
| `idtv` | `mframework/tvfw/core/framework-daemon` | Native TV framework; default app, foreground. |
| `nbrowser` | `com.nvt.opera/nvt_opera_wayland.sh` | Opera/Chromium browser (background). |
| `webui` | shortcut to `nbrowser` | Web UI shortcut. |
| `browser` | shortcut to `nbrowser` | URL browser shortcut. |
| `tvstore` | shortcut to `nbrowser` | Store URL shortcut. |
| `generic` | shortcut to `nbrowser` | Generic URL shortcut. |
| `youtube` | `com.nvt.cobalt/run.sh` | YouTube/Cobalt. |
| `netflix` | `com.nvt.netflix/run.sh` | Netflix. |
| `primevideo` | `com.nvt.amazon/run.sh` | Prime Video. |

The `idtv` app is the native TV UI (`framework-daemon`). The cloud TitanOS home
is loaded by the Opera/Chromium browser (`nbrowser`/`webui`), not by the native
`idtv` framework.

## `apext0`: the browser and local UI assets

The `apext0` component contains `com.nvt.opera` and `com.tpv.opera`:

- `bin/nbrowser` — Opera/Chromium browser.
- `browser_dir/virtual_keyboard_v2.pak` — local virtual keyboard.
- `browser_dir/browser_ui/imeui.html` — local IME UI.
- `browser_dir/pages/offlinelauncher/` — local offline launcher with Home,
  TV Guide, Sources, Settings, and app tiles.
- `browser_dir/jsplugins/liblocalui.so`, `liblauncher.so`,
  `libbrowser_ipc_plugin2.so`, `libbrowser_ipc.so` — local UI, launcher, and
  browser IPC plugins.
- `browser_home/config.json`, `browser_home/url-filter.json` — browser home and
  URL policy.

The native `idtv` UI is served from
`mframework/webui/PHI/page/index.html`, with `pages/main/launcher.js` and
`pages/oskb/oskb.js` (the native on-screen keyboard).

## Vendor customization hooks

`run.sh` calls `run_n22070_vewd()` which sources `run_custom.sh` and runs
`run_custom_main()` -> `run_custom_impl.sh` -> `run_custom_impl_main()`.

`run_custom_impl.sh` checks `/swdl` and bind-mounts vendor update payloads over
the read-only application partition, including:

```sh
/swdl/UI/page              -> mframework/webui/PHI/page
/swdl/com.tpv.opera        -> com.tpv.opera
/swdl/com.nvt.opera        -> com.nvt.opera
/swdl/framework-daemon     -> mframework/tvfw/core/framework-daemon
/swdl/rpc_plugins          -> mframework/tvfw/rpc_plugins
/swdl/libnettvp.so         -> lib/nettv/libnettvp.so
```

`/swdl` is a writable ext4 partition. This is a persistent, non-DNS update
surface. It is also the cleanest place to experiment with a local UI or browser
configuration, provided you keep a recovery path.

## Why this matters

- The TV already has a native launcher and on-screen keyboard, and the browser
  ships local keyboard/offline-launcher assets. A local UI does not have to
  invent a keyboard.
- The cloud TitanOS launcher is an Opera web app; it is not the only UI on the
  device.
- `/swdl` is the vendor-supported place to override UI/browser components
  without modifying the rootfs or the secure boot chain.

See [webview, launcher, and IPC](13-webview-launcher-ipc.md) for the keyboard,
offline-launcher, and `/swdl` details.
