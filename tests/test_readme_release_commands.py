import ast
from pathlib import Path
import unittest
class ReadmeReleaseCommandsTests(unittest.TestCase):
    def test_documented_version_matches_source(self):
        root=Path(__file__).resolve().parents[1]
        tree=ast.parse((root/'app.py').read_text())
        version=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='APP_VERSION' for t in n.targets))
        text=(root/'README.md').read_text()
        self.assertIn(f'Latest documented release: **v{version}**',text)
        self.assertIn(f'sudo ./scripts/update.sh --version {version}',text)
if __name__=='__main__': unittest.main()
