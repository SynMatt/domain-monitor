import unittest
from pathlib import Path
class Release132Tests(unittest.TestCase):
    def test_rotation_is_compact_summary_tile(self):
        d=Path('/app/templates/detail.html').read_text()
        for x in ('dm-rotation-tile','dm-rotation-mini','>Save<','>Today<','>Clear<'): self.assertIn(x,d)
        self.assertNotIn('<section class="panel dm-rotation"',d)
        self.assertNotIn('DKIM remains Warn while rotation is tracked',d)
if __name__=='__main__': unittest.main()
