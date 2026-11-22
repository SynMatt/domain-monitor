import unittest
from pathlib import Path

class Release133Tests(unittest.TestCase):
    def test_five_column_overview_and_breakpoints(self):
        s = Path('/app/templates/detail.html').read_text()
        self.assertIn('grid-template-columns:repeat(5,minmax(0,1fr))', s)
        for bp in (900, 600, 440):
            self.assertIn(f'@media(max-width:{bp}px)', s)
        self.assertIn('dm-rotation-mini', s)
        self.assertIn('name="rotation_action" value="clear"', s)
