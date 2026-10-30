#!/usr/bin/env python3
"""
Philips JointSpace REST API Client & Discovery Tool

Communicates with the local Philips TV REST API (Port 1925 / 1926).
Provides network auto-discovery, PIN pairing (Digest Auth / HMAC-SHA1),
input source switching, remote key injection, and Ambilight control.

Supports dynamic IP configuration via:
  1. CLI argument: --host <IP>
  2. Environment variable: export PHILIPS_TV_IP=<IP>
  3. Automatic LAN discovery: ./tools/jointspace_client.py discover
"""

import argparse
import base64
import concurrent.futures
import hashlib
import hmac
import json
import os
import random
import socket
import ssl
import string
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.auth import HTTPDigestAuth

# Suppress insecure SSL warnings for local self-signed TV certificates
requests.packages.urllib3.disable_warnings()

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(REPO_ROOT, ".jointspace_credentials.json")

# The v6 pairing handshake needs the vendor application secret. It is not
# included in this repository. Supply the base64 secret from your own official
# client-app research in PHILIPS_APP_SECRET, or set PHILIPS_APP_SECRET_FILE to a
# file containing it. Pairing is optional; the root path does not use it.
def load_app_secret() -> bytes:
    secret_b64 = os.environ.get("PHILIPS_APP_SECRET", "").strip()
    secret_file = os.environ.get("PHILIPS_APP_SECRET_FILE", "").strip()
    if not secret_b64 and secret_file:
        try:
            with open(secret_file, "r", encoding="utf-8") as handle:
                secret_b64 = handle.read().strip()
        except OSError as exc:
            raise RuntimeError(f"cannot read PHILIPS_APP_SECRET_FILE: {exc}") from exc
    if not secret_b64:
        raise RuntimeError(
            "Pairing requires PHILIPS_APP_SECRET (base64) or PHILIPS_APP_SECRET_FILE. "
            "The vendor application secret is intentionally not shipped with this repo."
        )
    try:
        return base64.b64decode(secret_b64, validate=True)
    except Exception as exc:
        raise RuntimeError("PHILIPS_APP_SECRET is not valid base64") from exc


def load_credentials() -> Dict[str, Any]:
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_credentials(creds: Dict[str, Any]):
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(creds, f, indent=2)


def create_signature(secret_key: bytes, timestamp: Any, pin: str) -> str:
    """Computes base64-encoded raw HMAC-SHA1 digest over timestamp + pin."""
    h = hmac.new(secret_key, digestmod=hashlib.sha1)
    h.update(str(timestamp).encode("utf-8"))
    h.update(str(pin).encode("utf-8"))
    return base64.b64encode(h.digest()).decode("utf-8")


class JointSpaceClient:

    def __init__(
        self,
        host: str,
        port: int = 1925,
        protocol: str = "http",
        timeout: float = 5.0,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.timeout = timeout
        self.username = username
        self.password = password

        # Auto-load saved credentials if matching host
        if not self.username or not self.password:
            saved = load_credentials()
            if saved.get("host") == self.host:
                self.username = saved.get("user")
                self.password = saved.get("pass")
                if saved.get("port"):
                    self.port = saved.get("port")
                    self.protocol = "https"

        self.base_url = f"{self.protocol}://{self.host}:{self.port}"
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
        self._session: Optional[requests.Session] = None
        self._lock = threading.Lock()

    def _get_session(self) -> requests.Session:
        if self._session is None:
            s = requests.Session()
            if self.username and self.password:
                s.auth = HTTPDigestAuth(self.username, self.password)
            s.verify = False
            self._session = s
        return self._session

    def reset_session(self):
        """Resets the persistent session in case of socket drop or timeout."""
        with self._lock:
            if self._session is not None:
                try:
                    self._session.close()
                except Exception:
                    pass
                self._session = None

    def request(
        self, path: str, method: str = "GET", data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Sends an HTTP/HTTPS request, using persistent Digest Session if credentials exist."""
        url = f"{self.base_url}/{path.lstrip('/')}"

        # If credentials exist, use persistent requests.Session with Digest Auth over HTTPS
        if self.username and self.password:
            with self._lock:
                session = self._get_session()
                try:
                    r = session.request(
                        method=method,
                        url=url,
                        json=data,
                        timeout=self.timeout,
                    )
                except Exception:
                    # Invalidate session on error to avoid using poisoned socket
                    self.reset_session()
                    raise

                if not r.ok:
                    raise RuntimeError(f"HTTP {r.status_code}: {r.reason} - {r.text}")
                return r.json() if r.text.strip() else {}

        # Fallback to standard urllib for unauthenticated requests
        encoded_data = json.dumps(data).encode("utf-8") if data else None
        headers = {"Content-Type": "application/json"} if data else {}

        req = urllib.request.Request(
            url, data=encoded_data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(
                req, timeout=self.timeout, context=self._ctx
            ) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body.strip() else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {e.reason} - {err_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection failed to {url}: {e.reason}")

    def pair(
        self, pin: Optional[str] = None, scopes: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """Executes the JointSpace v6 pairing handshake on port 1926."""
        import secrets
        device_id = secrets.token_hex(16)
        device_spec = {
            "device_name": "TitanTools",
            "device_os": "Linux",
            "app_name": "TitanTools",
            "type": "native",
            "app_id": "app.titantools",
            "id": device_id,
        }

        # Step 1: Request pairing
        req_url = f"https://{self.host}:1926/6/pair/request"
        req_payload = {
            "scope": scopes or ["read", "write", "control", "debug"],
            "device": device_spec,
        }

        print(f"Connecting to {req_url}...")
        r = requests.post(req_url, json=req_payload, verify=False, timeout=self.timeout)
        if not r.ok:
            raise RuntimeError(f"Pairing request failed (HTTP {r.status_code}): {r.text}")

        res = r.json()
        auth_key = res.get("auth_key")
        timestamp = res.get("timestamp")

        if not auth_key or timestamp is None:
            raise RuntimeError(f"Unexpected pair response from TV: {res}")

        print("\n" + "=" * 50)
        print("📺 LOOK AT YOUR TELEVISION SCREEN!")
        print("A fresh 4-digit numeric PIN is now displayed.")
        print("=" * 50)

        if not pin:
            pin = input("\nEnter the 4-digit PIN from your TV screen: ").strip()

        # Step 2: Compute HMAC-SHA1 signature (raw binary digest, base64 encoded)
        signature = create_signature(
            load_app_secret(),
            timestamp,
            pin,
        )

        # Step 3: Grant pairing
        grant_url = f"https://{self.host}:1926/6/pair/grant"
        grant_payload = {
            "auth": {
                "auth_appId": "1",
                "auth_timestamp": timestamp,
                "auth_signature": signature,
                "pin": str(pin),
            },
            "device": device_spec,
        }

        r2 = requests.post(
            grant_url,
            json=grant_payload,
            verify=False,
            auth=HTTPDigestAuth(device_id, auth_key),
            timeout=self.timeout,
        )

        grant_res = r2.json() if r2.text.strip() else {}
        if grant_res.get("error_id") != "SUCCESS":
            raise RuntimeError(f"Pairing grant rejected by TV: {grant_res}")

        creds = {
            "host": self.host,
            "port": 1926,
            "user": device_id,
            "pass": auth_key,
        }
        save_credentials(creds)
        print("\n🎉 Pairing successful! Credentials saved to .jointspace_credentials.json")
        return creds

    def get_system_info(self) -> Dict[str, Any]:
        """Queries /1/system or /6/system."""
        for v in [1, 6]:
            try:
                return self.request(f"/{v}/system")
            except Exception:
                continue
        raise RuntimeError(f"Failed to query system endpoint on {self.host}")

    def get_power_state(self) -> Dict[str, Any]:
        """Queries powerstate."""
        for v in [6, 1]:
            try:
                return self.request(f"/{v}/powerstate")
            except Exception:
                continue
        raise RuntimeError(f"Failed to query powerstate on {self.host}")

    def set_power_state(self, state: str) -> Dict[str, Any]:
        """Sets powerstate ('On' or 'Standby')."""
        return self.request("/6/powerstate", method="POST", data={"powerstate": state})

    def get_sources(self) -> Dict[str, Any]:
        """Queries available video inputs."""
        for v in [1, 6]:
            try:
                return self.request(f"/{v}/sources")
            except Exception:
                continue
        raise RuntimeError(f"Failed to query sources on {self.host}")

    def set_source(self, source_id: str) -> Dict[str, Any]:
        """Switches active video source (e.g. HDMI1, HDMI2, HDMI3, HDMI4)."""
        return self.request("/6/sources/current", method="POST", data={"id": source_id})

    KEY_ALIASES = {
        "red": "RedColour",
        "redcolour": "RedColour",
        "blue": "BlueColour",
        "bluecolour": "BlueColour",
        "green": "GreenColour",
        "greencolour": "GreenColour",
        "yellow": "YellowColour",
        "yellowcolour": "YellowColour",
        "up": "CursorUp",
        "down": "CursorDown",
        "left": "CursorLeft",
        "right": "CursorRight",
        "ok": "Confirm",
    }

    def send_key(self, key_name: str) -> Dict[str, Any]:
        """Sends a remote control key event (e.g. Home, Standby, VolumeUp, RedColour, etc.)."""
        norm_key = self.KEY_ALIASES.get(key_name.lower(), key_name)
        for v in [6, 1]:
            try:
                return self.request(f"/{v}/input/key", method="POST", data={"key": norm_key})
            except Exception:
                continue
        raise RuntimeError(f"Failed to send key '{key_name}' on {self.host}")

    def send_sequence(self, keys: List[str], delay_sec: float = 0.35) -> List[Dict[str, Any]]:
        """Sends an ordered sequence of remote control keys with a timing delay between presses."""
        results = []
        for i, key in enumerate(keys):
            res = self.send_key(key)
            results.append(res)
            if i < len(keys) - 1 and delay_sec > 0:
                time.sleep(delay_sec)
        return results

    def get_ambilight_topology(self) -> Dict[str, Any]:
        """Queries Ambilight topology."""
        for v in [6, 1]:
            try:
                return self.request(f"/{v}/ambilight/topology")
            except Exception:
                continue
        raise RuntimeError(f"Failed to query Ambilight topology on {self.host}")

    def get_network_devices(self) -> List[Dict[str, Any]]:
        """Queries network interfaces and MAC addresses (/6/network/devices)."""
        return self.request("/6/network/devices")

    def get_storage_status(self) -> Dict[str, Any]:
        """Queries USB/external storage mount status (/6/system/storage)."""
        return self.request("/6/system/storage")

    def get_screen_state(self) -> Dict[str, Any]:
        """Queries active screen state (/6/screenstate)."""
        return self.request("/6/screenstate")

    def get_ambilight_colors(self) -> Dict[str, Any]:
        """Queries live processed RGB pixel values for all Ambilight LEDs (/6/ambilight/processed)."""
        return self.request("/6/ambilight/processed")

    def launch_browser(self, url: str) -> Dict[str, Any]:
        """Requests Vewd/Titan webview to open a target URL (/6/activities/browser)."""
        return self.request("/6/activities/browser", method="POST", data={"url": url})

    def get_debug_endpoints(self) -> Dict[str, Any]:
        """Probes developer/hidden routes: /6/debug, /6/devtools, /6/diagnostics, /6/applications, /6/directfb."""
        results = {}
        for route in ["/6/debug", "/6/devtools", "/6/diagnostics", "/6/applications", "/6/directfb"]:
            try:
                results[route] = self.request(route)
            except Exception as e:
                results[route] = str(e)
        return results


def discover_philips_tvs(timeout: float = 2.5) -> List[Tuple[str, str, str]]:
    """Scans the local subnet for responding JointSpace API instances."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "192.0.2.10"
    finally:
        s.close()

    subnet_prefix = local_ip.rsplit(".", 1)[0]
    print(f"Scanning local subnet {subnet_prefix}.0/24 on port 1925 (timeout: {timeout}s)...")

    found = []

    def probe_ip(ip: str):
        try:
            client = JointSpaceClient(ip, timeout=timeout)
            info = client.get_system_info()
            model = info.get("name") or info.get("model", "Philips TV")
            software = info.get("softwareversion_encrypted") or info.get("softwareversion", "Unknown")
            return (ip, model, software)
        except Exception:
            return None

    ips = [f"{subnet_prefix}.{i}" for i in range(1, 255)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=60) as executor:
        for res in executor.map(probe_ip, ips):
            if res:
                found.append(res)

    return found


def resolve_host(args) -> str:
    host = args.host or os.environ.get("PHILIPS_TV_IP")
    if not host:
        saved = load_credentials()
        host = saved.get("host")
    if not host:
        print("Error: No TV IP address specified.", file=sys.stderr)
        print("Provide IP via --host <IP> or export PHILIPS_TV_IP=<IP>", file=sys.stderr)
        sys.exit(1)
    return host


def cmd_discover(args):
    found = discover_philips_tvs(timeout=args.timeout)
    if not found:
        print("\nNo Philips TVs detected on the local subnet.")
    else:
        print(f"\nDiscovered {len(found)} Philips TV(s):")
        for ip, model, sw in found:
            print(f"  - {ip:15} | Model: {model} | Software: {sw}")


def cmd_pair(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, port=1926, protocol="https")
    client.pair(pin=args.pin, scopes=args.scopes)


def cmd_debug(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, port=1926, protocol="https")
    res = client.get_debug_endpoints()
    print(json.dumps(res, indent=2))


def cmd_status(args):
    host = resolve_host(args)
    client = JointSpaceClient(host)
    info = client.get_system_info()
    print(f"\n[OK] TV is online at {host}:")
    print(f"  Model:           {info.get('name') or info.get('model', 'N/A')}")
    print(f"  Operating System:{info.get('operatingSystem') or info.get('os_type', 'Linux')}")


def cmd_system(args):
    host = resolve_host(args)
    client = JointSpaceClient(host)
    info = client.get_system_info()
    print(json.dumps(info, indent=2))


def cmd_sources(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, port=1926, protocol="https")
    sources = client.get_sources()
    print(json.dumps(sources, indent=2))


def cmd_key(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, port=1926, protocol="https")
    res = client.send_key(args.key_name)
    print(f"Key '{args.key_name}' sent: {res}")


def cmd_source(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, port=1926, protocol="https")
    res = client.set_source(args.source_id)
    print(f"Switched source to '{args.source_id}': {res}")


def cmd_power(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, port=1926, protocol="https")
    if args.state:
        res = client.set_power_state(args.state)
        print(f"Power set to '{args.state}': {res}")
    else:
        state = client.get_power_state()
        print(json.dumps(state, indent=2))


def cmd_devices(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, port=1926, protocol="https")
    devices = client.get_network_devices()
    print(json.dumps(devices, indent=2))


def cmd_storage(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, port=1926, protocol="https")
    storage = client.get_storage_status()
    print(json.dumps(storage, indent=2))


def cmd_screenstate(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, port=1926, protocol="https")
    state = client.get_screen_state()
    print(json.dumps(state, indent=2))


def cmd_ambilight(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, port=1926, protocol="https")
    if args.stream:
        colors = client.get_ambilight_colors()
        print(json.dumps(colors, indent=2))
    else:
        topo = client.get_ambilight_topology()
        print(json.dumps(topo, indent=2))


PRESET_SEQUENCES = {
    "devmenu": ["RedColour", "CursorLeft", "CursorLeft", "CursorLeft", "CursorLeft", "BlueColour"],
    "launcher-info": ["RedColour", "CursorRight", "CursorRight", "CursorRight", "CursorRight", "BlueColour"],
    "logs": ["RedColour", "CursorUp", "CursorDown", "CursorUp", "CursorDown", "BlueColour"],
    "player-debug": ["RedColour", "CursorDown", "CursorUp", "CursorDown", "CursorUp", "BlueColour"],
    "reload": ["RedColour", "CursorUp", "CursorUp", "CursorUp", "CursorUp", "BlueColour"],
    "sw-modal": ["RedColour", "CursorDown", "CursorDown", "CursorDown", "CursorDown", "BlueColour"],
    "qa-suitest": ["RedColour", "CursorLeft", "CursorRight", "CursorLeft", "CursorRight", "BlueColour"],
    "qa-bundle": ["RedColour", "CursorRight", "CursorLeft", "CursorRight", "CursorLeft", "BlueColour"],
    "screensaver": ["RedColour", "CursorLeft", "CursorRight", "CursorRight", "CursorRight", "BlueColour"],
}


def cmd_sequence(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, port=1926, protocol="https")
    target = args.target.lower() if args.target else ""
    if target in PRESET_SEQUENCES:
        keys = PRESET_SEQUENCES[target]
        print(f"Executing preset sequence '{target}': {' -> '.join(keys)}")
    elif args.keys or args.target:
        keys = [args.target] + (args.keys or [])
        print(f"Executing custom key sequence: {' -> '.join(keys)}")
    else:
        print(f"Error: Unknown preset sequence '{args.target}'. Available presets:")
        for k, v in PRESET_SEQUENCES.items():
            print(f"  - {k:<15} ({' -> '.join(v)})")
        sys.exit(1)

    client.send_sequence(keys, delay_sec=args.delay)
    print(f"✓ Sequence complete ({len(keys)} keys sent).")


def cmd_browser(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, port=1926, protocol="https")
    res = client.launch_browser(args.url)
    print(f"Browser launch request sent for '{args.url}': {res}")
    print("\n" + "=" * 65)
    print("⚠️  TITAN OS / SAPHI ARCHITECTURAL LIMITATION:")
    print("=" * 65)
    print("On Philips Titan OS TVs (55PUS8000/12, tvtype: 'consumer'):")
    print("• POST /6/activities/browser is a stub endpoint: it returns HTTP 200 {}")
    print("  without launching an external browser or navigating to arbitrary URLs.")
    print("• The TV has NO standalone browser app. The entire TV UI is a single")
    print("  Chromium/Vewd webview shell loaded from https://eu.app.titanos.tv.")
    print("\nVERIFIED ALTERNATIVES TO DELIVER HARNESS / DEBUG CODE TO TV:")
    print("1. Pi-hole DNS Hijack + Intercept Server (Path C - Recommended):")
    print("   • Map 'eu.app.titanos.tv' -> 192.0.2.44 in Pi-hole.")
    print("   • Start: sudo ./tools/intercept_server.py --generate-cert")
    print("   • Reload TV webview: ./tools/jointspace_client.py sequence reload")
    print("   • The TV launcher immediately connects and runs ipc_harness.html!")
    print("2. USB Drive Webview Probe (Path B):")
    print("   • Copy tools/debug_usb.html to a FAT32 USB drive.")
    print("   • Insert into TV USB 1, open Sources -> USB -> debug_usb.html.")
    print("3. Developer Actions Menu:")
    print("   • Open menu: ./tools/jointspace_client.py sequence devmenu")
    print("   • Toggle logs: ./tools/jointspace_client.py sequence logs")
    print("=" * 65)


def cmd_raw(args):
    host = resolve_host(args)
    client = JointSpaceClient(host, args.port, "https" if args.secure else "http")
    resp = client.request(args.path, method=args.method)
    print(json.dumps(resp, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Philips JointSpace REST API Client & Discovery Tool (Port 1925/1926)"
    )
    parser.add_argument(
        "--host",
        "-H",
        help="TV IP address (defaults to $PHILIPS_TV_IP or saved credentials)",
    )
    parser.add_argument("-p", "--port", type=int, default=1925, help="Port (default: 1925)")
    parser.add_argument("-s", "--secure", action="store_true", help="Use HTTPS (Port 1926)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Discover
    p_disc = subparsers.add_parser("discover", help="Scan local network for Philips TVs")
    p_disc.add_argument("-t", "--timeout", type=float, default=2.5, help="Socket timeout (default: 2.5s)")
    p_disc.set_defaults(func=cmd_discover)

    # Pair
    p_pair = subparsers.add_parser("pair", help="Authenticate and pair with TV via 4-digit PIN")
    p_pair.add_argument("--pin", help="4-digit PIN displayed on TV screen (optional, prompts if omitted)")
    p_pair.add_argument("--scopes", nargs="+", default=["read", "write", "control", "debug"], help="Requested authorization scopes (default: read write control debug)")
    p_pair.set_defaults(func=cmd_pair)

    # Debug
    p_dbg = subparsers.add_parser("debug", help="Interrogate developer and hidden debug endpoints (/6/debug, /6/devtools, /6/diagnostics)")
    p_dbg.set_defaults(func=cmd_debug)

    # Status
    p_status = subparsers.add_parser("status", help="Quick connectivity and device status test")
    p_status.set_defaults(func=cmd_status)

    # System
    p_sys = subparsers.add_parser("system", help="Query /system endpoint")
    p_sys.set_defaults(func=cmd_system)

    # Sources
    p_src = subparsers.add_parser("sources", help="List video input sources")
    p_src.set_defaults(func=cmd_sources)

    # Key
    p_key = subparsers.add_parser("key", help="Send remote control key (Home, Standby, VolumeUp, etc.)")
    p_key.add_argument("key_name", help="Key name (e.g. Home, Standby, VolumeUp, VolumeDown, Mute)")
    p_key.set_defaults(func=cmd_key)

    # Source
    p_set_src = subparsers.add_parser("source", help="Switch active video input source")
    p_set_src.add_argument("source_id", help="Source ID (e.g. HDMI1, HDMI2, HDMI3, HDMI4)")
    p_set_src.set_defaults(func=cmd_source)

    # Power
    p_pow = subparsers.add_parser("power", help="Query or set power state")
    p_pow.add_argument("state", nargs="?", choices=["On", "Standby"], help="Target power state")
    p_pow.set_defaults(func=cmd_power)

    # Devices
    p_dev = subparsers.add_parser("devices", help="Query network devices and MAC addresses")
    p_dev.set_defaults(func=cmd_devices)

    # Storage
    p_stor = subparsers.add_parser("storage", help="Query USB storage status")
    p_stor.set_defaults(func=cmd_storage)

    # Screenstate
    p_scr = subparsers.add_parser("screenstate", help="Query screen display state (On/Off)")
    p_scr.set_defaults(func=cmd_screenstate)

    # Ambilight
    p_amb = subparsers.add_parser("ambilight", help="Query Ambilight topology or real-time LED RGB stream")
    p_amb.add_argument("--stream", "-s", action="store_true", help="Query live processed RGB pixel array")
    p_amb.set_defaults(func=cmd_ambilight)

    # Browser
    p_brw = subparsers.add_parser("browser", help="Request browser activity launch with URL (Note: stub on Titan OS)")
    p_brw.add_argument("url", help="URL to launch")
    p_brw.set_defaults(func=cmd_browser)

    # Sequence
    p_seq = subparsers.add_parser("sequence", help="Send multi-key D-pad sequence (e.g. devmenu, reload, logs)")
    p_seq.add_argument("target", help="Preset name (devmenu, reload, logs, player-debug, sw-modal, qa-bundle) or first key name")
    p_seq.add_argument("keys", nargs="*", help="Additional key names if sending custom sequence")
    p_seq.add_argument("--delay", type=float, default=0.35, help="Delay in seconds between key presses (default: 0.35s)")
    p_seq.set_defaults(func=cmd_sequence)

    # Query
    p_raw = subparsers.add_parser("query", help="Query arbitrary API path")
    p_raw.add_argument("path", help="Endpoint path (e.g. /1/ambilight/mode)")
    p_raw.add_argument("-m", "--method", default="GET", choices=["GET", "POST"])
    p_raw.set_defaults(func=cmd_raw)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

