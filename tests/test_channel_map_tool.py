import os
import unittest
from tools.channel_map_tool import ChannelMap, crc16_modbus

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTORY_MAP = os.path.join(REPO_ROOT, "samples", "channel-maps", "ChannelMap_100")


class TestChannelMapTool(unittest.TestCase):
    def test_crc16_modbus_calculation(self):
        # Known test vector: "123456789" -> 0x4B37
        vector = b"123456789"
        self.assertEqual(crc16_modbus(vector), 0x4B37)

    def test_factory_channel_map_verification(self):
        cm = ChannelMap(FACTORY_MAP)
        ok, reports = cm.verify()
        self.assertTrue(ok)
        self.assertEqual(cm.model, "55PUS8000/12")
        self.assertEqual(len(cm.entries), 4)

    def test_round_trip_recalculation(self):
        cm = ChannelMap(FACTORY_MAP)
        cm.parse()
        temp_bin = os.path.join("/tmp", "test_chanLst.bin")
        cm.recalculate(temp_bin)

        with open(cm.chan_lst_bin, "rb") as f1, open(temp_bin, "rb") as f2:
            self.assertEqual(f1.read(), f2.read(), "Bit-identical round-trip reconstruction failed!")

        if os.path.exists(temp_bin):
            os.remove(temp_bin)


if __name__ == "__main__":
    unittest.main()
