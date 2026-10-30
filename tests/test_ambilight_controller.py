#!/usr/bin/env python3
import unittest
from unittest.mock import MagicMock, patch
from tools.ambilight_controller import hex_to_rgb, rgb_to_hex, AmbilightController, TelemetryCache


class TestAmbilightController(unittest.TestCase):
    def test_hex_conversion(self):
        self.assertEqual(hex_to_rgb("#FF0055"), (255, 0, 85))
        self.assertEqual(hex_to_rgb("00FF00"), (0, 255, 0))
        self.assertEqual(hex_to_rgb("#FFF"), (255, 255, 255))
        self.assertEqual(rgb_to_hex(255, 0, 85), "#ff0055")

    def test_invalid_hex(self):
        with self.assertRaises(ValueError):
            hex_to_rgb("#12345")

    def test_telemetry_cache(self):
        cache = TelemetryCache(live_ttl=1.0)
        mock_client = MagicMock()
        mock_client.request.return_value = {"layer1": {"top": {}}}

        # First fetch calls request
        data1 = cache.get_live(mock_client)
        self.assertEqual(mock_client.request.call_count, 1)

        # Immediate second fetch returns cached without extra request
        data2 = cache.get_live(mock_client)
        self.assertEqual(mock_client.request.call_count, 1)
        self.assertEqual(data1, data2)

        # Invalidation forces new request
        cache.invalidate_live()
        cache.get_live(mock_client)
        self.assertEqual(mock_client.request.call_count, 2)

    @patch("tools.ambilight_controller.JointSpaceClient")
    def test_set_led_invalid_side(self, mock_js):
        ctrl = AmbilightController("127.0.0.1")
        with self.assertRaises(ValueError):
            ctrl.set_led("bottom", 0, 255, 255, 255)

    @patch("tools.ambilight_controller.JointSpaceClient")
    def test_set_color_all(self, mock_js):
        ctrl = AmbilightController("127.0.0.1")
        ctrl.client.request = MagicMock(return_value={})
        ctrl.set_color_all(255, 128, 0)

        # Check that cached was posted with 16 LEDs
        calls = ctrl.client.request.call_args_list
        cached_call = [c for c in calls if c[0][0] == "/6/ambilight/cached"]
        self.assertTrue(len(cached_call) > 0)
        payload = cached_call[0][1]["data"]
        self.assertIn("layer1", payload)
        self.assertEqual(len(payload["layer1"]["top"]), 8)
        self.assertEqual(len(payload["layer1"]["left"]), 4)
        self.assertEqual(len(payload["layer1"]["right"]), 4)
        self.assertEqual(payload["layer1"]["top"]["0"], {"r": 255, "g": 128, "b": 0})

    @patch("tools.ambilight_controller.JointSpaceClient")
    def test_set_leds_batch(self, mock_js):
        ctrl = AmbilightController("127.0.0.1")
        ctrl.client.request = MagicMock(return_value={})
        updates = [
            {"side": "top", "index": 2, "r": 255, "g": 0, "b": 0},
            {"side": "left", "index": 1, "r": 0, "g": 255, "b": 0},
        ]
        ctrl.set_leds_batch(updates)
        cached_call = [c for c in ctrl.client.request.call_args_list if c[0][0] == "/6/ambilight/cached"]
        self.assertTrue(len(cached_call) > 0)
        payload = cached_call[0][1]["data"]["layer1"]
        self.assertEqual(payload["top"]["2"], {"r": 255, "g": 0, "b": 0})
        self.assertEqual(payload["left"]["1"], {"r": 0, "g": 255, "b": 0})


if __name__ == "__main__":
    unittest.main()
