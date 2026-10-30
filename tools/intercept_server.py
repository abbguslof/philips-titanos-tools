#!/usr/bin/env python3
"""
Titan OS Transparent Caching Reverse Proxy & IPC Interception Server

Proxies eu.app.titanos.tv via CloudFront (65.9.46.117 / dv9982mgw1cws.cloudfront.net)
while injecting our native C++ BrowserIpcPluginClass reflection and enumeration harness.

Why Reverse Proxy Mode?
The Titan OS UI is a React 19 webview application that requires real assets
(/assets/main-DMLPMM5z.js, /lib/zeasn_sdk.js, /assets/useCustomKeyDown-DqSjW-ea.js).
If those assets are missing or return errors, the built-in criticalAssetMonitor
enters an infinite reload loop that starves the CPU and freezes the virtual keyboard.

By acting as a transparent caching reverse proxy:
1. All real assets are fetched from CloudFront and cached locally.
2. The UI, virtual keyboard, and remote control navigation work 100% normally.
3. Our diagnostic harness is injected into <head> under the authorized
   'https://eu.app.titanos.tv' origin, unlocking BrowserIpcPluginClass!
4. Native methods, loopback access, and system files are enumerated and logged.

Usage:
    sudo ./tools/intercept_server.py
"""

import argparse
import http.server
import json
import os
import socketserver
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Dict, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_DIR = os.path.join(SCRIPT_DIR, ".certs")
CERT_FILE = os.path.join(CERT_DIR, "titanos.crt")
KEY_FILE = os.path.join(CERT_DIR, "titanos.key")
INTERCEPT_LOG = os.path.join(SCRIPT_DIR, "intercept_telemetry.json")

UPSTREAM_HOST = "dv9982mgw1cws.cloudfront.net"
TARGET_HOST = "eu.app.titanos.tv"

HTTPS_PORT = 443
HTTP_PORT = 80

# In-memory asset cache: path -> (status_code, content_type, body_bytes)
ASSET_CACHE: Dict[str, Tuple[int, str, bytes]] = {}
UPSTREAM_SSL_CTX = ssl.create_default_context()


def generate_cert():
    """Generates self-signed TLS certificate for eu.app.titanos.tv."""
    os.makedirs(CERT_DIR, exist_ok=True)
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", KEY_FILE,
        "-out", CERT_FILE,
        "-days", "3650",
        "-nodes",
        "-subj", "/CN=eu.app.titanos.tv/O=TitanOS Research/C=GB",
        "-addext", "subjectAltName=DNS:eu.app.titanos.tv,DNS:app.titanos.tv,DNS:*.titanos.tv,IP:192.0.2.44"
    ]
    print("Generating self-signed certificate...")
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print("✓ Certificate generated successfully!")
    except subprocess.CalledProcessError as e:
        print(f"✗ Certificate generation failed: {e.stderr.decode()}")
        sys.exit(1)
    except FileNotFoundError:
        print("✗ openssl not found.")
        sys.exit(1)


# =============================================================================
# Injected JavaScript Probe Harness
# =============================================================================

INJECTED_PROBE_JS = """
// Titan OS Injected BrowserIpcPluginClass Reflection Harness
(function() {
    console.log('[TITAN_IPC] Injected probe harness initializing on origin:', window.location.origin);

    function runHarness() {
        var report = {
            ts: new Date().toISOString(),
            origin: window.location.origin,
            href: window.location.href,
            ua: navigator.userAgent,
            ipc_found: false,
            ipc_plugin: {},
            methods: {},
            properties: {},
            prototype_chain: [],
            loopback: {},
            active_plugins: {},
            errors: []
        };

        // 1. Locate BrowserIpcPluginClass
        var ipc = document.getElementById('BrowserIpcPluginClass');
        if (!ipc) {
            var objs = document.getElementsByTagName('object');
            for (var i = 0; i < objs.length; i++) {
                if (objs[i].type && objs[i].type.indexOf('browser-ipc') >= 0) {
                    ipc = objs[i];
                    break;
                }
            }
        }

        if (ipc) {
            report.ipc_found = true;
            report.ipc_plugin = {
                id: ipc.id,
                type: ipc.type,
                tagName: ipc.tagName,
                toString: String(ipc)
            };

            var std = {};
            var dummy = document.createElement('object');
            for (var sk in dummy) std[sk] = 1;

            var extraCount = 0;
            for (var k in ipc) {
                if (!std[k]) {
                    extraCount++;
                    try {
                        var val = ipc[k];
                        var t = typeof val;
                        if (t === 'function') {
                            report.methods[k] = {
                                arity: val.length,
                                str: val.toString().substring(0, 200)
                            };
                            // Safe probe for 0-argument getters
                            if (val.length === 0) {
                                try {
                                    var res = val.call(ipc);
                                    report.methods[k].result = String(res).substring(0, 300);
                                } catch(callErr) {
                                    report.methods[k].callError = callErr.message;
                                }
                            }
                        } else {
                            report.properties[k] = {
                                type: t,
                                value: String(val).substring(0, 300)
                            };
                        }
                    } catch(propErr) {
                        report.properties[k] = { error: propErr.message };
                    }
                }
            }
            report.ipc_plugin.extraKeysCount = extraCount;

            try {
                var proto = Object.getPrototypeOf(ipc);
                while (proto && proto !== Object.prototype) {
                    report.prototype_chain.push(proto.constructor ? proto.constructor.name : 'Unknown');
                    proto = Object.getPrototypeOf(proto);
                }
            } catch(protoErr) {
                report.errors.push('proto:' + protoErr.message);
            }
        }

        // 2. Loopback JointSpace queries
        var routes = ['/6/system', '/6/debug', '/6/devtools', '/6/activities/browser', '/6/system/storage'];
        var done = 0;
        for (var j = 0; j < routes.length; j++) {
            (function(path) {
                var xhr = new XMLHttpRequest();
                xhr.open('GET', 'http://127.0.0.1:1925' + path, true);
                xhr.timeout = 2500;
                xhr.onload = function() {
                    report.loopback[path] = { status: xhr.status, body: xhr.responseText.substring(0, 300) };
                    checkDone();
                };
                xhr.onerror = function() {
                    report.loopback[path] = { status: 'error' };
                    checkDone();
                };
                xhr.send();
            })(routes[j]);
        }

        function checkDone() {
            done++;
            if (done >= routes.length) {
                transmit();
            }
        }

        function transmit() {
            try {
                var tx = new XMLHttpRequest();
                tx.open('POST', '/api/ipc-telemetry', true);
                tx.setRequestHeader('Content-Type', 'application/json');
                tx.send(JSON.stringify(report, null, 2));
                console.log('[TITAN_IPC] Telemetry transmitted successfully!');
            } catch(txErr) {
                console.error('[TITAN_IPC] Transmit failed:', txErr);
            }
        }

        setTimeout(transmit, 4000);
    }

    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(runHarness, 1200);
    } else {
        window.addEventListener('load', function() {
            setTimeout(runHarness, 1200);
        });
    }
})();
"""


class TransparentProxyHandler(http.server.BaseHTTPRequestHandler):
    """Transparent caching reverse proxy for eu.app.titanos.tv with script injection."""

    def fetch_upstream(self, path: str) -> Tuple[int, str, bytes]:
        """Fetches resource from upstream CloudFront with uncompressed transfer."""
        if path in ASSET_CACHE:
            return ASSET_CACHE[path]

        url = f"https://{UPSTREAM_HOST}{path}"
        req = urllib.request.Request(
            url,
            headers={
                "Host": TARGET_HOST,
                "User-Agent": self.headers.get("User-Agent", "Mozilla/5.0 (TitanOS Proxy)"),
                "Accept-Encoding": "identity",  # Uncompressed for easy script injection
                "Accept": self.headers.get("Accept", "*/*"),
            }
        )

        try:
            with urllib.request.urlopen(req, context=UPSTREAM_SSL_CTX, timeout=10) as resp:
                status = resp.status
                ctype = resp.headers.get("Content-Type", "application/octet-stream")
                body = resp.read()
                # Cache static assets (JS, CSS, images, fonts)
                if any(ext in path for ext in [".js", ".css", ".png", ".svg", ".ico", ".woff", ".json"]):
                    ASSET_CACHE[path] = (status, ctype, body)
                return status, ctype, body
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type", "text/plain"), e.read()
        except Exception as e:
            err_msg = f"Upstream fetch failed: {e}".encode("utf-8")
            return 502, "text/plain", err_msg

    def do_GET(self):
        client_ip = self.client_address[0]
        path = self.path.split("?")[0]

        # 1. Serve our injected probe JavaScript
        if path == "/__titan_ipc_probe.js":
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(INJECTED_PROBE_JS.encode("utf-8"))
            print(f"  ⚡ Injected probe script delivered to {client_ip}")
            return

        # 2. Main HTML entry point: fetch upstream and inject probe
        if path in ["/", "/index.html"]:
            print(f"\n🎯 [LAUNCHER REQUEST] Client {client_ip} requested {self.path}")
            status, ctype, body = self.fetch_upstream("/")
            if status == 200:
                html = body.decode("utf-8", errors="replace")
                # Inject probe script into <head>
                inject_tag = '<script src="/__titan_ipc_probe.js"></script></head>'
                if "</head>" in html:
                    html = html.replace("</head>", inject_tag, 1)
                else:
                    html += '<script src="/__titan_ipc_probe.js"></script>'
                body = html.encode("utf-8")

            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(body)
            print(f"  ✓ Served real Titan OS HTML with injected probe harness!")
            return

        # 3. All other paths: fetch from upstream and proxy
        status, ctype, body = self.fetch_upstream(self.path)
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        # Handle telemetry submission
        if self.path in ["/api/ipc-telemetry", "/__titan_ipc_telemetry"]:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            print(f"\n" + "=" * 65)
            print(f"🎉 [INCOMING NATIVE IPC TELEMETRY] Client: {self.client_address[0]}")
            print("=" * 65)
            try:
                data = json.loads(body)
                print(json.dumps(data, indent=2))
                with open(INTERCEPT_LOG, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"\n  ✓ Successfully saved to: {INTERCEPT_LOG}")

                # Terminal highlights
                if data.get("ipc_found"):
                    print(f"\n  ⭐ BROWSER IPC PLUGIN INITIALIZED!")
                    print(f"     Extra Keys Found: {data.get('ipc_plugin', {}).get('extraKeysCount', 0)}")
                if data.get("methods"):
                    print(f"\n  ⚡ NATIVE C++ METHODS EXPOSED:")
                    for mname, minfo in data["methods"].items():
                        res_str = f" → {minfo['result'][:60]}" if "result" in minfo else ""
                        err_str = f" (err: {minfo['callError'][:60]})" if "callError" in minfo else ""
                        print(f"     • {mname}(arity={minfo.get('arity', '?')}){res_str}{err_str}")
                if data.get("loopback"):
                    print(f"\n  🔄 LOOPBACK ACCESS RESULTS:")
                    for lp, linfo in data["loopback"].items():
                        print(f"     • {lp:<25} → HTTP {linfo.get('status')}")
            except Exception as e:
                print(f"  Parse error: {e}\n  Raw body: {body[:1000]}")
            print("=" * 65)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        # Fallback for unknown POST
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress verbose asset logging, only show key requests
        pass


def run_single_server(port: int, use_ssl: bool = False) -> Optional[socketserver.TCPServer]:
    socketserver.TCPServer.allow_reuse_address = True
    try:
        httpd = socketserver.TCPServer(("0.0.0.0", port), TransparentProxyHandler)
    except PermissionError:
        print(f"✗ Permission denied binding to port {port}. Run with sudo!")
        return None

    if use_ssl:
        if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
            print("Certificate files not found. Auto-generating self-signed certificate...")
            generate_cert()
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(CERT_FILE, KEY_FILE)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

    return httpd


def run_proxy(http_port: int = 80, https_port: int = 443):
    """Starts dual-port transparent reverse proxy."""
    print("=" * 65)
    print("🎯 Titan OS Transparent Caching Reverse Proxy & IPC Interceptor")
    print("=" * 65)
    print(f"  Upstream:    https://{UPSTREAM_HOST} (Host: {TARGET_HOST})")
    print(f"  HTTPS (SSL): 0.0.0.0:{https_port} (for primary TV home launcher)")
    print(f"  HTTP (TCP):  0.0.0.0:{http_port}  (for TV browser / cert bypass)")
    print(f"  Target:      eu.app.titanos.tv → 192.0.2.44")
    print(f"  Log file:    {INTERCEPT_LOG}")
    print("=" * 65)

    http_server = run_single_server(http_port, use_ssl=False)
    https_server = run_single_server(https_port, use_ssl=True)

    if not http_server and not https_server:
        print("✗ Both servers failed to start. Exiting.")
        sys.exit(1)

    threads = []
    if http_server:
        t_http = threading.Thread(target=http_server.serve_forever, daemon=True)
        t_http.start()
        threads.append(t_http)
        print(f"  ✓ HTTP reverse proxy active on port {http_port}")

    if https_server:
        t_https = threading.Thread(target=https_server.serve_forever, daemon=True)
        t_https.start()
        threads.append(t_https)
        print(f"  ✓ HTTPS reverse proxy active on port {https_port}")

    print("\n  Ready! When the TV connects:")
    print("    1. All real assets (keyboard, styles, React bundles) will load cleanly.")
    print("    2. The injected probe will enumerate BrowserIpcPluginClass.")
    print("    3. Findings will be printed live in this terminal.")
    print("=" * 65)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down reverse proxy servers.")
        if http_server:
            http_server.shutdown()
        if https_server:
            https_server.shutdown()


def main():
    parser = argparse.ArgumentParser(
        description="Titan OS Transparent Caching Reverse Proxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--generate-cert", action="store_true",
        help="Regenerate self-signed TLS certificate"
    )
    parser.add_argument(
        "--http-only", action="store_true",
        help="Run only HTTP proxy on port 80"
    )
    parser.add_argument(
        "--https-only", action="store_true",
        help="Run only HTTPS proxy on port 443"
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help="Override the HTTP listening port"
    )

    args = parser.parse_args()

    if args.generate_cert:
        generate_cert()

    if args.http_only:
        port = args.port or HTTP_PORT
        s = run_single_server(port, use_ssl=False)
        if s:
            print(f"✓ HTTP proxy active on port {port}")
            try:
                s.serve_forever()
            except KeyboardInterrupt:
                pass
    elif args.https_only:
        port = args.port or HTTPS_PORT
        s = run_single_server(port, use_ssl=True)
        if s:
            print(f"✓ HTTPS proxy active on port {port}")
            try:
                s.serve_forever()
            except KeyboardInterrupt:
                pass
    else:
        run_proxy(http_port=args.port or HTTP_PORT, https_port=HTTPS_PORT)


if __name__ == "__main__":
    main()
