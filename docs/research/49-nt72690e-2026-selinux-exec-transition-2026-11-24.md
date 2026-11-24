# 55PQS8501/12 (TPN266E, NT72690E 2026): SELinux exec-transition bypass, and the display-layer wall that stops it short

Status: **VERIFIED (lab)** on owner hardware, single session. Root was
obtained through the published USB autoroot path on a **2026 model this repo
had not previously tested**, confirmed persistent, then used to probe an
SELinux policy question raised by this family's hardened, cloud-first
`idtv` launcher (see "Why this matters" below).

Target:

| Field | Value |
| :--- | :--- |
| Model | Philips `55PQS8501/12` |
| Chassis | `TPN266E` |
| Firmware | `TV_NT72690E_2026_4K/066.002.126.131` |
| Platform generation | Novatek **NT72690E** ("2026_4K" variant) — distinct from the `NT72690` family this repo otherwise documents |
| Scope | Owner-authorized; root obtained via the published USB autoroot path; no new persistence mechanism; no firmware write |

## Why this is a different platform generation, not the tested model

The USB autoroot path and `persist_root.sh`'s `/swdl/telnet/telnetd` variant
both worked unmodified on this unit. Everything downstream differs:

- `idtv`'s browser (`./bin/browser.out`, `com.tpv.opera`) loads **the cloud
  launcher** (`app.titanos.tv`, resolving to a CloudFront distribution) as its
  home content, not a local `mframework/webui/PHI/page/index.html`. The
  `/swdl/UI/page` override documented for the older family mounts over a path
  this build's `idtv` never navigates to; installing it does nothing harmful,
  but it also does nothing.
- Redirecting `app.titanos.tv` via `/tmp/resolv.conf` (the writable symlink
  target of the read-only `/etc/resolv.conf`) resolves correctly but has no
  effect on the browser's actual connection: the embedded Chromium
  (`Chrome/122.0.6261.128` in the browser's own engine process, reported
  separately from the embedding shell's `OPR/46.0.2207.0`/`Chrome/122.0.4147.62`
  user-agent string) does not consult the process's DNS configuration for this
  origin, consistent with built-in DNS-over-HTTPS.
- JointSpace (`:1925`) returns `403` on every route, including `/1/system`,
  unauthenticated. Pairing requires `PHILIPS_APP_SECRET`, which this repo does
  not ship and did not attempt to obtain for this note.
- The two Chromium instances on the box carry different build numbers:
  `nbrowser` (`com.nvt.opera`) reports `Chrome/112.0.4147.62`-era strings in
  its own UA; `idtv`'s engine process (`omi_worker` under
  `com.tpv.opera/bin/browser.out`) reports `Chrome/122.0.6261.128` to CDP.
  Treat any UA string from this family as naming one specific process, not
  the box.

## SELinux domains observed

`id -Z` on the root shell from `persist_root.sh` is
`system_u:system_r:initrc_t`. Key domains and their exec-labeled entrypoints,
read with `ls -Z`:

| Domain | Exec type (file label) | Example file |
| :--- | :--- | :--- |
| `initrc_t` | — | the root shell itself |
| `idtv_t` | `idtv_exec_t` | `run.sh`, `run_custom_impl.sh`, `wpa_supplicant`, `dbus-daemon`, most of `/mtd_apexe/board` |
| `appmgr_t` | `appmgr_exec_t` | `com.nvt.appmgr/com.nvt.appmgr` |
| `tpvopera_t` | `tpvopera_exec_t` | `com.tpv.opera/bin/browser.out`, `com.tpv.opera/browser_env.sh` |
| `nvtopera_t` | (not probed) | `com.nvt.opera` (the `nbrowser` role) |

`runcon system_u:system_r:appmgr_t id -Z` from the `initrc_t` shell returns
`Permission denied`: the policy has no `dyntransition` rule from `initrc_t`
to `appmgr_t`. This is the restriction the manual-transition tools
(`runcon`, and by extension anything that calls `setcon()` without a fresh
`execve()`) are built to respect.

## The bypass: `chcon` an ELF, then `execve()` it — never source it

`type_transition` rules fire on `execve()` of a file carrying the matching
exec type, independent of whether the calling domain could `dyntransition`
there. `chcon` succeeded on arbitrary files in this shell (confined only by
ordinary DAC permissions on `/tmp`, a tmpfs); the kernel enforces the
`execve()`-time transition on the file's **current** label, not on who put
that label there.

Two things have to be true for this to work, both found empirically:

1. **The exec target must be a real ELF, not a shebang script.** A `chcon`'d
   `#!/bin/sh` script run from `initrc_t` stayed in `initrc_t` — confirmed by
   writing a one-line script that does nothing but
   `cat /proc/self/attr/current > result`, relabeling it, running it, and
   reading the result. The kernel's LSM hook for a shebang script fires on
   the **interpreter** `execve()`, not on the labeled script text; busybox's
   own `ash` does not re-invoke the kernel's binfmt_script path per-file in a
   way that preserves the script's own label for this purpose. A relabeled
   copy of `busybox` itself (a real ELF), run directly, transitioned cleanly:
   `/path/busybox_as_idtv_exec_t sleep 5 &` produced a child whose
   `/proc/<pid>/attr/current` read `system_u:system_r:idtv_t`, confirmed
   before the `sleep` returned.
2. **The invoked binary must literally be named/dispatched as `busybox`** for
   busybox's own applet lookup to work when exec'd this way; a copy named
   anything else, called as `that_name <applet>`, returned `applet not
   found` from busybox's own argv[0] dispatch — nothing to do with SELinux,
   easy to misread as a policy denial.

Chained two hops deep, from the `initrc_t` shell:

```sh
cp /path/to/busybox /tmp/sel_test/busybox_appmgr
chcon system_u:object_r:appmgr_exec_t /tmp/sel_test/busybox_appmgr
/tmp/sel_test/busybox_appmgr sh -c '
  cd /mtd_apexe/board/com.tpv.opera
  . ./browser_env.sh                 # now readable: appmgr_t can read tpvopera_exec_t files
  export LD_LIBRARY_PATH=...          # as in run_browser.sh
  echo DOMAIN: ; cat /proc/self/attr/current   # prints appmgr_t
  exec ./bin/browser.out --hw-gles --enable-memory-cache \
       --remote-debugging-port=7001 --ignore-certificate-errors \
       --remote-allow-origins=*
'
```

The first `execve()` (of the relabeled `busybox_appmgr`) transitions
`initrc_t -> appmgr_t`. The `exec ./bin/browser.out` inside the `sh -c`
string is a **second**, separate `execve()` of a file natively labeled
`tpvopera_exec_t` (unmodified — this is the real binary the box ships); from
`appmgr_t`, that transition is permitted, landing in `tpvopera_t` — the same
domain the production browser runs in, confirmed by reading
`/proc/<pid>/attr/current` on the box's own supervisor-launched instance for
comparison. Trying the single-hop version (`initrc_t` exec'ing
`tpvopera_exec_t` directly, or via a `chcon`'d **script** of either exec
type) failed at an earlier step every time: either the exec itself was
refused, or the process never left `initrc_t` and so failed exactly where
the unpatched shell always failed (see the companion note on `libdirect`
below).

One earlier, narrower symptom this explains: `./bin/browser.out` run
directly from the unmodified `initrc_t` shell fails to load
`libdirect-1.7.so.5` with `cannot enable executable stack as shared object
requires: Permission denied` — an SELinux `execstack`/`execmem` denial on
the `initrc_t` domain itself, not a property of the library. The same binary,
same library, launched through the two-hop chain above (ending in
`tpvopera_t`), loads cleanly. `setenforce 0` from `initrc_t` fails with
`Invalid argument` (`security_setenforce() failed`) — this kernel's SELinux
is not permissive-capable at runtime; the exec-transition path is the one
that worked, not a toggle.

## What the two-hop shell actually bought: a working CDP target, not a visible one

With the chain above and `--remote-debugging-port=7001` plus
`--remote-allow-origins=*` (Chromium rejects CDP WebSocket upgrades from an
unlisted origin otherwise — `--ignore-certificate-errors` alone does not
cover this), `:7001/json/version` and `:7001/json/list` answer normally
(after opening the port in `iptables`, which is `policy DROP` by default
with an explicit per-port allowlist — see the existing `:2323` rule
`persist_root.sh` installs as the pattern). A fresh instance opens its own
default local page, `file:///usr/opera/browser_dir/pages/ui/page/index.html`
(title `TPV TV`) — not the cloud launcher, because this fresh process never
received whatever the real `appmgr_t` supervisor sends over
`--static-config-socket-fd=3`/`--mojo-platform-channel-handle=4` to point it
at `app.titanos.tv`. `Page.navigate` over the `ws://.../devtools/page/<id>`
socket to an arbitrary `http://` URL on the LAN succeeds immediately and
`Page.captureScreenshot` on that target confirms the page renders pixel
-correct — tested with a hand-built HTML/CSS/JS page, screenshotted at
1280x720, matching exactly.

None of this touches `app.titanos.tv`'s TLS pinning or the engine's DNS-over
-HTTPS; it is a second, independent browser process with its own window, not
a hijack of the first one's navigation. That is also its limit:

- The real `idtv` supervisor (`appmgr_t`, confirmed by reading its own
  `/proc/<pid>/attr/current`) respawns its child within seconds of that
  child's death, racing any attempt to keep only the new instance alive.
- `.directfbrc` under `/mtd_apexe/board/etc/mp` configures exactly three
  DirectFB layers with a fixed stacking order:

  ```
  init-layer=0
  layer-stacking=upper
  init-layer=1
  layer-stacking=middle
  init-layer=2
  layer-stacking=lower
  ```

  and `wm=sawman` (DirectFB's window manager). A second `browser.out`
  instance, launched independently of whatever claims layer 0 at boot,
  renders to a small surface pinned to the top-left corner — visible through
  whichever part of the real foreground UI happens to be semi-transparent
  (observed through one specific ad creative's alpha-blended region; opaque
  UI elsewhere fully occludes it), confirmed by a full-content screenshot
  taken via CDP from that same surface at the moment it was only a sliver on
  the physical panel.
- Neither Chromium's own flags (`--window-size`, `--window-position`,
  `--start-fullscreen`) nor `DFBARGS=layer=0` changed this placement.
  `OPERA_EGL_SCREEN_SIZE`, `OPERA_VIDEO_WIDTH/HEIGHT`, `WAYLAND_OUTPUT_SIZE`,
  and the rest of the real supervisor's own environment (captured whole from
  `/proc/<supervisor-pid>/environ` and re-exported) also made no difference
  to placement, and separately made the fresh instance stop opening any
  default page at all — it sat with a live `omi_worker` and no top-level
  target, suggesting this build's `idtv` role expects its starting URL over
  the `static-config-socket-fd`/`mojo-platform-channel-handle` IPC rather
  than falling back to a default when that channel carries nothing usable.
  That IPC's framing was not reverse-engineered in this session.

Layer assignment for a DirectFB/SaWMan client is requested by the client
through the DirectFB API at window-creation time, not by an environment
variable read once at process start in the way `DFBARGS` is for some other
DirectFB options; finding (or patching) where `com.tpv.opera`'s embedding
code picks its layer would need either disassembly of
`com.tpv.opera/browser_dir` (or the DirectFB glue it links) or capturing and
replaying the real supervisor's IPC on fd 3/4, neither attempted here.

## Scope and what this is not

- **Not a local-UI replacement.** The goal going in was to put a
  locally-hosted page on screen in place of the cloud launcher. That did not
  happen; this note documents how far the access goes and exactly where it
  stops, not a working alternative launcher for this model.
- **Not a new root path.** Everything here runs after the published USB
  autoroot path and `persist_root.sh`'s existing `/swdl/telnet/telnetd`
  variant; no new privilege was gained relative to a telnetd root shell
  that already exists on hardware this repo supports.
- **The `execve()`-vs-`runcon()` distinction is general SELinux behavior,**
  documented in SELinux's own policy semantics (a `type_transition` rule
  fires on `execve()` of a matching file type; `dyntransition`/`setcon()` is
  a separate permission class a policy can grant or withhold independently)
  and in general write-ups on relabel-then-exec workflows. What was not
  found anywhere public, searched before writing this note, is this
  technique applied to Titan OS, to the `NT72690E` 2026 platform generation,
  or to the `appmgr_t`/`tpvopera_t`/`idtv_t` domain names; none of those
  strings returned anything relevant. Titan OS publishes a coordinated
  vulnerability disclosure policy at `titanos.tv/security`; this finding's
  practical impact is bounded by the same physical-USB-root prerequisite as
  everything else in this repo, so it is recorded here rather than filed
  there, but a maintainer who disagrees with that call should feel free to
  file it.
- **Restore:** nothing here writes outside `/tmp` (tmpfs, cleared on
  reboot) and the ordinary iptables `INPUT` chain (one `ACCEPT` rule for the
  test port, removed in the same session). A cold boot alone clears every
  trace. No `/swdl`, `/mtd_rwarea`, or squashfs path was modified for this
  note beyond the already-documented `persist_root.sh` hook.

## Open questions

- Whether the `static-config-socket-fd=3`/`mojo-platform-channel-handle=4`
  IPC can be captured from the real supervisor and replayed to a
  two-hop-launched instance, giving it a real startup URL and — if layer
  assignment turns out to ride along with that same handshake — the primary
  display layer.
- Whether `com.tpv.opera`'s DirectFB layer request is a compile-time
  constant, a value read from `nvt.app.ini` or another config file on the
  read-only partition, or itself supplied over that same IPC channel.
- Whether killing (rather than out-racing) the `appmgr_t` supervisor itself,
  not just its browser child, changes respawn behavior enough to let a
  replacement claim layer 0 cleanly — not attempted, since the supervisor
  also owns remote-input handling and other services this session did not
  want to risk losing mid-test.
- Whether this model's JointSpace 403-on-everything is a firmware default or
  specific to this unit's pairing state; not re-tested with a second unit.
