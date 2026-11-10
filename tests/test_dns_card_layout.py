import unittest
from pathlib import Path
class DnsCardLayoutTests(unittest.TestCase):
    def test_label_and_rows(self):
        root=Path(__file__).resolve().parents[1]
        index=(root/'templates/index.html').read_text()
        base=(root/'templates/base.html').read_text()
        self.assertIn('<strong>DNS host:</strong>',index)
        self.assertNotIn('DNS host (detected)',index)
        self.assertIn('dns-host-value',index)
        self.assertIn('grid-template-rows:',base)
        self.assertIn('max-height:3em;overflow:auto',base)
if __name__=='__main__': unittest.main()
