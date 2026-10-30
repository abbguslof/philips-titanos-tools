# Run the persistent BusyBox from a separate tmpfs path

BusyBox resolves applets from `argv[0]`, so the binary must be named `busybox`. The USB payload uses `/tmp/busybox`. If the persistent hook also used that path, a USB stick left in the TV could overwrite the running binary. The persistent hook copies `apdat/busybox` to `/tmp/persist/busybox` instead.

**Status:** accepted

**Consequences:** The basename stays `busybox`, the two paths do not collide, and the USB autorun remains a safe recovery path even when persistence is installed.
