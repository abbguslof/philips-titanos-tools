#!/usr/bin/env python3
"""Minimal CDP client for the TV webview on :7788 (stdlib only).

Read-only by default at the call site: pass an expression.

  ./cdp.py http://192.0.2.10:7788 --list
  ./cdp.py http://192.0.2.10:7788 'document.title'
  ./cdp.py http://192.0.2.10:7788 'JSON.stringify([...document.querySelectorAll("*")].slice(0,20).map(e=>e.tagName))'

Notes:
  - The :7788 surface is a debug port, not a root path.
  - Runtime.evaluate runs in the page; do not paste untrusted expressions.
  - If the page is the launcher, expression results describe the DOM only.
"""
import base64
import json
import os
import socket
import struct
import sys
import urllib.request
from urllib.parse import urlparse


def http_targets(base: str):
    with urllib.request.urlopen(base.rstrip("/") + "/json", timeout=6) as r:
        return json.load(r)


def ws_connect(ws_url: str):
    u = urlparse(ws_url)
    host = u.hostname
    port = u.port or 80
    path = u.path + (("?" + u.query) if u.query else "")
    s = socket.create_connection((host, port), timeout=8)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    s.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += s.recv(4096)
    status = buf.split(b"\r\n", 1)[0]
    if b" 101 " not in status:
        raise SystemExit(f"ws handshake failed: {status!r}")
    return s


def send_text(s: socket.socket, obj) -> None:
    data = json.dumps(obj).encode()
    hdr = bytearray([0x81])
    n = len(data)
    if n < 126:
        hdr.append(0x80 | n)
    elif n < 65536:
        hdr.append(0x80 | 126)
        hdr += struct.pack(">H", n)
    else:
        hdr.append(0x80 | 127)
        hdr += struct.pack(">Q", n)
    mask = os.urandom(4)
    hdr += mask
    s.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def recv_text(s: socket.socket) -> str:
    def rd(n: int) -> bytes:
        b = b""
        while len(b) < n:
            c = s.recv(n - len(b))
            if not c:
                raise SystemExit("ws closed")
            b += c
        return b

    h = rd(2)
    ln = h[1] & 0x7F
    if ln == 126:
        ln = struct.unpack(">H", rd(2))[0]
    elif ln == 127:
        ln = struct.unpack(">Q", rd(8))[0]
    if h[1] & 0x80:
        rd(4)
    return rd(ln).decode("utf-8", "replace")


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://192.0.2.10:7788"
    targets = http_targets(base)

    if len(sys.argv) <= 2 or sys.argv[2] == "--list":
        for t in targets:
            print(t.get("id"), t.get("type"), t.get("title"), t.get("url"))
        return

    expr = sys.argv[2]
    page = next((t for t in targets if t.get("type") == "page"), targets[0])
    ws = ws_connect(page["webSocketDebuggerUrl"])
    send_text(ws, {
        "id": 1,
        "method": "Runtime.evaluate",
        "params": {"expression": expr, "returnByValue": True, "awaitPromise": True},
    })
    while True:
        msg = json.loads(recv_text(ws))
        if msg.get("id") == 1:
            print(json.dumps(msg, indent=2))
            break


if __name__ == "__main__":
    main()
