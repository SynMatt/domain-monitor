import unittest
from pathlib import Path
class DnsCardLayoutTests(unittest.TestCase):
    def test_compact_layout(self):
        root=Path(__file__).resolve().parents[1]
        index=(root/'templates/index.html').read_text()
        base=(root/'templates/base.html').read_text()
        css=base.split('/* Compact domain cards:',1)[1].split('</style>',1)[0]
        self.assertIn('<strong>DNS host:</strong>',index)
        self.assertIn('title="{{dns_host_label(d.data)}}"',index)
        self.assertIn('text-overflow:ellipsis',css)
        self.assertIn('white-space:nowrap;overflow:hidden',css)
        self.assertNotIn('grid-template-rows',css)
        self.assertNotIn('overflow:auto',css)
        self.assertIn('.card-stale:empty{display:none}',css)
if __name__=='__main__': unittest.main()
