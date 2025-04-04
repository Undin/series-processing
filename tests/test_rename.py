import unittest
from typing import Optional

import rename_episodes

params: list[tuple[str, Optional[str]]] = [
    ("Shaman.King.S01E24.480p.avi", "Shaman.King.S01E24.480p.avi"),
    ("Money.Heist.S02E01.1080p.WEB-DL.x264-EDHD_Kyle.mkv", "Money.Heist.S02E01.1080p.mkv"),
    ("The.Good.Doctor.S06E12.WEBDL.1080p.RGzsRutracker.mkv", "The.Good.Doctor.S06E12.1080p.mkv"),
    ("The Office 09.01(169) - Новички (New Guys).mkv", None),
]

class RenameEpisodeTest(unittest.TestCase):
    def test_normalization(self):
        for initial_name, expected_result in params:
            with self.subTest(msg=f"{initial_name} -> {expected_result}"):
                actual_result = rename_episodes.normalize(initial_name)
                self.assertEqual(expected_result, actual_result)
