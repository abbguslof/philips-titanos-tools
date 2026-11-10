#!/bin/sh
# Cross-build the Phase B probes as static 32-bit ARM (armhf) binaries.
#
# Target userspace is ELF class 01 / ARM EABI5 (verified Phase A). The kernel is
# aarch64, but userspace is armhf; these binaries are freestanding (no libc).
#
# Requirements (workstation): clang with the ARM target and lld.
# On this host lld lives in the mdx07 template toolchain; override with LLD=.

set -eu

CC=${CC:-clang}
LLD=${LLD:-ld.lld}   # set LLD=/path/to/ld.lld if lld is not on PATH

TARGET=arm-linux-gnueabihf
CFLAGS="--target=$TARGET -march=armv7-a -nostdlib -nostartfiles -fno-stack-protector -fno-builtin -ffreestanding -static -no-pie -O2 -Wall -Wextra -Wno-unused-function -Wno-unused-parameter"
LDFLAGS="-fuse-ld=lld --ld-path=$LLD -Wl,-e,_start"

mkdir -p dist/armhf
for p in ntkctl gpio_enum uinput_key; do
    # shellcheck disable=SC2086
    $CC $CFLAGS $LDFLAGS -o "dist/armhf/$p" "tools/probe/$p.c"
    echo "built dist/armhf/$p"
done

file dist/armhf/* 2>/dev/null || true
