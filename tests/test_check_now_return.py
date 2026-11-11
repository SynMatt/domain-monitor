import unittest
from test_app import Tests
import app as m

class CheckNowReturnTests(Tests):
    def ident(self):
        self.add()
        with m.db() as c:
            return c.execute("SELECT id FROM domains WHERE domain='example.com'").fetchone()['id']

    def test_dashboard_check_returns_to_filtered_view(self):
        self.auth(); ident=self.ident()
        target='/?q=example&kind=spf&status=fail&sort=domain'
        response=self.post(f'/domain/{ident}/check',next=target)
        self.assertEqual(response.status_code,302)
        self.assertEqual(response.headers['Location'],target)

    def test_detail_check_returns_to_detail(self):
        self.auth(); ident=self.ident()
        response=self.post(f'/domain/{ident}/check',next=f'/domain/{ident}')
        self.assertEqual(response.headers['Location'],f'/domain/{ident}')

    def test_external_redirect_is_rejected(self):
        self.auth(); ident=self.ident()
        response=self.post(f'/domain/{ident}/check',next='https://evil.invalid/')
        self.assertEqual(response.headers['Location'],f'/domain/{ident}')
        response=self.post(f'/domain/{ident}/check',next='//evil.invalid/')
        self.assertEqual(response.headers['Location'],f'/domain/{ident}')

if __name__=='__main__': unittest.main(verbosity=2)
