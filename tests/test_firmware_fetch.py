#!/usr/bin/env python3
import unittest

from tools.firmware.fetch import candidate_names, extract_download_links


class TestFirmwareFetch(unittest.TestCase):
    def test_extract_links(self):
        html = (
            '<a href="https://download.p4c.philips.com/files/5/a.zip">a</a>'
            "<a href='https://download.p4c.philips.com/files/5/b.zip'>b</a>"
            'https://download.p4c.philips.com/files/5/a.zip'
        )
        self.assertEqual(
            extract_download_links(html),
            [
                "https://download.p4c.philips.com/files/5/a.zip",
                "https://download.p4c.philips.com/files/5/b.zip",
            ],
        )

    def test_candidate_names(self):
        self.assertEqual(
            candidate_names("55pus8000_12", ["eng"]),
            ["55pus8000_12_pkg_eng.zip", "55pus8000_12_fw_eng.zip"],
        )


if __name__ == "__main__":
    unittest.main()
