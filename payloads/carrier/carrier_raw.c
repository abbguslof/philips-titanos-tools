/* Unchecked arbitrary-call helper for the kernel carrier.
 *
 * Compiled without -fsanitize=kcfi on purpose: the kernel call site is a
 * controlled lab primitive and the target prototypes are not known ahead of
 * time. Keep this function in its own translation unit so the rest of the
 * carrier keeps its KCFI type hashes.
 */
typedef unsigned long u64;

u64 carrier_raw_call(u64 fn, u64 a0, u64 a1, u64 a2, u64 a3, u64 a4, u64 a5)
{
    return ((u64 (*)(u64, u64, u64, u64, u64, u64))fn)(a0, a1, a2, a3, a4, a5);
}
