#!/usr/bin/env python3
"""
Philips Titan OS Webview Debug & Kiosk Server

Runs a lightweight HTTP server on port 8080 serving a diagnostic console.
Captures User-Agent, HbbTV/OIPF global objects, screen metrics, and
Titan OS runtime APIs from the television's Vewd/Chromium browser engine.
"""

import http.server
import json
import os
import socketserver
import sys
import time

PORT = 8080
LOG_FILE = os.path.join(os.path.dirname(__file__), "webview_telemetry.json")
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".jointspace_credentials.json")

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Philips Titan OS Debug Kiosk</title>
    <style>
        body {
            background-color: #0d1117;
            color: #58a6ff;
            font-family: monospace, sans-serif;
            padding: 30px;
            font-size: 20px;
        }
        h1 { color: #2ea043; font-size: 34px; margin-bottom: 10px; }
        .box {
            background: #161b22;
            border: 2px solid #30363d;
            border-radius: 8px;
            padding: 16px;
            margin-top: 15px;
            word-wrap: break-word;
        }
        .highlight { color: #f0883e; }
        .status { color: #7ee787; font-weight: bold; }
        .explanation { color: #8b949e; font-size: 16px; margin-top: 6px; }
        pre { margin: 0; white-space: pre-wrap; font-size: 18px; }
    </style>
</head>
<body>
    <h1>🎯 TITAN OS LOCAL DEBUG KIOSK</h1>
    <div class="status">✓ Connected to Workstation (192.0.2.44:8080)</div>
    
    <div class="box">
        <strong>Browser User-Agent & Environment:</strong><br>
        <span id="ua" class="highlight">Detecting...</span>
    </div>

    <div class="box">
        <strong>Display & Viewport Metrics:</strong><br>
        <span id="metrics" class="highlight">Measuring...</span>
    </div>

    <div class="box">
        <strong>Discovered TV JavaScript & Plugin APIs:</strong><br>
        <span id="apis" class="highlight">Scanning window globals...</span>
        <pre id="oipfDetails" class="highlight" style="margin-top: 8px;"></pre>
    </div>

    <div class="box">
        <strong>Local Filesystem Probe (`file:///`):</strong><br>
        <div class="explanation">
            ℹ️ <em>Browser Same-Origin Policy (SOP): Remote HTTP web origins (e.g. <code>http://192.0.2.44:8080</code>) are blocked by Chromium sandbox security from reading local <code>file:///</code> paths. Direct file reading requires local <code>file:///</code> origin (e.g. running from USB).</em>
        </div>
        <pre id="files" class="highlight" style="margin-top: 8px;">Probing local files...</pre>
    </div>

    <div class="box">
        <strong>Localhost Loopback Services (`127.0.0.1`):</strong><br>
        <div class="explanation">
            ℹ️ <em>Reconnaissance Note: An immediate rejection (&lt;150ms) proves that loopback traffic is <strong>unfiltered</strong> by the Linux firewall (unlike external LAN traffic which is dropped/filtered).</em>
        </div>
        <pre id="loopback" class="highlight" style="margin-top: 8px;">Probing local services...</pre>
    </div>

    <div class="box">
        <strong>JointSpace Loopback API Probes (`http://127.0.0.1:1925`):</strong><br>
        <div class="explanation">
            ℹ️ <em>Testing direct unauthenticated localhost access to system & developer endpoints from inside the TV's browser sandbox.</em>
        </div>
        <pre id="jsLoopback" class="highlight" style="margin-top: 8px;">Testing JointSpace loopback routes...</pre>
    </div>

    <!-- OIPF / CE-HTML Embedded Plugin Objects -->
    <object id="oipfAppMan" type="application/oipfApplicationManager" style="position:absolute; width:0; height:0;"></object>
    <object id="oipfConfig" type="application/oipfConfiguration" style="position:absolute; width:0; height:0;"></object>
    <object id="oipfDownload" type="application/oipfDownloadManager" style="position:absolute; width:0; height:0;"></object>

    <script>
        var info = {
            origin: window.location.origin || window.location.protocol + '//' + window.location.host,
            protocol: window.location.protocol,
            userAgent: navigator.userAgent,
            screenWidth: window.screen.width,
            screenHeight: window.screen.height,
            innerWidth: window.innerWidth,
            innerHeight: window.innerHeight,
            devicePixelRatio: window.devicePixelRatio || 1,
            discoveredGlobals: [],
            oipfObjects: {},
            fileAccess: {},
            loopbackPorts: {},
            jointspaceLoopback: {}
        };

        document.getElementById('ua').innerText = info.userAgent;
        document.getElementById('metrics').innerText = 
            info.screenWidth + "x" + info.screenHeight + " (viewport: " + info.innerWidth + "x" + info.innerHeight + ", ratio: " + info.devicePixelRatio + ")";

        // 1. Probe candidate TV and vendor window globals
        var candidateGlobals = [
            'HbbTV', 'oipf', 'oipfObjectFactory', 'philips', 'titan',
            'vewd', 'Opera', 'opera', 'chrome', 'tpa', 'tpv', 'android', 'cef',
            'whale', 'whaletv', 'smarttv', 'nettv'
        ];

        for (var i = 0; i < candidateGlobals.length; i++) {
            var g = candidateGlobals[i];
            if (typeof window[g] !== 'undefined') {
                info.discoveredGlobals.push(g);
            }
        }

        // 2. Interrogate OIPF / CE-HTML plugins
        try {
            var appMan = document.getElementById('oipfAppMan');
            if (appMan) {
                var appKeys = [];
                for (var ak in appMan) { appKeys.push(ak); }
                info.oipfObjects['ApplicationManager'] = 'Active (properties: ' + (appKeys.join(', ') || 'native host object') + ')';
                
                if (typeof appMan.getOwnerApplication === 'function') {
                    try {
                        var owner = appMan.getOwnerApplication(window.document);
                        info.oipfObjects['OwnerApplication'] = owner ? 'Found' : 'Null';
                    } catch (oe) {
                        info.oipfObjects['OwnerApplication_err'] = oe.toString();
                    }
                }
            }
            var config = document.getElementById('oipfConfig');
            if (config) {
                var cfgKeys = [];
                for (var ck in config) { cfgKeys.push(ck); }
                info.oipfObjects['Configuration'] = 'Active (properties: ' + (cfgKeys.join(', ') || 'native host object') + ')';
                if (config.localSystem) {
                    var lsProps = {};
                    for (var lk in config.localSystem) { lsProps[lk] = String(config.localSystem[lk]); }
                    info.oipfObjects['localSystem'] = lsProps;
                }
            }
        } catch (e) {
            info.oipfObjects['error'] = e.toString();
        }

        document.getElementById('apis').innerText = 
            info.discoveredGlobals.length > 0 ? info.discoveredGlobals.join(', ') : "Standard web window (no exposed vendor globals on window)";
        document.getElementById('oipfDetails').innerText = JSON.stringify(info.oipfObjects, null, 2);

        // 3. Probe local file access with informative diagnostics
        var targetFiles = [
            'file:///proc/version',
            'file:///proc/cmdline',
            'file:///proc/mounts',
            'file:///etc/passwd'
        ];

        function probeFile(url) {
            if (window.location.protocol === 'http:' || window.location.protocol === 'https:') {
                info.fileAccess[url] = 'Blocked by SOP Sandbox (Remote HTTP origin cannot load local file:///)';
                updateFileUI();
                return;
            }
            try {
                var xhr = new XMLHttpRequest();
                xhr.open('GET', url, true);
                xhr.timeout = 1000;
                xhr.onreadystatechange = function() {
                    if (xhr.readyState === 4) {
                        info.fileAccess[url] = (xhr.status === 200 || xhr.responseText) ? xhr.responseText.substring(0, 300) : ('status:' + xhr.status);
                        updateFileUI();
                    }
                };
                xhr.onerror = function() { info.fileAccess[url] = 'Blocked / Error'; updateFileUI(); };
                xhr.send();
            } catch (err) {
                info.fileAccess[url] = 'Exception: ' + err.message;
                updateFileUI();
            }
        }

        function updateFileUI() {
            document.getElementById('files').innerText = JSON.stringify(info.fileAccess, null, 2);
        }

        for (var j = 0; j < targetFiles.length; j++) {
            probeFile(targetFiles[j]);
        }

        // 4. Probe localhost (127.0.0.1) internal daemons
        // Check JointSpace 1925 via actual HTTP fetch & authenticated routes
        var JS_USER = "__JS_USER__";
        var JS_PASS = "__JS_PASS__";

        if (window.fetch) {
            fetch('http://127.0.0.1:1925/1/system', { mode: 'no-cors' })
                .then(function() {
                    info.loopbackPorts[1925] = 'OPEN & ACTIVE (JointSpace HTTP API responding on 127.0.0.1:1925)';
                    updateLoopbackUI();
                })
                .catch(function(e) {
                    info.loopbackPorts[1925] = 'CLOSED / REJECTED (' + e.message + ')';
                    updateLoopbackUI();
                });

            var jsRoutes = [
                { path: '/1/system', method: 'GET', auth: false, desc: 'v1 system' },
                { path: '/6/system', method: 'GET', auth: false, desc: 'v6 system' },
                { path: '/6/debug', method: 'GET', auth: false, desc: 'debug unauth' },
                { path: '/6/debug', method: 'GET', auth: true, desc: 'debug auth' },
                { path: '/6/devtools', method: 'GET', auth: false, desc: 'devtools unauth' },
                { path: '/6/devtools', method: 'GET', auth: true, desc: 'devtools auth' },
                { path: '/6/devtools', method: 'POST', body: '{"enabled":true}', auth: true, desc: 'devtools enable' },
                { path: '/6/diagnostics', method: 'GET', auth: true, desc: 'diagnostics' },
                { path: '/6/applications', method: 'GET', auth: true, desc: 'applications list' },
                { path: '/6/activities/browser', method: 'GET', auth: false, desc: 'browser activity' }
            ];

            function probeJSRoute(route) {
                var label = (route.auth ? '🔒 [AUTH] ' : '🔓 [UNAUTH] ') + route.method + ' ' + route.path;
                var url = 'http://127.0.0.1:1925' + route.path;

                try {
                    var xhr = new XMLHttpRequest();
                    if (route.auth && JS_USER && JS_PASS) {
                        xhr.open(route.method, url, true, JS_USER, JS_PASS);
                    } else {
                        xhr.open(route.method, url, true);
                    }
                    xhr.timeout = 3000;
                    xhr.onreadystatechange = function() {
                        if (xhr.readyState === 4) {
                            var snippet = xhr.responseText ? (' - ' + xhr.responseText.substring(0, 100)) : '';
                            info.jointspaceLoopback[label] = 'HTTP ' + xhr.status + ' (' + xhr.statusText + ')' + snippet;
                            updateJSLoopbackUI();
                        }
                    };
                    xhr.onerror = function() {
                        info.jointspaceLoopback[label] = 'Network Error / Blocked';
                        updateJSLoopbackUI();
                    };
                    xhr.ontimeout = function() {
                        info.jointspaceLoopback[label] = 'Timeout (3s)';
                        updateJSLoopbackUI();
                    };
                    if (route.body) {
                        xhr.setRequestHeader('Content-Type', 'application/json');
                        xhr.send(route.body);
                    } else {
                        xhr.send();
                    }
                } catch (err) {
                    info.jointspaceLoopback[label] = 'Exception: ' + err.message;
                    updateJSLoopbackUI();
                }
            }

            for (var m = 0; m < jsRoutes.length; m++) {
                probeJSRoute(jsRoutes[m]);
            }
        }

        function updateJSLoopbackUI() {
            var el = document.getElementById('jsLoopback');
            if (el) el.innerText = JSON.stringify(info.jointspaceLoopback, null, 2);
        }

        var otherPorts = [2323, 4725, 8080, 9222];
        function probeOtherPort(p) {
            var img = new Image();
            var start = Date.now();
            img.onload = function() { 
                info.loopbackPorts[p] = 'OPEN (HTTP service detected)'; 
                updateLoopbackUI(); 
            };
            img.onerror = function() {
                var diff = Date.now() - start;
                if (diff < 150) {
                    info.loopbackPorts[p] = 'UNFILTERED (TCP RST in ' + diff + 'ms: port closed/no HTTP, but traffic is not dropped by firewall)';
                } else {
                    info.loopbackPorts[p] = 'FILTERED/TIMEOUT (> ' + diff + 'ms: dropped by firewall)';
                }
                updateLoopbackUI();
            };
            img.src = 'http://127.0.0.1:' + p + '/favicon.ico?' + Date.now();
        }

        function updateLoopbackUI() {
            document.getElementById('loopback').innerText = JSON.stringify(info.loopbackPorts, null, 2);
        }

        for (var k = 0; k < otherPorts.length; k++) {
            probeOtherPort(otherPorts[k]);
        }

        // Transmit updated telemetry report after probing completes
        setTimeout(function() {
            try {
                var tx = new XMLHttpRequest();
                tx.open("POST", "/api/telemetry", true);
                tx.setRequestHeader("Content-Type", "application/json");
                tx.send(JSON.stringify(info));
            } catch (e) {}
        }, 3000);
    </script>
</body>
</html>
"""


IPC_LOG_FILE = os.path.join(os.path.dirname(__file__), "ipc_telemetry.json")


def get_html_page() -> str:
    creds = {"user": "", "pass": ""}
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, "r") as f:
                creds = json.load(f)
        except Exception:
            pass
    return HTML_PAGE.replace("__JS_USER__", creds.get("user", "")).replace("__JS_PASS__", creds.get("pass", ""))


class DebugHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        print(f"\n[HTTP GET] Client: {self.client_address[0]} -> {self.path}")
        print(f"  User-Agent: {self.headers.get('User-Agent', 'Unknown')}")

        if self.path == "/ipc" or self.path == "/ipc/":
            # Serve the IPC Reflection Harness
            harness_path = os.path.join(os.path.dirname(__file__), "ipc_harness.html")
            try:
                with open(harness_path, "r") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
                print(f"  Served IPC Harness from {harness_path}")
            except FileNotFoundError:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"IPC harness file not found. Create tools/ipc_harness.html first.")
                print(f"  ERROR: {harness_path} not found!")
        else:
            # Default: serve the main diagnostic page with injected JointSpace credentials
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(get_html_page().encode("utf-8"))

    def do_OPTIONS(self):
        """Handle CORS preflight requests for cross-origin telemetry POSTs."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/telemetry":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            print(f"\n🎉 [TELEMETRY RECEIVED FROM TV: {self.client_address[0]}]")
            try:
                data = json.loads(body)
                print(json.dumps(data, indent=2))
                with open(LOG_FILE, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"  Saved to: {LOG_FILE}")
            except Exception as e:
                print(f"  Raw payload: {body}")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        elif self.path == "/api/ipc-telemetry":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            print(f"\n🔌 [IPC REFLECTION TELEMETRY FROM: {self.client_address[0]}]")
            print("=" * 60)
            try:
                data = json.loads(body)
                print(json.dumps(data, indent=2))
                with open(IPC_LOG_FILE, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"  Saved to: {IPC_LOG_FILE}")

                # Highlight interesting findings in terminal
                methods = {}
                if "phase2_enumeration" in data:
                    methods = data["phase2_enumeration"].get("methods", {})
                if "phase4_signatures" in data:
                    sigs = data["phase4_signatures"]
                    interesting = [k for k, v in sigs.items() if v.get("interesting")]
                    if interesting:
                        print(f"\n  ⚡ HIGH-INTEREST METHODS FOUND: {', '.join(interesting)}")
                if methods:
                    print(f"\n  📋 Total methods enumerated: {len(methods)}")
                    for mk, mv in methods.items():
                        print(f"    → {mk}(arity={mv.get('arity', '?')})")
            except Exception as e:
                print(f"  Parse error: {e}")
                print(f"  Raw payload: {body[:2000]}")
            print("=" * 60)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress noisy standard request log to keep terminal clean
        pass


def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), DebugHandler) as httpd:
        print("=" * 60)
        print(f"🚀 Titan OS Local Debug Server active on port {PORT}")
        print(f"=" * 60)
        print(f"  Main Diagnostic:    http://192.0.2.44:{PORT}/")
        print(f"  IPC Harness:        http://192.0.2.44:{PORT}/ipc")
        print(f"  Telemetry API:      POST /api/telemetry")
        print(f"  IPC Telemetry API:  POST /api/ipc-telemetry")
        print(f"=" * 60)
        print(f"  Telemetry log:  {LOG_FILE}")
        print(f"  IPC log:        {IPC_LOG_FILE}")
        print("=" * 60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")


if __name__ == "__main__":
    main()
