"""Pure-logic tests. Run: python3 -m unittest discover tests  (needs GTK4 + libadwaita bindings)."""
import os, sys, unittest
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.argv = [sys.argv[0]]
import claude_usage as m


class Logic(unittest.TestCase):
    def test_fmt_delta(self):
        self.assertEqual(m.fmt_delta(timedelta(seconds=75)), "1m 15s")
        self.assertEqual(m.fmt_delta(timedelta(hours=2, minutes=13)), "2h 13m")
        self.assertEqual(m.fmt_delta(timedelta(days=3, hours=5, minutes=2)), "3d 5h 2m")
        self.assertEqual(m.fmt_delta(timedelta(seconds=-5)), "0m 00s")

    def test_level(self):
        self.assertEqual([m.level_of(x) for x in (0, 69.9, 70, 89.9, 90, 100)],
                         ["ok", "ok", "warn", "warn", "crit", "crit"])

    def test_parse_ts(self):
        self.assertEqual(m.parse_ts("2026-11-13T18:10:00Z").hour, 18)
        self.assertEqual(m.parse_ts("2026-11-13T18:10:00+00:00").minute, 10)

    def test_icon_size(self):
        for pct in (None, 0, 5, 66, 100):
            self.assertEqual(len(m.render_icon(pct, "ok")), 64 * 64 * 4)


if __name__ == "__main__":
    unittest.main()
