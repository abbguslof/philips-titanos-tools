/* lsblk-lite: static armhf block-device lister for the install proof.
 *
 * Reads /proc/partitions and prints NAME MAJ:MIN BLOCKS. No libc, no
 * division (so no __aeabi_uidiv), no dynamic loader. This is deliberately
 * small: it proves a binary can live on /mtd_rwarea/apdat and execute.
 *
 * Build: see tools/install/README.md
 */
#include "../probe/mini.h"

static int isdig(char c) { return c >= '0' && c <= '9'; }

static void putdec(u32 v) {
    char tmp[12];
    int i = 0;
    if (v == 0) { out("0"); return; }
    while (v) {
        u32 q = 0;
        while (v >= 10) { v -= 10; q++; }
        tmp[i++] = (char)('0' + (int)v);
        v = q;
    }
    while (i > 0) { i--; outn(&tmp[i], 1); }
}

static void pad(const char *s, ulong n, ulong w) {
    ulong l = 0;
    while (l < n && s[l]) l++;
    outn(s, l);
    for (ulong i = l; i < w; i++) out(" ");
}

int app_main(int argc, char **argv) {
    (void)argc; (void)argv;
    static char b[16384];

    int fd = (int)sc3(SYS_open, (long)"/proc/partitions", O_RDONLY, 0);
    if (fd < 0) { out("lsblk: cannot open /proc/partitions\n"); ok(); }
    long n = sc3(SYS_read, fd, (long)b, sizeof(b) - 1);
    sc1(SYS_close, fd);
    if (n <= 0) { out("lsblk: read failed\n"); ok(); }
    b[n] = 0;

    out("NAME             MAJ:MIN      BLOCKS\n");
    char *p = b;
    while (*p) {
        char *e = p;
        while (*e && *e != '\n') e++;
        char save = *e;
        *e = 0;

        char *q = p;
        while (*q == ' ') q++;
        if (isdig(*q)) {
            u32 maj = 0, min = 0, blk = 0;
            while (isdig(*q)) { maj = maj * 10 + (u32)(*q - '0'); q++; }
            while (*q == ' ') q++;
            while (isdig(*q)) { min = min * 10 + (u32)(*q - '0'); q++; }
            while (*q == ' ') q++;
            while (isdig(*q)) { blk = blk * 10 + (u32)(*q - '0'); q++; }
            while (*q == ' ') q++;
            char *name = q;
            while (*q && *q != ' ') q++;
            pad(name, (ulong)(q - name), 16);
            out(" ");
            putdec(maj); out(":"); putdec(min);
            out("  ");
            putdec(blk);
            out(" KB\n");
        }

        *e = save;
        if (!save) break;
        p = e + 1;
    }
    ok();
    return 0;
}
