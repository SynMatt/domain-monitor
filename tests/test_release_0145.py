import re,unittest
from pathlib import Path
from test_app import Base
class Release0145Tests(Base):
    def test_readme_examples_never_hardcode_a_release(self):
        readme=Path('/app/README.md').read_text()
        start=readme.index('<!-- BEGIN UPDATE COMMANDS -->'); end=readme.index('<!-- END UPDATE COMMANDS -->')
        outside=readme[:start]+readme[end:]
        self.assertEqual(re.findall(r'--version \d+\.\d+\.\d+',outside),[],
            'Use X.Y.Z in hand-written README examples; only the generated block shows the real version')
        self.assertIn('--version X.Y.Z',outside)
if __name__=='__main__': unittest.main(verbosity=2)
