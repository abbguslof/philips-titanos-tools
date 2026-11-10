/* uinput_key - inject one key via /dev/uinput (standard Linux uAPI).
 *
 * No vendor numbers. This is the lowest-risk Phase B target: it cannot touch
 * panel, power, or GPIO. Caveat from Phase A: /proc/bus/input/devices is empty
 * and /dev/input has no nodes, so the TV UI may not consume evdev at all.
 * Treat a no-op result as TESTED-NEGATIVE, not a failure of the harness.
 *
 * Usage: uinput_key [keycode_hex]   (default KEY_POWER = 0x74)
 */
#include "mini.h"

#define _IOC_NRBITS    8
#define _IOC_TYPEBITS  8
#define _IOC_SIZEBITS  14
#define _IOC_NRSHIFT   0
#define _IOC_TYPESHIFT (_IOC_NRSHIFT + _IOC_NRBITS)
#define _IOC_SIZESHIFT (_IOC_TYPESHIFT + _IOC_TYPEBITS)
#define _IOC_DIRSHIFT  (_IOC_SIZESHIFT + _IOC_SIZEBITS)
#define _IOC_NONE  0U
#define _IOC_WRITE 1U
#define _IOC(dir, type, nr, size) \
    (((dir) << _IOC_DIRSHIFT) | ((type) << _IOC_TYPESHIFT) | \
     ((nr) << _IOC_NRSHIFT) | ((size) << _IOC_SIZESHIFT))
#define _IO(t, nr)       _IOC(_IOC_NONE, t, nr, 0)
#define _IOW(t, nr, st)  _IOC(_IOC_WRITE, t, nr, sizeof(st))

struct input_id { u16 bustype, vendor, product, version; };
struct uinput_setup { struct input_id id; char name[80]; u32 ff_effects_max; };
struct input_event { long sec; long usec; u16 type; u16 code; int value; };
struct timespec { long sec; long nsec; };

#define UI_DEV_CREATE   _IO('U', 1)
#define UI_DEV_DESTROY  _IO('U', 2)
#define UI_DEV_SETUP    _IOW('U', 3, struct uinput_setup)
#define UI_SET_EVBIT    _IOW('U', 100, int)
#define UI_SET_KEYBIT   _IOW('U', 101, int)

#define EV_SYN 0
#define EV_KEY 1
#define SYN_REPORT 0
#define BUS_HOST 0x19

static void emit(int fd, u16 type, u16 code, int value) {
    struct input_event ev;
    memset(&ev, 0, sizeof(ev));
    ev.type = type;
    ev.code = code;
    ev.value = value;
    sc3(SYS_write, fd, (long)&ev, sizeof(ev));
}

int app_main(int argc, char **argv) {
    u16 key = 0x74; /* KEY_POWER */
    if (argc > 1) key = (u16)parsehex(argv[1]);

    int fd = (int)sc3(SYS_open, (long)"/dev/uinput", O_RDWR | O_NONBLOCK, 0);
    if (fd < 0) { out("open /dev/uinput errno "); outhex((ulong)(-fd)); ok(); }

    if (sc3(SYS_ioctl, fd, UI_SET_EVBIT, EV_KEY) < 0) { out("SET_EVBIT failed\n"); }
    if (sc3(SYS_ioctl, fd, UI_SET_KEYBIT, key) < 0) { out("SET_KEYBIT failed\n"); }

    struct uinput_setup us;
    memset(&us, 0, sizeof(us));
    us.id.bustype = BUS_HOST;
    us.name[0] = 'p'; us.name[1] = 'h'; us.name[2] = 'a'; us.name[3] = 's';
    us.name[4] = 'e'; us.name[5] = '-'; us.name[6] = 'b'; us.name[7] = 'p'; us.name[8] = '\0';
    if (sc3(SYS_ioctl, fd, UI_DEV_SETUP, (long)&us) < 0) { out("DEV_SETUP failed\n"); }
    if (sc3(SYS_ioctl, fd, UI_DEV_CREATE, 0) < 0) { out("DEV_CREATE failed\n"); sc1(SYS_close, fd); ok(); }

    out("uinput device created, key="); outhex(key);
    struct timespec ts;
    ts.sec = 0; ts.nsec = 300000000L;
    sc2(SYS_nanosleep, (long)&ts, 0);

    emit(fd, EV_KEY, key, 1);
    emit(fd, EV_SYN, SYN_REPORT, 0);
    ts.nsec = 120000000L;
    sc2(SYS_nanosleep, (long)&ts, 0);
    emit(fd, EV_KEY, key, 0);
    emit(fd, EV_SYN, SYN_REPORT, 0);

    ts.nsec = 300000000L;
    sc2(SYS_nanosleep, (long)&ts, 0);
    sc3(SYS_ioctl, fd, UI_DEV_DESTROY, 0);
    sc1(SYS_close, fd);
    out("done\n");
    ok();
    return 0;
}
