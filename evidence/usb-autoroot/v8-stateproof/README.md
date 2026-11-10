# v8 stateproof (Step 1)

Date: 2026-11-10
Target: `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`
Payload: `payloads/autoscript.stateproof.txt:1`
Stick contents at boot: `autoscript.stateproof.txt`, `busybox-armhf`, `proof.txt`

## Result

`proof.txt` has exactly one `=== boot ===` block (56 lines). Checks in
`run-meta.txt` show `grep -c` = 1 and uptime 126.31 s at 12:28:53, while the
eval ran at 12:27:23. No reboot after eval; `RESET(33)` did not recur on this
boot.

## Label

- Self-report per boot: VERIFIED (`proof.txt:1-56`).
- No reset on this boot: VERIFIED (`run-meta.txt:3-8`).
- Exact `RESET(33)` trigger: UNKNOWN (n=1 boot).

## Notes

- The stick had no `autoscript.txt`; the menu matched `autoscript*.txt`
  (`docs/research/05-usb-autorun-hook.md:23`), so the stateproof file ran.
- No redaction needed: the file contains no MAC, serial, SSID, or IP.
