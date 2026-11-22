import unittest
from pathlib import Path

class Release136Tests(unittest.TestCase):
    def test_rotation_button_group_and_order(self):
        s=Path('/app/templates/detail.html').read_text()
        group=s.split('<div class="dm-rotation-buttons">',1)[1].split('</div>',1)[0]
        self.assertLess(group.index('value="today"'),group.index('value="save"'))
        self.assertLess(group.index('value="save"'),group.index('value="clear"'))
        self.assertIn('{% if rotation %}',group)
        self.assertIn('.dm-rotation-buttons{display:flex;flex-wrap:nowrap;',s)
        self.assertIn('flex-direction:column;align-items:flex-start',s)
