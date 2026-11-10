/* Freestanding ARM32 (EABI, armhf) runtime for Phase B probes.
 *
 * No libc and no sysroot. Everything is raw syscalls, so the binaries are
 * static and run on the TV's 32-bit unsigned userspace (ELF class 01, ARM).
 *
 * Build with tools/probe/build.sh.
 */
#ifndef MINI_H
#define MINI_H

typedef unsigned char  u8;
typedef unsigned short u16;
typedef unsigned int   u32;
typedef unsigned long  ulong;

#define SYS_exit   1
#define SYS_read   3
#define SYS_write  4
#define SYS_open   5
#define SYS_close  6
#define SYS_ioctl  54
#define SYS_nanosleep 162

#define O_RDONLY   0
#define O_WRONLY   1
#define O_RDWR     2
#define O_NONBLOCK 04000

static inline long sc1(long n, long a) {
    register long r7 __asm__("r7") = n;
    register long r0 __asm__("r0") = a;
    __asm__ volatile("svc 0" : "+r"(r0) : "r"(r7) : "memory", "r1", "r2", "r3");
    return r0;
}
static inline long sc2(long n, long a, long b) {
    register long r7 __asm__("r7") = n;
    register long r0 __asm__("r0") = a;
    register long r1 __asm__("r1") = b;
    __asm__ volatile("svc 0" : "+r"(r0) : "r"(r7), "r"(r1) : "memory", "r2", "r3");
    return r0;
}
static inline long sc3(long n, long a, long b, long c) {
    register long r7 __asm__("r7") = n;
    register long r0 __asm__("r0") = a;
    register long r1 __asm__("r1") = b;
    register long r2 __asm__("r2") = c;
    __asm__ volatile("svc 0" : "+r"(r0) : "r"(r7), "r"(r1), "r"(r2) : "memory", "r3");
    return r0;
}

/* The compiler may still emit calls to these even with -ffreestanding. */
__attribute__((unused)) static void *memcpy(void *d, const void *s, ulong n) {
    u8 *a = (u8 *)d; const u8 *b = (const u8 *)s;
    while (n--) *a++ = *b++;
    return d;
}
__attribute__((unused)) static void *memset(void *d, int c, ulong n) {
    u8 *a = (u8 *)d;
    while (n--) *a++ = (u8)c;
    return d;
}

static ulong slen(const char *s) { const char *p = s; while (*p) p++; return (ulong)(p - s); }
static void out(const char *s) { sc3(SYS_write, 1, (long)s, (long)slen(s)); }
static void outn(const char *s, ulong n) { sc3(SYS_write, 1, (long)s, (long)n); }

static char hexc(int d) { return (char)(d < 10 ? ('0' + d) : ('a' + d - 10)); }

/* Print "0x" + 8 hex digits + newline. */
static void outhex(ulong v) {
    char b[11];
    b[0] = '0'; b[1] = 'x';
    for (int i = 0; i < 8; i++) {
        int sh = (7 - i) * 4;
        b[2 + i] = hexc((int)((v >> sh) & 0xf));
    }
    b[10] = '\n';
    outn(b, 11);
}

/* Print a bounded, possibly unterminated name. */
static void outz(const char *s, ulong max) {
    ulong n = 0;
    while (n < max && s[n]) n++;
    if (n) outn(s, n);
}

static int streq(const char *a, const char *b) {
    while (*a && *b && *a == *b) { a++; b++; }
    return *a == *b;
}
static int hex1(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
static ulong parsehex(const char *s) {
    ulong v = 0;
    if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X')) s += 2;
    for (; *s; s++) { int d = hex1(*s); if (d < 0) break; v = (v << 4) | (ulong)d; }
    return v;
}

static void die(const char *m) { out(m); sc1(SYS_exit, 1); for (;;) {} }
static void ok(void) { sc1(SYS_exit, 0); for (;;) {} }

/* Entry point: recover argc/argv from the initial stack, then branch to C. */
extern int app_main(int argc, char **argv);
__attribute__((naked)) void _start(void) {
    __asm__ volatile(
        "ldr r0, [sp]\n"
        "add r1, sp, #4\n"
        "b app_main\n");
}

#endif
