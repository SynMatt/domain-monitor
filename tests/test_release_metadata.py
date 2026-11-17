import re,unittest
from pathlib import Path
from test_app import Base
import app as m
class ReleaseMetadataTests(Base):
    def test_health_reports_app_version(self):
        self.assertRegex(m.APP_VERSION,r'^\d+\.\d+\.\d+$')
        self.assertEqual(self.client.get('/health').json['version'],m.APP_VERSION)
    def test_changelog_starts_with_current_release(self):
        first=re.search(r'^## (\d+\.\d+\.\d+) - \d{4}-\d{2}-\d{2}$',Path('/app/CHANGELOG.md').read_text(),re.M)
        self.assertEqual(first.group(1),m.APP_VERSION)
    def test_header_uses_app_version(self):
        self.auth(); self.assertIn(f'v{m.APP_VERSION} ·'.encode(),self.client.get('/').data)
        self.assertNotRegex(Path('/app/templates/base.html').read_text(),r'v\d+\.\d+\.\d+')
    def test_tests_do_not_hardcode_current_version(self):
        for path in Path('/app/tests').glob('test_*.py'):
            self.assertNotIn(repr(m.APP_VERSION),path.read_text(),path.name)
if __name__=='__main__': unittest.main(verbosity=2)
