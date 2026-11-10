/* gpio_enum - read-only enumeration of /dev/gpiochip0 line names.
 *
 * Uses the standard Linux GPIO character-device uAPI (v2 line info). No
 * vendor request numbers, no line requests, no writes. This is the safe way
 * to discover standby/power/IR line names before touching ntgpio.
 *
 * Usage: gpio_enum [/dev/gpiochip0]
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
#define _IOC_READ  2U
#define _IOC(dir, type, nr, size) \
    (((dir) << _IOC_DIRSHIFT) | ((type) << _IOC_TYPESHIFT) | \
     ((nr) << _IOC_NRSHIFT) | ((size) << _IOC_SIZESHIFT))
#define _IOR(t, nr, st)  _IOC(_IOC_READ, t, nr, sizeof(st))
#define _IOWR(t, nr, st) _IOC(_IOC_READ | _IOC_WRITE, t, nr, sizeof(st))

struct gpiochip_info {
    char name[32];
    char label[32];
    u32 lines;
};

struct gpio_v2_line_attribute {
    u32 id;
    u32 padding;
    unsigned long long values;
};

struct gpio_v2_line_info {
    u32 offset;
    u32 flags;
    char name[32];
    char consumer[32];
    u32 num_attrs;
    u32 padding[4];
    struct gpio_v2_line_attribute attrs[10];
};

#define GPIO_GET_CHIPINFO_IOCTL        _IOR(0xB4, 0x01, struct gpiochip_info)
#define GPIO_V2_GET_LINEINFO_IOCTL     _IOWR(0xB4, 0x05, struct gpio_v2_line_info)

int app_main(int argc, char **argv) {
    const char *dev = (argc > 1) ? argv[1] : "/dev/gpiochip0";
    struct gpiochip_info ci;
    struct gpio_v2_line_info li;

    memset(&ci, 0, sizeof(ci));
    int fd = (int)sc3(SYS_open, (long)dev, O_RDONLY | O_NONBLOCK, 0);
    if (fd < 0) { out("open failed "); out(dev); out(" errno "); outhex((ulong)(-fd)); ok(); }

    long r = sc3(SYS_ioctl, fd, GPIO_GET_CHIPINFO_IOCTL, (long)&ci);
    if (r < 0) { out("chipinfo ioctl errno "); outhex((ulong)(-r)); sc1(SYS_close, fd); ok(); }

    out("chip name="); outz(ci.name, 32);
    out(" label="); outz(ci.label, 32);
    out(" lines="); outhex(ci.lines);

    for (u32 i = 0; i < ci.lines; i++) {
        memset(&li, 0, sizeof(li));
        li.offset = i;
        long q = sc3(SYS_ioctl, fd, GPIO_V2_GET_LINEINFO_IOCTL, (long)&li);
        if (q < 0) { out("  line "); outhex(i); out("  <errno "); outhex((ulong)(-q)); out(">\n"); continue; }
        out("  "); outhex(i); out(" flags="); outhex(li.flags);
        out(" name="); outz(li.name, 32);
        out(" consumer="); outz(li.consumer, 32);
        out("\n");
    }

    sc1(SYS_close, fd);
    ok();
    return 0;
}
