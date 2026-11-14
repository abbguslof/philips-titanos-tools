/* ntkctl - vendor /dev/ntk* ioctl probe.
 *
 * It does NOT contain any vendor request numbers. You pass the command that
 * you measured from the vendor driver (see docs/research/19). Default is dry:
 * it opens and prints, but will not call ioctl unless you add --go.
 *
 * Usage:
 *   ntkctl <dev> [cmd_hex|none] [buflen_hex] [--rw] [--fill XX] [--data HEX] [--go]
 *
 * Safety:
 *   - opens O_RDONLY unless --rw
 *   - requires --go before any ioctl
 *   - buffer is zeroed, filled with --fill, or loaded with --data; capped at
 *     4096 bytes. --data must be exactly buflen*2 hex characters.
 *   - prints ret/errno and the post-call buffer
 *
 * This is a measurement tool. Do not run blind ioctl sweeps; the "cannot
 * hang" rule forbids them. Measure cmds from the .ko first.
 */
#include "mini.h"

static u8 buf[4096];

int app_main(int argc, char **argv) {
    if (argc < 2) die("usage: ntkctl <dev> [cmd_hex|none] [buflen_hex] [--rw] [--fill XX] [--data HEX] [--go]\n");

    const char *dev = argv[1];
    ulong cmd = 0;
    int have_cmd = 0, rw = 0, go = 0, fill = -1, npos = 0;
    ulong blen = 0x40;
    const char *pos[2] = {0, 0};
    const char *data = 0;

    for (int i = 2; i < argc; i++) {
        if (streq(argv[i], "--rw")) rw = 1;
        else if (streq(argv[i], "--go")) go = 1;
        else if (streq(argv[i], "--fill") && i + 1 < argc) fill = (int)parsehex(argv[++i]);
        else if (streq(argv[i], "--data") && i + 1 < argc) data = argv[++i];
        else if (npos < 2) pos[npos++] = argv[i];
    }
    if (npos >= 1 && !streq(pos[0], "none")) { cmd = parsehex(pos[0]); have_cmd = 1; }
    if (npos >= 2) blen = parsehex(pos[1]);
    if (blen > sizeof(buf)) die("buflen > 4096 refused\n");

    if (data) {
        ulong n = 0;
        while (data[n]) n++;
        if (n != blen * 2) die("--data hex length must be buflen*2\n");
        for (ulong i = 0; i < blen; i++) {
            char h[3] = { data[2 * i], data[2 * i + 1], 0 };
            buf[i] = (u8)parsehex(h);
        }
    } else if (fill >= 0) {
        memset(buf, fill, blen);
    } else {
        memset(buf, 0, blen);
    }

    int fd = (int)sc3(SYS_open, (long)dev, rw ? O_RDWR : O_RDONLY, 0);
    if (fd < 0) { out("open failed, errno "); outhex((ulong)(-fd)); ok(); }

    out("opened "); out(dev); out("\nfd="); outhex((ulong)fd);
    out("mode="); out(rw ? "O_RDWR\n" : "O_RDONLY\n");

    if (!have_cmd) { out("no cmd given: dry open only\n"); sc1(SYS_close, fd); ok(); }
    if (!go) {
        out("dry: would call ioctl cmd="); outhex(cmd);
        out("buf="); outhex(blen);
        out("re-run with --go to send it\n");
        sc1(SYS_close, fd);
        ok();
    }

    out("calling ioctl cmd="); outhex(cmd);
    long r = sc3(SYS_ioctl, fd, (long)cmd, (long)buf);
    if (r < 0) { out("ioctl ret = -errno "); outhex((ulong)(-r)); }
    else { out("ioctl ret = "); outhex((ulong)r); }

    out("buffer after call:\n");
    for (ulong i = 0; i < blen; i++) {
        if (i % 16 == 0) {
            if (i) out("\n");
            out("  "); outhex(i); out(" ");
        }
        char h[3];
        h[0] = hexc((int)(buf[i] >> 4));
        h[1] = hexc((int)(buf[i] & 0xf));
        h[2] = ' ';
        outn(h, 3);
    }
    out("\n");

    sc1(SYS_close, fd);
    ok();
    return 0;
}
