import unittest
from pathlib import Path

ROOT = Path('/app')
SUFFIXES = {'.md', '.py', '.html', '.js', '.sh', '.yml', '.yaml', '.txt', '.example', '.cfg', '.toml', '.json'}
SKIP_PARTS = {'data', 'backups', '.git', '__pycache__'}
# Built from fragments so this file does not contain the names it forbids.
FORBIDDEN = (
    'gol' + 'f.co.nz',
    'remuera' + 'golfclub',
    'aswe' + 'fa',
    'syn' + 'axis',
    'impact' + 'websites',
    'impact ' + 'websites',
)


class NoRealDataTests(unittest.TestCase):
    def test_repository_uses_reserved_example_names(self):
        found = []
        for path in ROOT.rglob('*'):
            if not path.is_file() or path.suffix.lower() not in SUFFIXES:
                continue
            if SKIP_PARTS.intersection(path.parts):
                continue
            text = path.read_text(errors='ignore').lower()
            for index, term in enumerate(FORBIDDEN, 1):
                if term in text:
                    found.append(f'{path.relative_to(ROOT)} contains forbidden term #{index}')
        self.assertEqual(found, [], 'Use reserved example names (example.com, example.net) instead of real data')


if __name__ == '__main__':
    unittest.main(verbosity=2)
