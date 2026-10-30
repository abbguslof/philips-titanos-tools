# Remote sequences

All sequences are six keys: **RED**, four D-pad directions, **BLUE**. The
launcher bundle contains the handlers; only the Developer Actions menu was
verified on hardware in this research.

| Target | Sequence | Status |
| :--- | :--- | :--- |
| Developer Actions menu | RED, LEFT, LEFT, LEFT, LEFT, BLUE | **VERIFIED on hardware** |
| Launcher info HUD | RED, RIGHT, RIGHT, RIGHT, RIGHT, BLUE | INFERRED from bundle |
| Toggle on-screen logs | RED, UP, DOWN, UP, DOWN, BLUE | INFERRED |
| Toggle player debug | RED, DOWN, UP, DOWN, UP, BLUE | INFERRED |
| Reload launcher | RED, UP, UP, UP, UP, BLUE | INFERRED |
| Service worker modal | RED, DOWN, DOWN, DOWN, DOWN, BLUE | INFERRED |
| Toggle QA bundle | RED, RIGHT, LEFT, RIGHT, LEFT, BLUE | INFERRED |
| Toggle Suitest mode | RED, LEFT, RIGHT, LEFT, RIGHT, BLUE | INFERRED |
| Screen saver options | RED, LEFT, RIGHT, RIGHT, RIGHT, BLUE | INFERRED |
| Toggle accounts flag | RED, UP, RIGHT, DOWN, LEFT, BLUE | INFERRED |
| Toggle payment flag | RED, RIGHT, DOWN, LEFT, UP, BLUE | INFERRED |
| Toggle subscriptions | RED, DOWN, LEFT, UP, RIGHT, BLUE | INFERRED |

Inject keys over LAN after pairing:

```bash
./tools/jointspace_client.py --host <TV_IP> sequence devmenu
./tools/jointspace_client.py --host <TV_IP> key Red
./tools/jointspace_client.py --host <TV_IP> key Blue
```

On a remote without physical color keys, press `123` to show the on-screen
color keys, or inject `Red`/`Blue` over JointSpace.

The sequences are a launcher convenience, not a privilege boundary. The
Developer Actions menu does not unlock the JointSpace engineering routes; those
are blocked by `tvtype: consumer`.
