#!/usr/bin/env python3
import base64
import unittest
from unittest.mock import MagicMock, patch

from tools.jointspace_client import JointSpaceClient, create_signature

TEST_SECRET = base64.b64encode(b"public-test-secret").decode("ascii")


class TestJointSpaceClient(unittest.TestCase):

    def test_create_signature(self):
        secret = base64.b64decode(TEST_SECRET)
        sig = create_signature(secret, 12345678, "9999")
        self.assertIsInstance(sig, str)
        self.assertTrue(len(sig) > 10)

    @patch("requests.Session.request")
    def test_get_network_devices(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.text = '[{"id": "wifi0", "mac": "02:00:00:00:00:00"}]'
        mock_resp.json.return_value = [{"id": "wifi0", "mac": "02:00:00:00:00:00"}]
        mock_request.return_value = mock_resp

        client = JointSpaceClient(
            "192.0.2.10",
            port=1926,
            protocol="https",
            username="testuser",
            password="testpass",
        )
        devices = client.get_network_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["id"], "wifi0")

    @patch("requests.Session.request")
    def test_get_screen_state(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.text = '{"screenstate": "On"}'
        mock_resp.json.return_value = {"screenstate": "On"}
        mock_request.return_value = mock_resp

        client = JointSpaceClient(
            "192.0.2.10",
            port=1926,
            protocol="https",
            username="testuser",
            password="testpass",
        )
        state = client.get_screen_state()
        self.assertEqual(state.get("screenstate"), "On")

    @patch("requests.Session.request")
    def test_launch_browser(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.text = "{}"
        mock_resp.json.return_value = {}
        mock_request.return_value = mock_resp
        client = JointSpaceClient(
            "192.0.2.10",
            port=1926,
            protocol="https",
            username="testuser",
            password="testpass",
        )
        res = client.launch_browser("http://192.0.2.44:8080")
        self.assertEqual(res, {})

    @patch("requests.Session.request")
    def test_send_sequence(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.text = "{}"
        mock_resp.json.return_value = {}
        mock_request.return_value = mock_resp

        client = JointSpaceClient(
            "192.0.2.10",
            port=1926,
            protocol="https",
            username="testuser",
            password="testpass",
        )
        res = client.send_sequence(["Red", "CursorLeft", "Blue"], delay_sec=0)
        self.assertEqual(len(res), 3)
        self.assertEqual(mock_request.call_count, 3)


if __name__ == "__main__":
    unittest.main()
