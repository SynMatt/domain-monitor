import re
import unittest
from pathlib import Path

ROOT = Path('/app')


def parse_entries(text):
    """Return [((major, minor, patch), body), ...] for each changelog entry, newest first."""
    found = re.findall(
        r'^## (\d+)\.(\d+)\.(\d+) - [^\n]*\n(.*?)(?=^## \d+\.\d+\.\d+ - |\Z)',
        text, flags=re.M | re.S,
    )
    return [((int(a), int(b), int(c)), body) for a, b, c, body in found]


def policy_problems(new, old, body):
    """Check one release against the one before it. Versions are (major, minor, patch)."""
    if new <= old:
        return ['The newest version must be higher than the one before it.']
    problems = []
    major_up = new[0] > old[0]
    minor_up = new[0] == old[0] and new[1] > old[1]
    if major_up and new[1:] != (0, 0):
        problems.append('A major release must reset the minor and patch numbers to zero.')
    if minor_up and new[2] != 0:
        problems.append('A minor release must reset the patch number to zero.')
    if '### Added' in body and not (major_up or minor_up):
        problems.append('An entry with an Added section needs a minor or major release.')
    return problems


class VersioningPolicyTests(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(policy_problems((1, 0, 0), (0, 15, 2), '### Added\n'), [])
        self.assertEqual(policy_problems((2, 3, 0), (2, 2, 7), '### Added\n'), [])
        self.assertEqual(policy_problems((2, 3, 4), (2, 3, 3), '### Fixed\n'), [])
        self.assertTrue(policy_problems((2, 3, 4), (2, 3, 3), '### Added\n'))
        self.assertTrue(policy_problems((2, 3, 1), (2, 2, 7), '### Fixed\n'))
        self.assertTrue(policy_problems((3, 1, 0), (2, 2, 7), '### Changed\n'))
        self.assertTrue(policy_problems((2, 2, 7), (2, 2, 7), '### Fixed\n'))
        self.assertTrue(policy_problems((2, 2, 6), (2, 2, 7), '### Fixed\n'))

    def test_changelog_parser(self):
        sample = '# Log\n\n## 2.0.0 - 2030-01-01\n\n### Added\n- x\n\n## 1.4.2 - 2029-12-01\n\n### Fixed\n- y\n'
        entries = parse_entries(sample)
        self.assertEqual([v for v, _ in entries], [(2, 0, 0), (1, 4, 2)])
        self.assertIn('### Added', entries[0][1])
        self.assertNotIn('### Added', entries[1][1])

    def test_newest_changelog_entry_follows_the_policy(self):
        entries = parse_entries((ROOT / 'CHANGELOG.md').read_text())
        self.assertGreaterEqual(len(entries), 2)
        (new, body), (old, _) = entries[0], entries[1]
        self.assertEqual(policy_problems(new, old, body), [])

    def test_readme_explains_the_rules(self):
        readme = (ROOT / 'README.md').read_text()
        self.assertIn('Versioning', readme)
        self.assertIn('MAJOR.MINOR.PATCH', readme)
        for word in ('**Major**', '**Minor**', '**Patch**'):
            self.assertIn(word, readme)


if __name__ == '__main__':
    unittest.main(verbosity=2)
