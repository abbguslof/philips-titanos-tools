# 43PUS7608/12 (TPN236E) 169.001: USB flag, CDP, RPC injection, and root

Status: **REPORTED (live)** on owner hardware by the reporter of issues #6 and
#8, on the same unit as [doc 34](34-tpn236e-43pus7608-2026-11-14.md). The
maintainer has not reproduced it.

This note supplies the step that [doc 36](36-tpn236e-169001-corrections-2026-11-16.md)
left as an inference. A USB flag file opens CDP. The launcher page calls the
local JSON-RPC bridge. One RPC method passes an unquoted value to a shell as
`idtv`. The writable boot hook then runs as root. The reporter proved root on
two reboots with the stick and again on a later boot with the stick removed,
and byte-checked the anchors against the running image.

Target:

| Field | Value |
| :--- | :--- |
| Model | Philips `43PUS7608/12` (same unit as doc 34) |
| Chassis | `TPN236E` |
| Firmware | `TPN236E_236.006.169.001` (build date 2026-05-20) |
| Package | The externally verified 169.001 artifact in [doc 35](35-tpn236e-169001-static-2026-11-15.md) |
| Scope | Owner-authorized live testing; destructive RPCs avoided; advertising ID restored |

## Entry: the USB flag file

A FAT32 stick that contains only an empty file named `nbrowser_log_to_file`
opens CDP on `:7788` at the next browser launch after a warm reboot. Nothing on
the stick is executed. The returned banner is `Chrome/92.0.4515.159`, and
`Runtime.evaluate` runs in the launcher page target
(`file:///mtd_apdat/ui/page/index.html`).

The flag is an existence probe, not a token. Any local file with that name is
enough. CDP closes when the browser starts without the flag present.

## Bridge: launcher page to `idtv`

The launcher UI holds the JSON-RPC bridge at `ws://127.0.0.1:28001/jsonrpc`.
The serving app runs as uid 114 `idtv` in `idtv_t` with broad capabilities,
including `CAP_SYS_MODULE` and `CAP_SYS_ADMIN`. The `nvt.app.ini` `[apps]` entry
attributes the bridge to `framework-daemon`; that attribution is config-based,
not socket-mapped. Every documented `Rpc*` method is callable from the launcher
page.

## Sink: `setup.system.advertising.id.set`

The RPC method reaches a shell through the advertising-ID path:

| Step | Location | Observed behaviour |
| :--- | :--- | :--- |
| RPC handler | `CSetupPlugin::SetAdvertisingID` (libsetupplugin `0xa2d78`) | Reads the `adId` string from the RPC JSON. |
| Setter | `SocMwAppsMgr::SetAdvertisingID` (libsocmw `0xcf134`) | Calls `NUI_SETTING_SetIFAInfo`. |
| Format | libnui `0x252a98` | `snprintf` writes `(echo ADVERTISING_ID= %s && echo LMT_STATUS= disabled) > /tmp/adid` into 256 bytes. The `%s` is unquoted. |
| Exec | `_system_command` `0x1a91e8` | `vfork` + `execlp("/bin/sh", "-c", ...)` at `0x1a9298`. |

A value that closes the subshell and appends a command runs as `idtv`. The
`snprintf` budget leaves about 180 characters per call. Chained calls two
seconds apart append, which was enough to write `customer_env.sh` line by
line. The exec primitive was proven live by injecting `touch` and confirming it
with `RpcSystemCheckFileExist`.

This note deliberately omits a working payload string. The primitive is the
unquoted `%s` inside `(...) > /tmp/adid`; the mitigation is to stop using a
shell here.

## Root on reboot

The `idtv` process can write `/mtd_rwarea/apdat/customer_env.sh`, which is an
`idtv_data_t` path. `run.sh:333` sources that file as root on the next boot.
The reporter observed the following on each boot:

```
uid=0(root) gid=0(root) context=system_u:system_r:initrc_t
```

Persistence held across two reboots with the stick variant. A stick-free
variant, with a BusyBox binary copied to `apdat`, was later reboot-validated:
the FAT32 stick was removed before boot, `/media/` stayed empty, and
`/mtd_rwarea/apdat/root_proof.txt` was written by the boot script at about
12 s after kernel start. Root returned as
`uid=0(root) gid=0(root) context=system_u:system_r:initrc_t`, and both
listeners (`:2323`, `:9999`) and their ACCEPT rules were present. The retry
loops beat the netfilter start race again.

## Second sink (static, not fired)

RPC `setup.update.Usbsoftwarestart.ui` passes the JSON `filepath` unquoted into
`cp %s /swdl/autorun.upg`. One space and a comment character are enough to
append a command. This sink was found statically and was not used live.

## Telemetry leak

The `adId` value is sent to the advertising platform in the routine
`CMP token ... ifa=...` request before the shell runs. Injected payload text
can therefore appear in ad-platform logs. The reporter restored the original
UUID after testing. Treat any payload as disclosed to that request path.

## Corrections to earlier notes

| Earlier statement | Live finding |
| :--- | :--- |
| Doc 36: "browser/idtv code execution" is **INFERRED**; no live test has been run. | The `advertising.id.set` sink makes it concrete and live-verified. |
| Issue #3 follow-up 2: "This closes the 'Chromium CDP -> idtv code execution' candidate for the 2023 family." | Wrong as a family statement. CDP is absent from the default boot, but the USB flag enables it and the chain above is real. |
| Doc 36: `/dev/ntkmem` is not an arbitrary physical-memory window. | The static refutation stands; the live test did not challenge it. |

GNU `netcat -e` background loops zombie on this build: they accept and do not
exec. BusyBox `telnetd` from `apdat` is the stable root listener.

## Threat model

The entry class matches the published autoroot: one physical USB write that
places a flag-file name only, plus one warm reboot. Nothing on the stick is
executed and no cold boot is needed. Once the hook is written, later boots need
no stick. After entry, CDP, the RPC bridge, and the root listeners are
LAN-reachable through the ACCEPT rules that the persistence script installs;
the stock `iptables_conf.sh` does not open them.

Not claimed: entry without the flag file, remote exploitation, a Widevine or
secure-boot bypass, or survival when the flag is absent at browser start.

## Mitigations

1. Quote or remove the shell round-trip in `NUI_SETTING_SetIFAInfo`; the file
   can be written directly. Do the same for the `Usbsoftwarestart.ui`
   `filepath`.
2. Do not ship `--remote-debugging-port` in production images.
3. Replace existence-probe flags such as `nbrowser_log_to_file` with a signed
   token.
4. Do not source a file from a writable partition as root on every boot. The
   `customer_env.sh` hook is the persistence primitive behind this chain and
   the published autoroot.

## Limits

- The maintainer has not reproduced this unit or chain.
- The second sink is static only.
- One stick-free reboot was validated. Repeated stick-free boots and a recovery
  test are not claimed.
- The bridge binary attribution is inferred from `nvt.app.ini`.
- The sink is in the shared Titan OS RPC stack, so it plausibly applies to the
  55PUS8108/12 169.001 unit in
  [doc 41](41-tpn236e-55pus8108-2026-11-21.md). That requires one probe and is
  **OPEN**.

## Related

- [Doc 34](34-tpn236e-43pus7608-2026-11-14.md): the read-only field scan and
  the `:7788` default-boot result.
- [Doc 35](35-tpn236e-169001-static-2026-11-15.md): the verified 169.001
  artifact.
- [Doc 36](36-tpn236e-169001-corrections-2026-11-16.md): the `initrc_t`
  correction and the RW-hook inference this note completes.
- [Doc 13](13-webview-launcher-ipc.md): the webview and launcher IPC.
- [Doc 41](41-tpn236e-55pus8108-2026-11-21.md): the 55PUS8108/12 field report
  on the same firmware family.
- Issue #11: the live report and anchors.

Disclosure: the issue is public and every constituent except the execution step
is already in docs 34 and 36. This note keeps the execution primitive and the
anchors, and omits a ready-to-run payload. If the maintainer prefers private
disclosure for the injection sink, move this note to the private advisory and
leave only the entry-class summary here.
