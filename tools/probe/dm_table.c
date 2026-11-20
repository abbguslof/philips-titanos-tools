/* dm_table: read-only device-mapper table and device list probe.
 *
 * Static armhf, no libc. It uses DM_LIST_DEVICES and DM_TABLE_STATUS only.
 * It never creates, loads, suspends, or removes a mapping.
 *
 * Build: see tools/install/README.md.
 * Run:   dm_table                 (list devices)
 *        dm_table nfsb-2 nfsb-3  (table status by dm name)
 */
#include "mini.h"

typedef unsigned long long u64;

struct dm_ioctl {
    u32 version[3];
    u32 data_size;
    u32 data_start;
    u32 target_count;
    int open_count;
    u32 flags;
    u32 event_nr;
    u32 padding;
    u64 dev;
    char name[128];
    char uuid[129];
    char data[7];
};

struct dm_target_spec {
    u64 sector_start;
    u64 length;
    int status;
    u32 next;
    char target_type[16];
};

struct dm_name_list {
    u64 dev;
    u32 next;
    char name[];
};

_Static_assert(sizeof(struct dm_ioctl) == 312, "dm_ioctl layout");
_Static_assert(sizeof(struct dm_target_spec) == 40, "dm_target_spec layout");

#define DM_TABLE_STATUS 0xc138fd0cUL
#define DM_LIST_DEVICES 0xc138fd02UL
#define DM_IOCTL_BUF 8192

static unsigned long long buf[DM_IOCTL_BUF / 8];

static void outhex32(u32 v) {
    char b[8];
    for (int i = 0; i < 8; i++)
        b[i] = hexc((int)((v >> ((7 - i) * 4)) & 0xf));
    outn(b, 8);
}

static void outhex64(u64 v) {
    char b[16];
    for (int i = 0; i < 16; i++)
        b[i] = hexc((int)((v >> ((15 - i) * 4)) & 0xf));
    outn(b, 16);
}

static void copy_name(char *dst, const char *src, u32 max) {
    u32 i = 0;
    while (i + 1 < max && src[i]) {
        dst[i] = src[i];
        i++;
    }
    dst[i] = 0;
}

static int dm_open(void) {
    return (int)sc3(SYS_open, (long)"/dev/mapper/control", O_RDWR, 0);
}

static void list_devices(int fd) {
    struct dm_ioctl *io = (struct dm_ioctl *)buf;
    memset(io, 0, DM_IOCTL_BUF);
    io->version[0] = 4;
    io->data_size = DM_IOCTL_BUF;
    io->data_start = sizeof(struct dm_ioctl);
    long r = sc3(SYS_ioctl, fd, DM_LIST_DEVICES, (long)io);
    if (r < 0) {
        out("LIST_ERR ");
        outhex32((u32)-r);
        out("\n");
        return;
    }
    out("count ");
    outhex32(io->target_count);
    out(" data_start ");
    outhex32(io->data_start);
    out(" data_size ");
    outhex32(io->data_size);
    out("\n");
    char *e = (char *)io + io->data_start;
    for (u32 i = 0; i < 256; i++) {
        struct dm_name_list *nl = (struct dm_name_list *)e;
        out("dev 0x");
        outhex64(nl->dev);
        out(" name ");
        outz((char *)nl + 12, 128);
        out("\n");
        if (!nl->next) break;
        e += nl->next;
    }
}

static void table_status(int fd, const char *name) {
    struct dm_ioctl *io = (struct dm_ioctl *)buf;
    memset(io, 0, DM_IOCTL_BUF);
    io->version[0] = 4;
    io->data_size = DM_IOCTL_BUF;
    io->data_start = sizeof(struct dm_ioctl);
    copy_name(io->name, name, sizeof(io->name));
    long r = sc3(SYS_ioctl, fd, DM_TABLE_STATUS, (long)io);
    out(name);
    if (r < 0) {
        out(" err ");
        outhex32((u32)-r);
        out("\n");
        return;
    }
    out(" targets ");
    outhex32(io->target_count);
    out("\n");
    char *base = (char *)io + io->data_start;
    struct dm_target_spec *spec = (struct dm_target_spec *)base;
    for (u32 i = 0; i < io->target_count; i++) {
        out("  target ");
        outhex32(i);
        out(" type ");
        outz(spec->target_type, 16);
        out(" start 0x");
        outhex64(spec->sector_start);
        out(" len 0x");
        outhex64(spec->length);
        out(" status 0x");
        outhex32((u32)spec->status);
        out(" params ");
        outz((char *)(spec + 1), 256);
        out("\n");
        if (!spec->next) break;
        spec = (struct dm_target_spec *)(base + spec->next);
    }
}

int app_main(int argc, char **argv) {
    int fd = dm_open();
    if (fd < 0) die("open /dev/mapper/control failed\n");
    if (argc < 2) {
        list_devices(fd);
    } else {
        for (int i = 1; i < argc; i++)
            table_status(fd, argv[i]);
    }
    sc1(SYS_close, fd);
    ok();
    return 0;
}
