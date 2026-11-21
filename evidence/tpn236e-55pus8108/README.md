# 55PUS8108/12 browser and USB observations

External hardware observations on `TPN236E_V236.006.169.001`, 16–21 November
2026. Each row summarizes selected fields from the owner's recorded test.

| Test | Recorded result | Status |
| :--- | :--- | :--- |
| Browser player, first completed playback | H.264, 12 s, 1280 × 720, 360 frames, 0 dropped, no player error | REPORTED |
| Nuvio web player, first completed playback | Same clip, 360 frames, 0 dropped, no player error | REPORTED |
| USB insertion, then separate browser-restart check | 5 TCP timeouts on 7788 after insertion. At the restart check, 1926 accepted TCP while 7001, 7788 and 9222 timed out. | TESTED-NEGATIVE for browser debug in those checks |
| USB cold boot and browser reopening | 48 TCP timeouts on 7788 followed by one successful connection. Version metadata returned HTTP 200, Chrome/92.0.4515.159 and protocol 1.3. | REPORTED |
| USB removed, cold boot, browser reopened | 7001, 7788 and 9222 timed out. JointSpace returned HTTP 200 and API version 6.1.0. | TESTED-NEGATIVE for browser debug in this check |

Timeout describes the result at the observing client. The tests did not
distinguish filtering from an absent listener. The successful response
identified a browser service. The later boot observation below has a separate device record.

## Later hardware observations

| Date (UTC) | Observation | Scope |
| :--- | :--- | :--- |
| 19 Nov | An initial system query timed out. After three wake datagrams, JointSpace returned HTTP 200, matching model and firmware, API 6.1.0. | REPORTED network response. The screen state was unobserved. |
| 20 Nov | The device returned USB mount `/media/sdb1`. Two existence queries returned false for `/media/sda1` and its HAL log. In a separate run, all five expected diagnostic outputs returned read errors. | REPORTED mount snapshot. TESTED-NEGATIVE for readable output in that run. |
| 21 Nov | Two reads of the same post-boot result matched in SHA-256. The retained 957 bytes contain `Name: rcS`, `PPid: 1`, UID and GID tuples each `0 0 0 0`, and `system_u:system_r:initrc_t`. | REPORTED one privileged boot execution. The framework process was not sampled. |

No interactive session, second successful boot test or full recovery was
demonstrated. Only selected fields from the records are reproduced here.
