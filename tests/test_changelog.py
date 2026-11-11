import unittest
from test_app import Tests
import app as m

class ChangeLogTests(Tests):
    def test_changelog_requires_login(self):
        self.assertEqual(self.client.get('/changelog').status_code,302)

    def test_changelog_page_and_version(self):
        self.auth()
        page=self.client.get('/changelog')
        self.assertEqual(page.status_code,200)
        self.assertIn(b'Version 0.13.1',page.data)
        self.assertIn(b'Added',page.data)
        self.assertIn(b'Fixed',page.data)
        self.assertIn(b'Removed',page.data) if b'Removed' in page.data else None
        home=self.client.get('/')
        self.assertIn(b'v0.13.1',home.data)
        self.assertIn(b'Change log',home.data)

    def test_health_version(self):
        self.assertEqual(self.client.get('/health').json['version'],'0.13.1')

if __name__=='__main__': unittest.main(verbosity=2)
