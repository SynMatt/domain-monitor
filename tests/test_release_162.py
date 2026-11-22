from pathlib import Path
import unittest

class ConsistentStatusLegendTests(unittest.TestCase):
    def test_legend_uses_consistent_leading_labels(self):
        s=Path('/app/templates/index.html').read_text()
        expected=(
            '<strong>Pass*</strong> Manually approved exception',
            '<strong>Warn*</strong> DKIM rotation in progress (up to 4 days)',
            '<strong>Stale</strong> Result is not current',
        )
        for text in expected:
            self.assertIn(text,s)
        self.assertLess(s.index(expected[0]),s.index(expected[1]))
        self.assertLess(s.index(expected[1]),s.index(expected[2]))
        self.assertNotIn('<strong>*</strong> Pass includes',s)
