import unittest
from pathlib import Path

class Release135Tests(unittest.TestCase):
    def test_css_layout_and_no_stray_brace(self):
        s=Path('/app/templates/detail.html').read_text()
        self.assertNotIn('.dm-rotation-date input{width:100%}',s)
        css=s.split('<style>',1)[1].split('</style>',1)[0]
        import re
        css=re.sub(r'/\*.*?\*/', '', css, flags=re.S)
        depth=0
        for char in css:
            if char=='{': depth+=1
            elif char=='}': depth-=1
            self.assertGreaterEqual(depth,0,'Unmatched closing CSS brace')
        self.assertEqual(depth,0,'Unclosed CSS block')
        self.assertIn('grid-template-columns:repeat(5,minmax(0,1fr))',s)
        for bp in (900,600,440): self.assertIn(f'@media(max-width:{bp}px)',s)
        self.assertIn('name="rotation_action" value="clear"',s)
