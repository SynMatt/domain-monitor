import unittest
from test_app import Tests

class RefreshViewTests(Tests):
    def test_refresh_uses_current_path_and_query(self):
        self.auth()
        page=self.client.get('/?q=alpha&kind=spf&status=fail&sort=severity')
        self.assertEqual(page.status_code,200)
        self.assertIn(b'href="/?q=alpha&amp;kind=spf&amp;status=fail&amp;sort=severity">Refresh</a>',page.data)

    def test_refresh_without_query_stays_on_dashboard(self):
        self.auth(); page=self.client.get('/')
        self.assertIn(b'href="/">Refresh</a>',page.data)

    def test_refresh_on_detail_stays_on_detail(self):
        self.auth(); self.add(); page=self.client.get('/domain/1')
        self.assertEqual(page.status_code,200)
        self.assertIn(b'href="/domain/1">Refresh</a>',page.data)

if __name__ == '__main__': unittest.main(verbosity=2)
