#!/usr/bin/env python3
"""
Philips Titan OS Ambilight Studio & TV Command Center
Unified Web Remote & LED Controller (JointSpace v6)

Features:
1. Real-Time Color Extraction & ANSI TrueColor Terminal Visualizer (/6/ambilight/processed)
2. Individual LED Pixel Control & Zone Canvas in Expert Mode (/6/ambilight/cached)
3. Advanced Multi-Select (Single click, Shift-Click range, Drag-to-paint, Zones, Invert, Clear)
4. Gradient & Mood Lighting Generators (Cyberpunk, Sunset, Nordic, HSV Rainbow, 6500K Cinema)
5. Live Brightness Slider & Auto-Apply Mode
6. Full TV Remote Control Deck (D-Pad, Volume Slider, Navigation, Standby)
7. Developer Sequence Macros (Developer Menu, Logs HUD, Player Debug, Launcher Reload)
8. Non-blocking Caching & Rate-Limiting to prevent TV HTTP daemon overloading
9. Embedded Web Command Center GUI on port 8088
"""

import argparse
import http.server
import json
import os
import socketserver
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tools.jointspace_client import JointSpaceClient, resolve_host, PRESET_SEQUENCES

WEB_PORT = 8088


def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    """Converts #RRGGBB or RRGGBB to (r, g, b) tuple."""
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join(c * 2 for c in hex_code)
    if len(hex_code) != 6:
        raise ValueError(f"Invalid hex color code: '{hex_code}' (expected 3 or 6 hex digits)")
    return int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Converts (r, g, b) to #RRGGBB."""
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def ansi_block(r: int, g: int, b: int, width: int = 4) -> str:
    """Returns an ANSI TrueColor background block."""
    return f"\033[48;2;{r};{g};{b}m{' ' * width}\033[0m"


class TelemetryCache:
    """Thread-safe cache with TTL to throttle TV polling and prevent daemon starvation."""

    def __init__(self, live_ttl: float = 1.0, status_ttl: float = 4.0):
        self.live_ttl = live_ttl
        self.status_ttl = status_ttl
        self.cached_live: Optional[Dict[str, Any]] = None
        self.last_live_fetch = 0.0
        self.cached_status: Optional[Dict[str, Any]] = None
        self.last_status_fetch = 0.0
        self.lock = threading.Lock()

    def get_live(self, client: JointSpaceClient) -> Dict[str, Any]:
        now = time.time()
        with self.lock:
            if self.cached_live is not None and (now - self.last_live_fetch) < self.live_ttl:
                return self.cached_live

        data = client.request("/6/ambilight/processed")
        with self.lock:
            self.cached_live = data
            self.last_live_fetch = time.time()
        return data

    def invalidate_live(self):
        with self.lock:
            self.last_live_fetch = 0.0

    def get_status(self, client: JointSpaceClient) -> Dict[str, Any]:
        now = time.time()
        with self.lock:
            if self.cached_status is not None and (now - self.last_status_fetch) < self.status_ttl:
                return self.cached_status

        status: Dict[str, Any] = {}
        try:
            status["screenstate"] = client.request("/6/screenstate")
        except Exception:
            status["screenstate"] = {"screenstate": "Unknown"}

        # In Philips JointSpace: screenstate 'Off' = Eco Screen-Off mode is OFF (Display panel is ON).
        raw_screen = status.get("screenstate", {}).get("screenstate", "Unknown")
        if raw_screen == "Off":
            status["display_power"] = "On"
            status["display_label"] = "Display: On"
        elif raw_screen == "On":
            status["display_power"] = "Eco-Off"
            status["display_label"] = "Display: Audio Only"
        else:
            status["display_power"] = "Active"
            status["display_label"] = "Display: Active"

        try:
            status["volume"] = client.request("/6/audio/volume")
        except Exception:
            status["volume"] = {"current": 0, "muted": False}

        try:
            status["ambilight_power"] = client.request("/6/ambilight/power")
        except Exception:
            status["ambilight_power"] = {"power": "Unknown"}

        with self.lock:
            self.cached_status = status
            self.last_status_fetch = time.time()
        return status

    def invalidate_status(self):
        with self.lock:
            self.last_status_fetch = 0.0


class AmbilightController:
    """Controls Philips TV Ambilight and Remote Functions via JointSpace v6."""

    def __init__(self, host: Optional[str] = None):
        self.host = host or "192.0.2.10"
        self.client = JointSpaceClient(self.host, port=1926, protocol="https")
        self.cache = TelemetryCache()
        self._is_expert = False

    def get_topology(self) -> Dict[str, Any]:
        return self.client.request("/6/ambilight/topology")

    def get_current_configuration(self) -> Dict[str, Any]:
        return self.client.request("/6/ambilight/currentconfiguration")

    def get_supported_styles(self) -> Dict[str, Any]:
        return self.client.request("/6/ambilight/supportedstyles")

    def get_mode(self) -> Dict[str, Any]:
        return self.client.request("/6/ambilight/mode")

    def get_power(self) -> Dict[str, Any]:
        return self.client.request("/6/ambilight/power")

    def set_power(self, power_state: str) -> Dict[str, Any]:
        """Toggles Ambilight power ('On' or 'Off')."""
        res = self.client.request("/6/ambilight/power", method="POST", data={"power": power_state})
        self.cache.invalidate_status()
        return res

    def get_live_colors(self) -> Dict[str, Any]:
        """Reads live processed RGB pixel values with daemon rate limiting."""
        return self.cache.get_live(self.client)

    def get_system_status(self) -> Dict[str, Any]:
        """Fetches unified status of screen, audio volume, and ambilight."""
        return self.cache.get_status(self.client)

    def set_expert_mode(self) -> Dict[str, Any]:
        """Activates 'expert' mode so manual pixel / cached frame injection persists."""
        if not self._is_expert:
            try:
                res = self.client.request("/6/ambilight/mode", method="POST", data={"current": "expert"})
                self._is_expert = True
                self.cache.invalidate_status()
                return res
            except Exception:
                pass
        return {}

    def set_color_all(self, r: int, g: int, b: int) -> Dict[str, Any]:
        """Sets all 16 physical Ambilight LEDs to a solid RGB color in expert mode."""
        self.set_expert_mode()
        payload = {
            "layer1": {
                "left": {str(i): {"r": r, "g": g, "b": b} for i in range(4)},
                "top": {str(i): {"r": r, "g": g, "b": b} for i in range(8)},
                "right": {str(i): {"r": r, "g": g, "b": b} for i in range(4)},
            }
        }
        res = self.client.request("/6/ambilight/cached", method="POST", data=payload)
        self.cache.invalidate_live()
        return res

    def set_led(self, side: str, index: int, r: int, g: int, b: int) -> Dict[str, Any]:
        """Sets an individual LED to a specific RGB value."""
        self.set_expert_mode()
        side_clean = side.lower()
        if side_clean not in ["left", "top", "right"]:
            raise ValueError(f"Invalid side '{side}'. Must be 'left', 'top', or 'right'.")

        payload = {
            "layer1": {
                side_clean: {
                    str(index): {"r": max(0, min(255, r)), "g": max(0, min(255, g)), "b": max(0, min(255, b))}
                }
            }
        }
        res = self.client.request("/6/ambilight/cached", method="POST", data=payload)
        self.cache.invalidate_live()
        return res

    def set_leds_batch(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Updates multiple LEDs in a single atomic payload.
        Each update item: {"side": "top"|"left"|"right", "index": int, "r": int, "g": int, "b": int}
        """
        self.set_expert_mode()
        layer: Dict[str, Dict[str, Dict[str, int]]] = {}
        for item in updates:
            side = item.get("side", "").lower()
            idx = str(item.get("index", 0))
            r = int(item.get("r", 0))
            g = int(item.get("g", 0))
            b = int(item.get("b", 0))
            if side in ["left", "top", "right"]:
                if side not in layer:
                    layer[side] = {}
                layer[side][idx] = {
                    "r": max(0, min(255, r)),
                    "g": max(0, min(255, g)),
                    "b": max(0, min(255, b)),
                }

        payload = {"layer1": layer}
        res = self.client.request("/6/ambilight/cached", method="POST", data=payload)
        self.cache.invalidate_live()
        return res

    def set_zones(
        self,
        left_rgb: Tuple[int, int, int],
        top_rgb: Tuple[int, int, int],
        right_rgb: Tuple[int, int, int],
    ) -> Dict[str, Any]:
        """Sets distinct RGB colors for Left, Top, and Right LED banks."""
        self.set_expert_mode()
        payload = {
            "layer1": {
                "left": {str(i): {"r": left_rgb[0], "g": left_rgb[1], "b": left_rgb[2]} for i in range(4)},
                "top": {str(i): {"r": top_rgb[0], "g": top_rgb[1], "b": top_rgb[2]} for i in range(8)},
                "right": {str(i): {"r": right_rgb[0], "g": right_rgb[1], "b": right_rgb[2]} for i in range(4)},
            }
        }
        res = self.client.request("/6/ambilight/cached", method="POST", data=payload)
        self.cache.invalidate_live()
        return res

    def set_style(self, style_name: str, algorithm: Optional[str] = None) -> Dict[str, Any]:
        """
        Switches Ambilight operating style.
        Switches mode back to 'internal' so the TV video/audio engine regains control.
        """
        self._is_expert = False
        try:
            self.client.request("/6/ambilight/mode", method="POST", data={"current": "internal"})
        except Exception:
            pass

        payload: Dict[str, Any] = {"styleName": style_name.upper()}
        if algorithm:
            payload["algorithm"] = algorithm.upper()
        res = self.client.request("/6/ambilight/currentconfiguration", method="POST", data=payload)
        self.cache.invalidate_status()
        self.cache.invalidate_live()
        return res

    def reset_to_video(self) -> Dict[str, Any]:
        """Restores standard video synchronization mode."""
        return self.set_style("FOLLOW_VIDEO")

    def send_key(self, key_name: str) -> Dict[str, Any]:
        """Sends a remote control key event (e.g. Home, Confirm, VolumeUp, Standby)."""
        return self.client.send_key(key_name)

    def send_sequence(self, sequence_name: str) -> List[Dict[str, Any]]:
        """Executes a known developer secret sequence macro."""
        seq_name = sequence_name.lower()
        if seq_name in PRESET_SEQUENCES:
            keys = PRESET_SEQUENCES[seq_name]
            return self.client.send_sequence(keys, delay_sec=0.25)
        raise ValueError(f"Unknown preset sequence '{sequence_name}'. Available: {list(PRESET_SEQUENCES.keys())}")

    def set_volume(self, level: int, muted: Optional[bool] = None) -> Dict[str, Any]:
        """Sets audio volume level (0-60) and mute state."""
        payload: Dict[str, Any] = {"current": max(0, min(60, int(level)))}
        if muted is not None:
            payload["muted"] = bool(muted)
        res = self.client.request("/6/audio/volume", method="POST", data=payload)
        self.cache.invalidate_status()
        return res


def stream_visualizer(controller: AmbilightController, fps: float = 10.0):
    """Renders a real-time TrueColor ANSI representation of the 16 Ambilight LEDs."""
    delay = 1.0 / max(1.0, min(20.0, fps))
    print("\033[2J\033[H", end="")
    print("🎯 Streaming Live Ambilight Telemetry (Ctrl+C to stop)...")

    try:
        while True:
            t0 = time.time()
            data = controller.get_live_colors()
            layer = data.get("layer1", {})
            left = layer.get("left", {})
            top = layer.get("top", {})
            right = layer.get("right", {})

            out = ["\033[H"]
            out.append("=== 🌈 PHILIPS TITAN OS LIVE AMBILIGHT MONITOR ===\n")
            out.append(f"Host: {controller.host} | Target: 16 Physical LEDs\n\n")

            top_blocks = []
            for i in range(8):
                led = top.get(str(i), {"r": 0, "g": 0, "b": 0})
                top_blocks.append(ansi_block(led["r"], led["g"], led["b"], width=6))
            out.append("       " + " ".join(top_blocks) + "\n")

            for i in range(4):
                l_led = left.get(str(i), {"r": 0, "g": 0, "b": 0})
                r_led = right.get(str(i), {"r": 0, "g": 0, "b": 0})
                l_block = ansi_block(l_led["r"], l_led["g"], l_led["b"], width=5)
                r_block = ansi_block(r_led["r"], r_led["g"], r_led["b"], width=5)
                screen_gap = " " * 52
                out.append(f"{l_block}  {screen_gap}  {r_block}\n")

            out.append("\n" + "-" * 66 + "\n")
            out.append("Press Ctrl+C to return to shell.\n")

            sys.stdout.write("".join(out))
            sys.stdout.flush()

            elapsed = time.time() - t0
            time.sleep(max(0.01, delay - elapsed))
    except KeyboardInterrupt:
        print("\n\n✓ Ambilight stream stopped cleanly.")


# -----------------------------------------------------------------------------
# Embedded Web Controller & Command Center GUI (Port 8088)
# -----------------------------------------------------------------------------
WEB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Philips Titan OS Command Center & Ambilight Studio</title>
    <style>
        :root {
            --bg: #0b0f19;
            --surface: #141c2e;
            --surface-hover: #1e2942;
            --surface-active: #283756;
            --border: #24324f;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.4);
            --neon-pink: #ec4899;
            --neon-green: #10b981;
            --neon-amber: #f59e0b;
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --text-muted: #64748b;
            --danger: #ef4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif;
            padding: 24px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }
        header {
            width: 100%;
            max-width: 1220px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }
        .header-title h1 {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, #38bdf8, #818cf8, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }
        .header-title .subtitle {
            font-size: 13px;
            color: var(--text-dim);
            margin-top: 4px;
        }
        .header-badges {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .badge {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-dim);
        }
        .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--neon-green);
            box-shadow: 0 0 8px var(--neon-green);
        }
        .dot.pulse {
            animation: pulse-dot 2s infinite ease-in-out;
        }
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.85); }
        }

        /* Main Dashboard Grid */
        .dashboard-grid {
            display: grid;
            grid-template-columns: 1.25fr 0.85fr;
            gap: 24px;
            width: 100%;
            max-width: 1220px;
        }
        @media (max-width: 980px) {
            .dashboard-grid { grid-template-columns: 1fr; }
        }

        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
            display: flex;
            flex-direction: column;
            gap: 18px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .card-title {
            font-size: 17px;
            font-weight: 700;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card-desc {
            font-size: 13px;
            color: var(--text-dim);
            margin-top: 2px;
        }

        /* Interactive TV Visualizer Frame */
        .tv-wrapper {
            position: relative;
            width: 100%;
            height: 300px;
            background: #020617;
            border-radius: 14px;
            border: 2px solid #1e293b;
            box-shadow: inset 0 0 40px rgba(0,0,0,0.85);
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            margin-top: 6px;
            user-select: none;
        }
        .tv-screen-center {
            text-align: center;
            z-index: 10;
        }
        .tv-model-badge {
            font-size: 20px;
            font-weight: 800;
            letter-spacing: 1px;
            color: #475569;
        }
        .tv-subtext {
            font-size: 12px;
            color: #334155;
            margin-top: 4px;
        }
        .tv-instruction {
            margin-top: 8px;
            font-size: 11px;
            color: var(--accent);
            font-family: monospace;
            background: rgba(15, 23, 42, 0.7);
            padding: 4px 10px;
            border-radius: 6px;
            border: 1px solid #1e293b;
            display: inline-block;
        }

        /* Physical 16 LEDs */
        .led-strip-top {
            position: absolute;
            top: 10px;
            left: 55px;
            right: 55px;
            height: 30px;
            display: grid;
            grid-template-columns: repeat(8, 1fr);
            gap: 8px;
            z-index: 20;
        }
        .led-strip-left {
            position: absolute;
            top: 50px;
            bottom: 50px;
            left: 10px;
            width: 32px;
            display: grid;
            grid-template-rows: repeat(4, 1fr);
            gap: 8px;
            z-index: 20;
        }
        .led-strip-right {
            position: absolute;
            top: 50px;
            bottom: 50px;
            right: 10px;
            width: 32px;
            display: grid;
            grid-template-rows: repeat(4, 1fr);
            gap: 8px;
            z-index: 20;
        }

        .led-node {
            background: #1e293b;
            border: 2px solid #334155;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 800;
            font-family: monospace;
            color: #cbd5e1;
            transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
            user-select: none;
            box-shadow: 0 0 6px rgba(0,0,0,0.5);
            position: relative;
        }
        .led-node:hover {
            transform: scale(1.15);
            border-color: #94a3b8;
            z-index: 30;
        }
        .led-node.selected {
            border: 2px solid #ffffff !important;
            box-shadow: 0 0 16px #38bdf8, 0 0 26px #38bdf8 !important;
            transform: scale(1.2);
            z-index: 40;
        }
        .led-node.selected::after {
            content: "✓";
            color: #ffffff;
            font-weight: 900;
            font-size: 13px;
            text-shadow: 0 0 4px #000, 0 0 8px #000;
            position: absolute;
        }

        /* Selection Controls */
        .selection-panel {
            display: flex;
            flex-direction: column;
            gap: 10px;
            background: #0f172a;
            border-radius: 12px;
            padding: 12px 16px;
            border: 1px solid var(--border);
        }
        .selection-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 8px;
        }
        .sel-count {
            font-size: 13px;
            font-weight: 700;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .chip-group {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }
        .chip {
            background: var(--surface-hover);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 5px 11px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            color: var(--text-dim);
            transition: all 0.15s;
            user-select: none;
        }
        .chip:hover {
            background: var(--surface-active);
            color: var(--text);
            border-color: var(--accent);
        }
        .chip.active-chip {
            background: #0284c7;
            border-color: #38bdf8;
            color: #fff;
        }

        /* Color Applicator Deck */
        .color-deck {
            display: flex;
            flex-direction: column;
            gap: 14px;
            background: #0f172a;
            border-radius: 12px;
            padding: 14px 18px;
            border: 1px solid var(--border);
        }
        .color-row {
            display: flex;
            align-items: center;
            gap: 14px;
            flex-wrap: wrap;
        }
        input[type="color"] {
            -webkit-appearance: none;
            border: none;
            width: 44px;
            height: 44px;
            border-radius: 8px;
            cursor: pointer;
            background: transparent;
        }
        input[type="color"]::-webkit-color-swatch-wrapper { padding: 0; }
        input[type="color"]::-webkit-color-swatch {
            border-radius: 8px;
            border: 2px solid var(--border);
            box-shadow: 0 0 10px rgba(0,0,0,0.4);
        }
        .hex-input {
            background: #1e293b;
            border: 1px solid var(--border);
            color: #fff;
            padding: 8px 12px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 14px;
            font-weight: 700;
            width: 100px;
            text-transform: uppercase;
        }
        .hex-input:focus {
            outline: none;
            border-color: var(--accent);
        }

        /* Brightness & Auto-Apply Row */
        .tool-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            flex-wrap: wrap;
        }
        .slider-group {
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
            min-width: 200px;
        }
        .slider-group span {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-dim);
            white-space: nowrap;
        }

        /* Preset Swatches */
        .palette-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .swatch {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            cursor: pointer;
            border: 2px solid transparent;
            transition: transform 0.15s, border-color 0.15s;
        }
        .swatch:hover {
            transform: scale(1.2);
            border-color: #fff;
            box-shadow: 0 0 12px rgba(255,255,255,0.4);
        }

        /* Mood Lighting Themes */
        .theme-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 8px;
        }
        .theme-btn {
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid var(--border);
            background: var(--surface-hover);
            color: var(--text);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.18s;
        }
        .theme-btn:hover {
            border-color: var(--accent);
            background: var(--surface-active);
            transform: translateY(-1px);
        }
        .theme-preview {
            width: 14px;
            height: 14px;
            border-radius: 4px;
            flex-shrink: 0;
        }

        /* Buttons */
        .btn-group {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        button {
            background: var(--surface-hover);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 9px 15px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.18s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            user-select: none;
        }
        button:hover {
            background: var(--surface-active);
            border-color: var(--accent);
            color: #fff;
            transform: translateY(-1px);
        }
        button:active {
            transform: translateY(1px);
        }
        button.primary {
            background: #0284c7;
            border-color: #38bdf8;
            color: #fff;
        }
        button.primary:hover {
            background: #0369a1;
            box-shadow: 0 0 14px var(--accent-glow);
        }
        button.success {
            background: #059669;
            border-color: #10b981;
        }
        button.danger {
            background: #b91c1c;
            border-color: #ef4444;
        }
        button.macro {
            background: #312e81;
            border-color: #6366f1;
        }
        button.macro:hover {
            background: #3730a3;
            box-shadow: 0 0 12px rgba(99, 102, 241, 0.4);
        }

        /* Remote Control Section */
        .remote-deck {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .dpad-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
            margin: 6px 0;
        }
        .dpad-row {
            display: flex;
            gap: 6px;
        }
        .dpad-btn {
            width: 64px;
            height: 52px;
            font-size: 17px;
            justify-content: center;
            border-radius: 10px;
            background: #1e293b;
            border-color: #334155;
        }
        .dpad-btn.ok-btn {
            background: #0284c7;
            border-color: #38bdf8;
            font-weight: 800;
            font-size: 15px;
            width: 74px;
        }
        .dpad-btn.ok-btn:hover {
            background: #0369a1;
        }

        /* Volume Deck */
        .vol-deck {
            display: flex;
            flex-direction: column;
            gap: 10px;
            background: #0f172a;
            border-radius: 12px;
            padding: 14px 18px;
            border: 1px solid var(--border);
        }
        .vol-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .vol-level {
            font-size: 15px;
            font-weight: 700;
            color: var(--accent);
            font-family: monospace;
        }
        .vol-slider-row {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        input[type="range"] {
            flex: 1;
            accent-color: var(--accent);
            cursor: pointer;
        }

        /* Secret Macro Cards */
        .macro-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        /* Status Toast Bar */
        .toast-bar {
            width: 100%;
            max-width: 1220px;
            margin-top: 20px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px 18px;
            font-size: 13px;
            font-family: monospace;
            color: var(--text-dim);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .toast-msg {
            color: var(--accent);
            font-weight: 600;
        }

        /* Toggle Switches */
        .switch-label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            font-size: 12px;
            color: var(--text-dim);
            font-weight: 600;
            user-select: none;
        }
        .switch-label input { cursor: pointer; }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>✨ PHILIPS TITAN OS COMMAND CENTER</h1>
            <div class="subtitle">JointSpace v6 Remote & Ambilight Studio • Target: <TV_IP></div>
        </div>
        <div class="header-badges">
            <label class="switch-label" title="Enable real-time LED mirroring (polls at 1.2 Hz)">
                <input type="checkbox" id="sync-toggle" checked onchange="toggleSync()">
                <span>Live Sync Mirror</span>
            </label>
            <div class="badge" id="screen-badge">
                <span class="dot pulse" id="screen-dot"></span>
                <span id="screen-text">Display: Active</span>
            </div>
            <div class="badge">
                <span class="dot" id="tv-status-dot"></span>
                <span id="tv-status-text">Connected</span>
            </div>
        </div>
    </header>

    <div class="dashboard-grid">
        <!-- LEFT COLUMN: AMBILIGHT STUDIO -->
        <div class="card">
            <div class="card-header">
                <div>
                    <div class="card-title">🌈 Ambilight Studio & Per-LED Canvas</div>
                    <div class="card-desc">Click or drag across LEDs to select. Shift-Click to select ranges. (Expert Mode)</div>
                </div>
                <button onclick="toggleAmbilightPower()">⚡ Toggle Power</button>
            </div>

            <!-- TV Screen Visualizer with 16 Interactive LEDs -->
            <div class="tv-wrapper" id="tv-canvas">
                <div class="led-strip-top" id="top-leds"></div>
                <div class="led-strip-left" id="left-leds"></div>
                <div class="led-strip-right" id="right-leds"></div>
                <div class="tv-screen-center">
                    <div class="tv-model-badge">55PUS8000</div>
                    <div class="tv-subtext">16 Physical RGB LEDs • Top (8) | Left (4) | Right (4)</div>
                    <div class="tv-instruction">💡 Tip: Drag mouse to paint-select • Shift+Click for ranges</div>
                </div>
            </div>

            <!-- Enhanced Selection Bar -->
            <div class="selection-panel">
                <div class="selection-header">
                    <div class="sel-count">
                        <span id="selection-label">0 of 16 LEDs selected</span>
                    </div>
                    <div class="chip-group">
                        <div class="chip" onclick="selectAllLEDs()">All (16)</div>
                        <div class="chip" onclick="clearLEDSelection()">Clear</div>
                        <div class="chip" onclick="invertLEDSelection()">Invert</div>
                        <div class="chip" onclick="selectZone('top')">Top (8)</div>
                        <div class="chip" onclick="selectZone('left')">Left (4)</div>
                        <div class="chip" onclick="selectZone('right')">Right (4)</div>
                        <div class="chip" onclick="selectZone('sides')">Sides (8)</div>
                        <div class="chip" onclick="selectZone('corners')">Corners (4)</div>
                    </div>
                </div>
            </div>

            <!-- Color Applicator & Tools -->
            <div class="color-deck">
                <div class="color-row">
                    <input type="color" id="color-input" value="#00f2fe" oninput="onColorChange(this.value)">
                    <input type="text" id="hex-input" class="hex-input" value="#00F2FE" maxlength="7" onchange="onHexInputChange(this.value)">
                    <button class="primary" onclick="applyToSelected()">Apply to Selected</button>
                    <button onclick="applyToAll()">Apply to All 16</button>
                    <label class="switch-label" style="margin-left: auto;">
                        <input type="checkbox" id="auto-apply-toggle" checked>
                        <span>⚡ Live Auto-Apply</span>
                    </label>
                </div>

                <!-- Swatches -->
                <div class="palette-row">
                    <div class="swatch" style="background: #00f2fe;" title="Cyber Cyan" onclick="pickColor('#00f2fe')"></div>
                    <div class="swatch" style="background: #ec4899;" title="Hot Pink" onclick="pickColor('#ec4899')"></div>
                    <div class="swatch" style="background: #8b5cf6;" title="Neon Purple" onclick="pickColor('#8b5cf6')"></div>
                    <div class="swatch" style="background: #f59e0b;" title="Sunset Amber" onclick="pickColor('#f59e0b')"></div>
                    <div class="swatch" style="background: #10b981;" title="Emerald Green" onclick="pickColor('#10b981')"></div>
                    <div class="swatch" style="background: #3b82f6;" title="Electric Blue" onclick="pickColor('#3b82f6')"></div>
                    <div class="swatch" style="background: #fbbf24;" title="Gold" onclick="pickColor('#fbbf24')"></div>
                    <div class="swatch" style="background: #ffffff;" title="Cool White (6500K)" onclick="pickColor('#ffffff')"></div>
                    <div class="swatch" style="background: #ffedd5;" title="Warm White (3000K)" onclick="pickColor('#ffedd5')"></div>
                    <div class="swatch" style="background: #020617; border: 1px solid #475569;" title="Black / Off" onclick="pickColor('#000000')"></div>
                </div>

                <!-- Brightness Slider -->
                <div class="tool-row">
                    <div class="slider-group">
                        <span>💡 Brightness:</span>
                        <input type="range" id="brightness-slider" min="0" max="100" value="100" oninput="onBrightnessChange(this.value)">
                        <span id="brightness-label" style="width: 40px; font-family: monospace;">100%</span>
                    </div>
                </div>
            </div>

            <!-- Mood Lighting Themes & Gradients -->
            <div>
                <div class="card-desc" style="margin-bottom: 8px;">Preset Lighting Themes & Gradients</div>
                <div class="theme-grid">
                    <div class="theme-btn" onclick="applyTheme('cyberpunk')">
                        <div class="theme-preview" style="background: linear-gradient(135deg, #00f2fe, #ec4899);"></div>
                        <span>Cyberpunk</span>
                    </div>
                    <div class="theme-btn" onclick="applyTheme('sunset')">
                        <div class="theme-preview" style="background: linear-gradient(135deg, #ff8800, #7928ca);"></div>
                        <span>Sunset Aurora</span>
                    </div>
                    <div class="theme-btn" onclick="applyTheme('nordic')">
                        <div class="theme-preview" style="background: linear-gradient(135deg, #00ff88, #0072ff);"></div>
                        <span>Nordic Forest</span>
                    </div>
                    <div class="theme-btn" onclick="applyTheme('rainbow')">
                        <div class="theme-preview" style="background: linear-gradient(135deg, #ff0000, #ffff00, #00ff00, #00ffff, #0000ff, #ff00ff);"></div>
                        <span>Rainbow Cycle</span>
                    </div>
                    <div class="theme-btn" onclick="applyTheme('cinema')">
                        <div class="theme-preview" style="background: #ffc58f;"></div>
                        <span>Cinema Warm</span>
                    </div>
                    <div class="theme-btn" onclick="applyTheme('studio')">
                        <div class="theme-preview" style="background: #ffffff;"></div>
                        <span>Studio 6500K</span>
                    </div>
                </div>
            </div>

            <!-- Styles & Dynamic Algorithms -->
            <div>
                <div class="card-desc" style="margin-bottom: 8px;">Switch Ambilight Dynamic Operating Modes</div>
                <div class="btn-group">
                    <button class="success" onclick="setStyle('FOLLOW_VIDEO')">🎬 Follow Video</button>
                    <button onclick="setStyle('FOLLOW_AUDIO', 'PARTY')">🎉 Audio Party</button>
                    <button onclick="setStyle('FOLLOW_AUDIO', 'VU_METER')">📊 VU Meter</button>
                    <button onclick="setStyle('FOLLOW_AUDIO', 'KNIGHT_RIDER_CLOCKWISE')">🚨 Knight Rider</button>
                    <button onclick="setStyle('FOLLOW_COLOR')">💡 Follow Color</button>
                    <button class="danger" onclick="setStyle('OFF')">⭕ Turn Off</button>
                </div>
            </div>
        </div>

        <!-- RIGHT COLUMN: REMOTE CONTROL & MACROS -->
        <div class="card">
            <div class="card-header">
                <div>
                    <div class="card-title">🎮 Full TV Remote & D-Pad Deck</div>
                    <div class="card-desc">Control menu navigation, volume, playback, and developer secrets</div>
                </div>
                <button class="danger" onclick="sendKey('Standby')">⚡ Standby</button>
            </div>

            <div class="remote-deck">
                <!-- Navigation Bar -->
                <div class="btn-group" style="justify-content: center;">
                    <button onclick="sendKey('Home')">🏠 Home</button>
                    <button onclick="sendKey('Back')">↩ Back</button>
                    <button onclick="sendKey('Options')">⚙️ Options</button>
                    <button onclick="sendKey('Source')">📺 Source</button>
                </div>

                <!-- D-Pad Directional Controls -->
                <div class="dpad-container">
                    <div class="dpad-row">
                        <button class="dpad-btn" onclick="sendKey('CursorUp')" title="Up (ArrowUp)">▲</button>
                    </div>
                    <div class="dpad-row">
                        <button class="dpad-btn" onclick="sendKey('CursorLeft')" title="Left (ArrowLeft)">◀</button>
                        <button class="dpad-btn ok-btn" onclick="sendKey('Confirm')" title="OK / Confirm (Enter)">OK</button>
                        <button class="dpad-btn" onclick="sendKey('CursorRight')" title="Right (ArrowRight)">▶</button>
                    </div>
                    <div class="dpad-row">
                        <button class="dpad-btn" onclick="sendKey('CursorDown')" title="Down (ArrowDown)">▼</button>
                    </div>
                </div>

                <!-- Volume Deck -->
                <div class="vol-deck">
                    <div class="vol-header">
                        <span style="font-size: 13px; font-weight: 600;">🔊 Audio Volume</span>
                        <span class="vol-level" id="vol-level-text">13 / 60</span>
                    </div>
                    <div class="vol-slider-row">
                        <button onclick="sendKey('VolumeDown')">🔉 -</button>
                        <input type="range" id="vol-slider" min="0" max="60" value="13" onchange="applyVolumeSlider(this.value)">
                        <button onclick="sendKey('VolumeUp')">🔊 +</button>
                        <button onclick="sendKey('Mute')">🔇 Mute</button>
                    </div>
                </div>

                <!-- Media Controls -->
                <div class="btn-group" style="justify-content: center;">
                    <button onclick="sendKey('Rewind')">⏮ Prev</button>
                    <button onclick="sendKey('Play')">▶ Play</button>
                    <button onclick="sendKey('Pause')">⏸ Pause</button>
                    <button onclick="sendKey('FastForward')">⏭ Next</button>
                </div>

                <!-- Developer Secrets & Macro Sequence Deck -->
                <div>
                    <div class="card-desc" style="margin-bottom: 8px;">Developer & System Secret Sequences</div>
                    <div class="macro-grid">
                        <button class="macro" onclick="triggerSequence('devmenu')">🛠️ Developer Menu</button>
                        <button class="macro" onclick="triggerSequence('logs')">📜 On-Screen Logs</button>
                        <button class="macro" onclick="triggerSequence('player-debug')">📈 Player Debug HUD</button>
                        <button class="macro" onclick="triggerSequence('reload')">🔄 Reload Launcher</button>
                        <button class="macro" onclick="triggerSequence('qa-bundle')">📦 Export QA Telemetry</button>
                        <button class="macro" onclick="triggerSequence('screensaver')">🖼️ Screensaver</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Status Toast Bar -->
    <div class="toast-bar">
        <div>Activity: <span class="toast-msg" id="status-toast">Ready</span></div>
        <div id="status-timing">Latency: ~24ms</div>
    </div>

    <script>
        // Perimeter mapping of the 16 LEDs in clockwise sequence around the bezel
        var PERIMETER_LEDS = [
            'left-3', 'left-2', 'left-1', 'left-0',
            'top-0', 'top-1', 'top-2', 'top-3', 'top-4', 'top-5', 'top-6', 'top-7',
            'right-0', 'right-1', 'right-2', 'right-3'
        ];

        // State
        var selectedLEDs = new Set();
        var isSyncEnabled = true;
        var lastUserAction = 0;
        var currentAmbilightPower = "On";
        var isMouseDown = false;
        var dragSelectMode = true; // true = selecting, false = deselecting
        var lastClickedKey = null;

        // LED Layout Containers
        var topStrip = document.getElementById('top-leds');
        var leftStrip = document.getElementById('left-leds');
        var rightStrip = document.getElementById('right-leds');

        // Build Top LEDs (0 to 7)
        for (var i = 0; i < 8; i++) {
            var el = document.createElement('div');
            el.className = 'led-node';
            el.id = 'led-top-' + i;
            el.innerText = 'T' + i;
            bindLEDDragEvents(el, 'top-' + i);
            topStrip.appendChild(el);
        }

        // Build Left LEDs (0 to 3)
        for (var j = 0; j < 4; j++) {
            var el_l = document.createElement('div');
            el_l.className = 'led-node';
            el_l.id = 'led-left-' + j;
            el_l.innerText = 'L' + j;
            bindLEDDragEvents(el_l, 'left-' + j);
            leftStrip.appendChild(el_l);
        }

        // Build Right LEDs (0 to 3)
        for (var k = 0; k < 4; k++) {
            var el_r = document.createElement('div');
            el_r.className = 'led-node';
            el_r.id = 'led-right-' + k;
            el_r.innerText = 'R' + k;
            bindLEDDragEvents(el_r, 'right-' + k);
            rightStrip.appendChild(el_r);
        }

        // Mouse listeners for drag-to-select across LED nodes
        window.addEventListener('mousedown', function() { isMouseDown = true; });
        window.addEventListener('mouseup', function() { isMouseDown = false; });

        function bindLEDDragEvents(el, key) {
            el.addEventListener('mousedown', function(e) {
                e.preventDefault();
                isMouseDown = true;
                if (e.shiftKey && lastClickedKey) {
                    selectRange(lastClickedKey, key);
                } else {
                    dragSelectMode = !selectedLEDs.has(key);
                    setLEDSelected(key, dragSelectMode);
                }
                lastClickedKey = key;
                updateSelectionCount();
                lastUserAction = Date.now();
                if (document.getElementById('auto-apply-toggle').checked && selectedLEDs.has(key)) {
                    debouncedApplyToSelected(100);
                }
            });

            el.addEventListener('mouseenter', function() {
                if (isMouseDown) {
                    setLEDSelected(key, dragSelectMode);
                    lastClickedKey = key;
                    updateSelectionCount();
                    lastUserAction = Date.now();
                    if (document.getElementById('auto-apply-toggle').checked && dragSelectMode) {
                        debouncedApplyToSelected(100);
                    }
                }
            });
        }

        function setLEDSelected(key, isSelected) {
            var el = document.getElementById('led-' + key);
            if (isSelected) {
                selectedLEDs.add(key);
                if (el) el.classList.add('selected');
            } else {
                selectedLEDs.delete(key);
                if (el) el.classList.remove('selected');
            }
        }

        // Shift-Click Range Selection along the perimeter
        function selectRange(startKey, endKey) {
            var idx1 = PERIMETER_LEDS.indexOf(startKey);
            var idx2 = PERIMETER_LEDS.indexOf(endKey);
            if (idx1 === -1 || idx2 === -1) return;

            var minIdx = Math.min(idx1, idx2);
            var maxIdx = Math.max(idx1, idx2);
            for (var i = minIdx; i <= maxIdx; i++) {
                setLEDSelected(PERIMETER_LEDS[i], true);
            }
            updateSelectionCount();
        }

        function selectAllLEDs() {
            PERIMETER_LEDS.forEach(function(k) { setLEDSelected(k, true); });
            updateSelectionCount();
            lastUserAction = Date.now();
        }

        function clearLEDSelection() {
            PERIMETER_LEDS.forEach(function(k) { setLEDSelected(k, false); });
            updateSelectionCount();
            lastUserAction = Date.now();
        }

        function invertLEDSelection() {
            PERIMETER_LEDS.forEach(function(k) {
                setLEDSelected(k, !selectedLEDs.has(k));
            });
            updateSelectionCount();
            lastUserAction = Date.now();
        }

        function selectZone(zone) {
            clearLEDSelection();
            if (zone === 'top') {
                for (var i = 0; i < 8; i++) setLEDSelected('top-' + i, true);
            } else if (zone === 'left') {
                for (var j = 0; j < 4; j++) setLEDSelected('left-' + j, true);
            } else if (zone === 'right') {
                for (var k = 0; k < 4; k++) setLEDSelected('right-' + k, true);
            } else if (zone === 'sides') {
                for (var j = 0; j < 4; j++) setLEDSelected('left-' + j, true);
                for (var k = 0; k < 4; k++) setLEDSelected('right-' + k, true);
            } else if (zone === 'corners') {
                setLEDSelected('left-0', true);
                setLEDSelected('left-3', true);
                setLEDSelected('right-0', true);
                setLEDSelected('right-3', true);
            }
            updateSelectionCount();
            lastUserAction = Date.now();
        }

        function updateSelectionCount() {
            document.getElementById('selection-label').innerText = selectedLEDs.size + ' of 16 LEDs selected';
        }

        var colorInput = document.getElementById('color-input');
        var hexInput = document.getElementById('hex-input');

        var debounceTimer = null;
        function debouncedApplyToSelected(delayMs) {
            if (debounceTimer) clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function() {
                applyToSelected();
            }, delayMs || 60);
        }

        var debounceAllTimer = null;
        function debouncedApplyToAll(delayMs) {
            if (debounceAllTimer) clearTimeout(debounceAllTimer);
            debounceAllTimer = setTimeout(function() {
                applyToAll();
            }, delayMs || 60);
        }

        function onColorChange(val) {
            hexInput.value = val.toUpperCase();
            lastUserAction = Date.now();
            if (document.getElementById('auto-apply-toggle').checked && selectedLEDs.size > 0) {
                debouncedApplyToSelected(60);
            }
        }

        function onHexInputChange(val) {
            val = val.trim();
            if (!val.startsWith('#')) val = '#' + val;
            if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
                colorInput.value = val;
                hexInput.value = val.toUpperCase();
                lastUserAction = Date.now();
                if (document.getElementById('auto-apply-toggle').checked && selectedLEDs.size > 0) {
                    debouncedApplyToSelected(60);
                }
            }
        }

        function pickColor(hex) {
            colorInput.value = hex;
            hexInput.value = hex.toUpperCase();
            lastUserAction = Date.now();
            if (document.getElementById('auto-apply-toggle').checked) {
                if (selectedLEDs.size > 0) {
                    debouncedApplyToSelected(30);
                } else {
                    debouncedApplyToAll(30);
                }
            }
        }

        function onBrightnessChange(val) {
            document.getElementById('brightness-label').innerText = val + '%';
            lastUserAction = Date.now();
            if (selectedLEDs.size > 0) {
                debouncedApplyToSelected(60);
            }
        }

        function setToast(msg, isError) {
            var el = document.getElementById('status-toast');
            el.innerText = msg;
            el.style.color = isError ? 'var(--danger)' : 'var(--accent)';
        }

        function toggleSync() {
            isSyncEnabled = document.getElementById('sync-toggle').checked;
            setToast(isSyncEnabled ? 'Live Sync Mirror enabled' : 'Live Sync Mirror paused');
        }

        function hexToRgb(hex) {
            var c = hex.replace('#', '');
            return {
                r: parseInt(c.substr(0, 2), 16),
                g: parseInt(c.substr(2, 2), 16),
                b: parseInt(c.substr(4, 2), 16)
            };
        }

        // Apply to Selected LEDs
        function applyToSelected() {
            if (selectedLEDs.size === 0) {
                setToast('Please select one or more LEDs on the TV frame first.', true);
                return;
            }
            var hex = colorInput.value;
            var baseRGB = hexToRgb(hex);
            var brightness = parseInt(document.getElementById('brightness-slider').value, 10) / 100.0;
            var r = Math.round(baseRGB.r * brightness);
            var g = Math.round(baseRGB.g * brightness);
            var b = Math.round(baseRGB.b * brightness);
            var rgbString = 'rgb(' + r + ',' + g + ',' + b + ')';

            var updates = [];
            selectedLEDs.forEach(function(key) {
                var parts = key.split('-');
                var side = parts[0];
                var idx = parseInt(parts[1], 10);
                updates.push({ side: side, index: idx, r: r, g: g, b: b });

                var el = document.getElementById('led-' + key);
                if (el) {
                    el.style.backgroundColor = rgbString;
                    el.style.boxShadow = '0 0 14px ' + rgbString;
                }
            });

            lastUserAction = Date.now();
            fetch('/api/leds', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ updates: updates })
            })
            .then(function(res) { return res.json(); })
            .then(function(d) { setToast('✓ Applied to ' + updates.length + ' LEDs (RGB: ' + r + ', ' + g + ', ' + b + ')'); })
            .catch(function(e) { setToast('Error: ' + e.message, true); });
        }

        // Apply to All 16 LEDs
        function applyToAll() {
            var hex = colorInput.value;
            var baseRGB = hexToRgb(hex);
            var brightness = parseInt(document.getElementById('brightness-slider').value, 10) / 100.0;
            var r = Math.round(baseRGB.r * brightness);
            var g = Math.round(baseRGB.g * brightness);
            var b = Math.round(baseRGB.b * brightness);
            var rgbString = 'rgb(' + r + ',' + g + ',' + b + ')';

            lastUserAction = Date.now();
            fetch('/api/color', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hex: hex })
            })
            .then(function(res) { return res.json(); })
            .then(function(d) {
                setToast('✓ Solid color sent to all 16 LEDs in Expert Mode');
                document.querySelectorAll('.led-node').forEach(function(el) {
                    el.style.backgroundColor = rgbString;
                    el.style.boxShadow = '0 0 12px ' + rgbString;
                });
            })
            .catch(function(e) { setToast('Error: ' + e.message, true); });
        }

        // Mood Lighting Themes & Gradients
        function applyTheme(theme) {
            lastUserAction = Date.now();
            var updates = [];

            function interpolate(c1, c2, factor) {
                return {
                    r: Math.round(c1.r + factor * (c2.r - c1.r)),
                    g: Math.round(c1.g + factor * (c2.g - c1.g)),
                    b: Math.round(c1.b + factor * (c2.b - c1.b))
                };
            }

            function hsvToRgb(h, s, v) {
                var f = function(n) {
                    var k = (n + h / 60) % 6;
                    return v - v * s * Math.max(Math.min(k, 4 - k, 1), 0);
                };
                return {
                    r: Math.round(f(5) * 255),
                    g: Math.round(f(3) * 255),
                    b: Math.round(f(1) * 255)
                };
            }

            for (var i = 0; i < PERIMETER_LEDS.length; i++) {
                var key = PERIMETER_LEDS[i];
                var parts = key.split('-');
                var factor = i / (PERIMETER_LEDS.length - 1);
                var rgb = { r: 255, g: 255, b: 255 };

                if (theme === 'cyberpunk') {
                    rgb = interpolate(hexToRgb('#00f2fe'), hexToRgb('#ec4899'), factor);
                } else if (theme === 'sunset') {
                    rgb = interpolate(hexToRgb('#ff8800'), hexToRgb('#7928ca'), factor);
                } else if (theme === 'nordic') {
                    rgb = interpolate(hexToRgb('#00ff88'), hexToRgb('#0072ff'), factor);
                } else if (theme === 'rainbow') {
                    rgb = hsvToRgb(i * (360 / 16), 1.0, 1.0);
                } else if (theme === 'cinema') {
                    rgb = hexToRgb('#ffc58f');
                } else if (theme === 'studio') {
                    rgb = hexToRgb('#ffffff');
                }

                updates.push({ side: parts[0], index: parseInt(parts[1], 10), r: rgb.r, g: rgb.g, b: rgb.b });

                var el = document.getElementById('led-' + key);
                if (el) {
                    var s = 'rgb(' + rgb.r + ',' + rgb.g + ',' + rgb.b + ')';
                    el.style.backgroundColor = s;
                    el.style.boxShadow = '0 0 14px ' + s;
                }
            }

            setToast('Applying theme: ' + theme + ' across 16 LEDs...');
            fetch('/api/leds', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ updates: updates })
            })
            .then(function(res) { return res.json(); })
            .then(function(d) { setToast('✓ Theme ' + theme.toUpperCase() + ' applied successfully'); })
            .catch(function(e) { setToast('Theme error: ' + e.message, true); });
        }

        // Style Switcher
        function setStyle(styleName, algorithm) {
            lastUserAction = Date.now();
            setToast('Switching style to ' + styleName + '...');
            fetch('/api/style', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ style: styleName, algorithm: algorithm })
            })
            .then(function(r) { return r.json(); })
            .then(function(d) { setToast('✓ Active style: ' + styleName + (algorithm ? ' (' + algorithm + ')' : '')); })
            .catch(function(e) { setToast('Error: ' + e.message, true); });
        }

        function toggleAmbilightPower() {
            var nextPower = (currentAmbilightPower === "On") ? "Off" : "On";
            setToast('Setting Ambilight power to ' + nextPower + '...');
            fetch('/api/ambilight/power', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ power: nextPower })
            })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                currentAmbilightPower = nextPower;
                setToast('✓ Ambilight power: ' + nextPower);
            })
            .catch(function(e) { setToast('Error: ' + e.message, true); });
        }

        // Remote Key Injection
        function sendKey(keyName) {
            lastUserAction = Date.now();
            setToast('Sending remote key: ' + keyName + '...');
            fetch('/api/key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: keyName })
            })
            .then(function(r) { return r.json(); })
            .then(function(d) { setToast('✓ Sent key: ' + keyName); })
            .catch(function(e) { setToast('Error sending key: ' + e.message, true); });
        }

        // Volume
        function applyVolumeSlider(val) {
            document.getElementById('vol-level-text').innerText = val + ' / 60';
            fetch('/api/volume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ current: parseInt(val, 10) })
            })
            .then(function(r) { return r.json(); })
            .then(function(d) { setToast('✓ Volume set to ' + val); })
            .catch(function(e) { setToast('Volume error: ' + e.message, true); });
        }

        // Secret Sequence Macros
        function triggerSequence(seqName) {
            lastUserAction = Date.now();
            setToast('Executing macro sequence: ' + seqName + '...');
            fetch('/api/sequence', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sequence: seqName })
            })
            .then(function(r) { return r.json(); })
            .then(function(d) { setToast('✓ Triggered macro: ' + seqName + ' successfully'); })
            .catch(function(e) { setToast('Macro error: ' + e.message, true); });
        }

        // Physical Keyboard listener for TV D-Pad navigation
        window.addEventListener('keydown', function(e) {
            if (e.target.tagName === 'INPUT') return;
            if (e.key === 'ArrowUp') { e.preventDefault(); sendKey('CursorUp'); }
            else if (e.key === 'ArrowDown') { e.preventDefault(); sendKey('CursorDown'); }
            else if (e.key === 'ArrowLeft') { e.preventDefault(); sendKey('CursorLeft'); }
            else if (e.key === 'ArrowRight') { e.preventDefault(); sendKey('CursorRight'); }
            else if (e.key === 'Enter') { e.preventDefault(); sendKey('Confirm'); }
            else if (e.key === 'Escape' || e.key === 'Backspace') { e.preventDefault(); sendKey('Back'); }
        });

        // Background polling for TV status & LED mirror (calm 1.2s interval)
        function pollTelemetry() {
            if (!isSyncEnabled) return;
            // Pause mirror if user interacted in the last 2.5 seconds to prevent race conditions
            if (Date.now() - lastUserAction < 2500) return;

            var t0 = Date.now();
            fetch('/api/live')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var elapsed = Date.now() - t0;
                    document.getElementById('status-timing').innerText = 'Latency: ~' + elapsed + 'ms';
                    document.getElementById('tv-status-text').innerText = 'Connected';
                    document.getElementById('tv-status-dot').style.background = 'var(--neon-green)';

                    var layer = data.layer1 || {};
                    var left = layer.left || {};
                    var top = layer.top || {};
                    var right = layer.right || {};

                    for (var i = 0; i < 8; i++) {
                        var c = top[String(i)] || { r: 0, g: 0, b: 0 };
                        var el = document.getElementById('led-top-' + i);
                        if (el && !el.classList.contains('selected')) {
                            var rgb = 'rgb(' + c.r + ',' + c.g + ',' + c.b + ')';
                            el.style.backgroundColor = rgb;
                            el.style.boxShadow = '0 0 10px ' + rgb;
                        }
                    }
                    for (var j = 0; j < 4; j++) {
                        var cl = left[String(j)] || { r: 0, g: 0, b: 0 };
                        var cr = right[String(j)] || { r: 0, g: 0, b: 0 };
                        var el_l = document.getElementById('led-left-' + j);
                        var el_r = document.getElementById('led-right-' + j);
                        if (el_l && !el_l.classList.contains('selected')) {
                            var rgbl = 'rgb(' + cl.r + ',' + cl.g + ',' + cl.b + ')';
                            el_l.style.backgroundColor = rgbl;
                            el_l.style.boxShadow = '0 0 10px ' + rgbl;
                        }
                        if (el_r && !el_r.classList.contains('selected')) {
                            var rgbr = 'rgb(' + cr.g + ',' + cr.g + ',' + cr.b + ')';
                            el_r.style.backgroundColor = rgbr;
                            el_r.style.boxShadow = '0 0 10px ' + rgbr;
                        }
                    }
                })
                .catch(function(e) {
                    document.getElementById('tv-status-text').innerText = 'Reconnecting';
                    document.getElementById('tv-status-dot').style.background = 'var(--danger)';
                });
        }

        // Slow poll for TV System State (Volume, Screen Power, Ambilight Power) every 3.5 seconds
        function pollSystemStatus() {
            fetch('/api/status')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    // JointSpace screenstate interpretation:
                    // If display_power is 'On' or screenstate is 'Off', the screen panel is actively ON.
                    var dispLabel = data.display_label || (data.screenstate && data.screenstate.screenstate === 'Off' ? 'Display: On' : 'Display: Active');
                    if (data.context && data.context.level1 && data.context.level1 !== 'NA') {
                        dispLabel += ' (' + data.context.level1 + ')';
                    }
                    document.getElementById('screen-text').innerText = dispLabel;
                    document.getElementById('screen-dot').style.background = 'var(--neon-green)';

                    if (data.volume && data.volume.current !== undefined) {
                        var v = data.volume.current;
                        document.getElementById('vol-level-text').innerText = v + ' / 60' + (data.volume.muted ? ' (Muted)' : '');
                        document.getElementById('vol-slider').value = v;
                    }
                    if (data.ambilight_power && data.ambilight_power.power) {
                        currentAmbilightPower = data.ambilight_power.power;
                    }
                })
                .catch(function(e) {
                    document.getElementById('screen-text').innerText = 'Display: Standby';
                    document.getElementById('screen-dot').style.background = 'var(--neon-amber)';
                });
        }

        setInterval(pollTelemetry, 1500);
        setInterval(pollSystemStatus, 6000);
        pollSystemStatus();
    </script>
</body>
</html>
"""


class WebStudioHandler(http.server.SimpleHTTPRequestHandler):
    """Handles REST API and Web UI requests for the TV Command Center."""

    controller: Optional[AmbilightController] = None

    def log_message(self, format: str, *args: Any) -> None:
        """Filter out noisy /api/live polling logs to keep terminal readable."""
        if len(args) > 0 and "/api/live" in str(args[0]):
            return
        super().log_message(format, *args)

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(WEB_HTML.encode("utf-8"))

        elif self.path == "/api/live":
            try:
                data = self.controller.get_live_colors() if self.controller else {}
                body = json.dumps(data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif self.path == "/api/status":
            try:
                data = self.controller.get_system_status() if self.controller else {}
                body = json.dumps(data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body) if body else {}

        if self.path == "/api/color":
            hex_code = payload.get("hex", "#FFFFFF")
            r, g, b = hex_to_rgb(hex_code)
            res = self.controller.set_color_all(r, g, b) if self.controller else {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "hex": hex_code, "response": res}).encode("utf-8"))

        elif self.path == "/api/led":
            side = payload.get("side", "top")
            idx = int(payload.get("index", 0))
            if "hex" in payload:
                r, g, b = hex_to_rgb(payload["hex"])
            else:
                r, g, b = int(payload.get("r", 255)), int(payload.get("g", 255)), int(payload.get("b", 255))
            res = self.controller.set_led(side, idx, r, g, b) if self.controller else {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "side": side, "index": idx, "response": res}).encode("utf-8"))

        elif self.path == "/api/leds":
            updates = payload.get("updates", [])
            res = self.controller.set_leds_batch(updates) if self.controller else {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "count": len(updates), "response": res}).encode("utf-8"))

        elif self.path == "/api/style":
            style_name = payload.get("style", "FOLLOW_VIDEO")
            algorithm = payload.get("algorithm")
            res = self.controller.set_style(style_name, algorithm) if self.controller else {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "style": style_name, "response": res}).encode("utf-8"))

        elif self.path == "/api/ambilight/power":
            power_val = payload.get("power", "On")
            res = self.controller.set_power(power_val) if self.controller else {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "power": power_val, "response": res}).encode("utf-8"))

        elif self.path == "/api/key":
            key_name = payload.get("key", "Confirm")
            res = self.controller.send_key(key_name) if self.controller else {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "key": key_name, "response": res}).encode("utf-8"))

        elif self.path == "/api/volume":
            current_vol = payload.get("current", 15)
            muted = payload.get("muted")
            res = self.controller.set_volume(current_vol, muted=muted) if self.controller else {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "volume": current_vol, "response": res}).encode("utf-8"))

        elif self.path == "/api/sequence":
            seq_name = payload.get("sequence", "devmenu")
            res = self.controller.send_sequence(seq_name) if self.controller else {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "sequence": seq_name, "response": res}).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()


def start_web_studio(controller: AmbilightController, port: int = WEB_PORT):
    WebStudioHandler.controller = controller
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), WebStudioHandler) as httpd:
        print(f"✨ Philips Titan OS Command Center active at: http://localhost:{port}")
        print("   • Real-Time Interactive 16-LED Canvas (Top, Left, Right)")
        print("   • Advanced Multi-Select: Drag-to-paint, Shift-Click range, Zones, Invert, Clear")
        print("   • Mood Lighting Themes & Gradients: Cyberpunk, Sunset, Nordic, HSV Rainbow")
        print("   • Full Remote Control D-Pad, Volume Slider & Navigation Deck")
        print("   • Secret Developer Macro Sequences (WhaleTV / Titan OS)")
        print("   • Daemon-Safe Throttling & Caching (Zero Network Flooding)")
        print("   Press Ctrl+C to terminate.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n✓ Command Center stopped cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Philips Titan OS Command Center & Ambilight Studio")
    parser.add_argument("--host", "-H", help="TV IP address (defaults to .jointspace_credentials.json or env)")

    sub = parser.add_subparsers(dest="cmd", required=True)

    # 1. Stream
    p_stream = sub.add_parser("stream", help="Stream live ANSI TrueColor LED visualizer in terminal")
    p_stream.add_argument("--fps", type=float, default=10.0, help="Frames per second (default: 10)")

    # 2. Set solid color
    p_color = sub.add_parser("color", help="Set static solid color across all Ambilight LEDs")
    p_color.add_argument("hex", help="Hex color code (e.g. #00F2FE, #EC4899, #8B5CF6)")

    # 3. Set individual LED
    p_led = sub.add_parser("led", help="Set individual LED color on top, left, or right strip")
    p_led.add_argument("side", choices=["top", "left", "right"], help="LED strip location")
    p_led.add_argument("index", type=int, help="LED index (top: 0-7, left: 0-3, right: 0-3)")
    p_led.add_argument("hex", help="Hex color code (e.g. #FF0055)")

    # 4. Set style
    p_style = sub.add_parser("style", help="Switch Ambilight style mode")
    p_style.add_argument(
        "name",
        choices=["video", "audio", "color", "off"],
        help="Style mode: video (Follow Video), audio (Follow Audio), color, off",
    )
    p_style.add_argument(
        "--algo",
        choices=["PARTY", "STROBE", "VU_METER", "KNIGHT_RIDER_CLOCKWISE", "SPECTRUM_ANALYZER"],
        help="Audio algorithm",
    )

    # 5. Remote key
    p_key = sub.add_parser("key", help="Send remote control key event (e.g. Home, Confirm, Standby)")
    p_key.add_argument("name", help="Key name (Confirm, Home, Back, VolumeUp, VolumeDown, Standby)")

    # 6. Web GUI
    p_web = sub.add_parser("web", help="Launch interactive Command Center Web UI on port 8088")
    p_web.add_argument("-p", "--port", type=int, default=WEB_PORT, help=f"HTTP port (default: {WEB_PORT})")

    # 7. Info
    p_info = sub.add_parser("info", help="Query Ambilight topology, current configuration, and status")

    args = parser.parse_args()
    host = resolve_host(args)
    ctrl = AmbilightController(host)

    if args.cmd == "stream":
        stream_visualizer(ctrl, fps=args.fps)
    elif args.cmd == "color":
        r, g, b = hex_to_rgb(args.hex)
        res = ctrl.set_color_all(r, g, b)
        print(f"✓ Sent color {args.hex} (R:{r} G:{g} B:{b}) to all 16 LEDs: {res}")
    elif args.cmd == "led":
        r, g, b = hex_to_rgb(args.hex)
        res = ctrl.set_led(args.side, args.index, r, g, b)
        print(f"✓ Set {args.side.upper()} LED #{args.index} to {args.hex}: {res}")
    elif args.cmd == "style":
        style_map = {
            "video": "FOLLOW_VIDEO",
            "audio": "FOLLOW_AUDIO",
            "color": "FOLLOW_COLOR",
            "off": "OFF",
        }
        res = ctrl.set_style(style_map[args.name], args.algo)
        print(f"✓ Switched Ambilight style to {style_map[args.name]}: {res}")
    elif args.cmd == "key":
        res = ctrl.send_key(args.name)
        print(f"✓ Sent key '{args.name}' to TV: {res}")
    elif args.cmd == "web":
        start_web_studio(ctrl, port=args.port)
    elif args.cmd == "info":
        print("=== AMBILIGHT TOPOLOGY ===")
        print(json.dumps(ctrl.get_topology(), indent=2))
        print("\n=== CURRENT CONFIGURATION ===")
        print(json.dumps(ctrl.get_current_configuration(), indent=2))
        print("\n=== SYSTEM STATUS ===")
        print(json.dumps(ctrl.get_system_status(), indent=2))


if __name__ == "__main__":
    main()
