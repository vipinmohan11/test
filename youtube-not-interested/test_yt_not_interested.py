"""Offline tests: no phone needed. Run with `python -m unittest`."""

import unittest

from yt_not_interested import Config, decide, find_cards

FEED_XML = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy rotation="0">
  <node class="androidx.recyclerview.widget.RecyclerView" bounds="[0,200][1440,2900]" content-desc="" text="" clickable="false">
    <node class="android.view.ViewGroup" bounds="[0,200][1440,1300]" content-desc="" text="" clickable="false">
      <node class="android.view.ViewGroup" bounds="[0,200][1440,1300]" clickable="true" text=""
            content-desc="Epic PRANK on my dad - 12 minutes - Go to channel - Funny Guys - 2.1M views - 3 days ago - play video"/>
      <node class="android.widget.ImageView" bounds="[1330,1100][1430,1200]" content-desc="Action menu" text="" clickable="true"/>
    </node>
    <node class="android.view.ViewGroup" bounds="[0,1300][1440,2400]" content-desc="" text="" clickable="false">
      <node class="android.view.ViewGroup" bounds="[0,1300][1440,2400]" clickable="true" text=""
            content-desc="Rust ownership explained - 20 minutes - Go to channel - Code Talks - 50K views - 1 week ago - play video"/>
      <node class="android.widget.ImageView" bounds="[1330,2200][1430,2300]" content-desc="Action menu" text="" clickable="true"/>
    </node>
  </node>
  <node class="android.widget.ImageView" bounds="[1330,2700][1430,2800]" content-desc="More actions" text="" clickable="true"/>
  <node class="android.view.View" bounds="[0,2450][1440,2850]" clickable="true" text=""
        content-desc="Crazy reaction to finale, 3.4M views - play Short"/>
</hierarchy>"""


class FindCardsTest(unittest.TestCase):
    def test_pairs_each_menu_with_its_video(self):
        cards = find_cards(FEED_XML, Config())
        self.assertEqual(len(cards), 3)
        self.assertIn("PRANK", cards[0].description)
        self.assertIn("Rust", cards[1].description)
        self.assertEqual(cards[1].menu.center, (1380, 2250))
        # Menu with no video in its ancestors falls back to geometry.
        self.assertIn("play Short", cards[2].description)


class DecideTest(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(block_keywords=["prank", "reaction"], allow_channels=["Code Talks"])

    def test_keyword_block(self):
        self.assertEqual(decide("Epic PRANK - Go to channel - X - play video", self.cfg), (True, "keyword: prank"))

    def test_allow_beats_block(self):
        self.cfg.block_keywords.append("rust")
        self.assertFalse(decide("Rust - Go to channel - Code Talks - play video", self.cfg)[0])

    def test_shorts_skipped(self):
        self.assertEqual(decide("Crazy reaction - play Short", self.cfg), (False, "short"))

    def test_mark_everything(self):
        self.cfg.mark_everything = True
        self.assertTrue(decide("Some random video - play video", self.cfg)[0])

    def test_no_match(self):
        self.assertFalse(decide("Cooking pasta - play video", self.cfg)[0])


class ConfigTest(unittest.TestCase):
    def test_shipped_config_loads(self):
        from pathlib import Path
        cfg = Config.load(Path(__file__).parent / "config.toml")
        self.assertIn("Not interested", cfg.not_interested_labels)


if __name__ == "__main__":
    unittest.main()
