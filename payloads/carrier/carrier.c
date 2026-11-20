/* Reusable kernel carrier for the ndp_logo sysfs parameter.
 *
 * Built against the shipped ndp_logo.ko with build_carrier.py. The module
 * exposes /sys/module/ndp_logo/parameters/carrier. Every command is a single
 * text token written by root:
 *
 *   n                         set the result to the probe magic
 *   r <addr>                  read 64 bits (direct dereference)
 *   w <addr> <value>          write 64 bits (direct dereference)
 *   c <addr> <a0..a5>         call a kernel address with up to six arguments
 *   a                         set the result to the address of the scratch word
 *   m                         set the result to the scratch word
 *
 * <addr>, <value> and the call arguments are hexadecimal. Reading the
 * parameter returns the last result as 0x%016x. The kernel KCFI hash in front
 * of set/get is emitted by clang; build_carrier.py checks the hash algorithm
 * against the vendor module before packaging.
 *
 * The arbitrary-call helper is in carrier_raw.c and is compiled without KCFI
 * so the call itself is not type-checked. This is a lab primitive, not a
 * hardened interface.
 */
typedef unsigned long u64;

struct module;
struct kernel_param_ops;
struct kernel_param {
    const char *name;
    struct module *mod;
    const struct kernel_param_ops *ops;
    unsigned short perm;
    signed char level;
    unsigned char flags;
    void *arg;
};
struct kernel_param_ops {
    unsigned int flags;
    int (*set)(const char *val, const struct kernel_param *kp);
    int (*get)(char *buffer, const struct kernel_param *kp);
    void (*free)(void *arg);
};

extern struct module __this_module;
extern u64 carrier_raw_call(u64 fn, u64 a0, u64 a1, u64 a2,
                            u64 a3, u64 a4, u64 a5);

static volatile u64 g_addr;
static volatile u64 g_val;
static volatile u64 g_ret;
static volatile u64 g_args[6];
static volatile u64 g_buf[64];

static const char carrier_name[] = "carrier";

static int hexval(int c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static const char *skip_ws(const char *p)
{
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')
        p++;
    return p;
}

static u64 parse_hex(const char **pp)
{
    const char *p = skip_ws(*pp);
    u64 v = 0;
    int d;
    if (p[0] == '0' && (p[1] == 'x' || p[1] == 'X'))
        p += 2;
    while ((d = hexval((unsigned char)*p)) >= 0) {
        v = (v << 4) | (u64)d;
        p++;
    }
    *pp = p;
    return v;
}

__attribute__((noinline))
int carrier_set(const char *val, const struct kernel_param *kp)
{
    const char *p = skip_ws(val);
    char cmd = *p;
    int i;

    (void)kp;
    if (cmd == 'w') {
        p++;
        g_addr = parse_hex(&p);
        g_val = parse_hex(&p);
        *(volatile u64 *)(u64)g_addr = g_val;
        g_ret = 0;
        return 0;
    }
    if (cmd == 'r') {
        p++;
        g_addr = parse_hex(&p);
        g_ret = *(volatile u64 *)(u64)g_addr;
        return 0;
    }
    if (cmd == 'c') {
        p++;
        g_addr = parse_hex(&p);
        for (i = 0; i < 6; i++)
            g_args[i] = parse_hex(&p);
        g_ret = carrier_raw_call(g_addr, g_args[0], g_args[1], g_args[2],
                                 g_args[3], g_args[4], g_args[5]);
        return 0;
    }
    if (cmd == 'a') {
        g_ret = (u64)(unsigned long)&g_buf;
        return 0;
    }
    if (cmd == 'm') {
        g_ret = *(volatile u64 *)(u64)&g_buf;
        return 0;
    }
    if (cmd == 'n') {
        g_ret = 0x0d15ea5e0d15ea5eULL;
        return 0;
    }
    return -22;
}

static const char hexdig[] = "0123456789abcdef";

int carrier_get(char *buffer, const struct kernel_param *kp)
{
    u64 v = g_ret;
    int i;

    (void)kp;
    buffer[0] = '0';
    buffer[1] = 'x';
    for (i = 0; i < 16; i++)
        buffer[2 + i] = hexdig[(v >> (60 - 4 * i)) & 0xf];
    buffer[18] = '\n';
    return 19;
}

struct kernel_param_ops carrier_ops __attribute__((section(".data.carrier"), used)) = {
    0, carrier_set, carrier_get, 0
};

struct kernel_param __param_carrier __attribute__((section("__param"), used)) = {
    carrier_name, &__this_module, &carrier_ops, 0644, -1, 0, 0
};
