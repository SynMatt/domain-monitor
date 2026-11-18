import unittest
from test_app import Base as Tests
import app as m


class BulkTests(Tests):
    """Adding several domains at once goes through the Add domain form."""

    def add_text(self, text, label='', selectors='', policy='quarantine'):
        return self.client.post('/new', data=dict(csrf='token', domain=text, label=label,
                                                  selectors=selectors, policy=policy), follow_redirects=True)

    def test_bulk_add_and_skip(self):
        self.auth()
        r = self.add_text('EXAMPLE.com,Label A\nexample.net\nexample.com', selectors='selector1,selector2')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Added 2 domains', r.data)
        self.assertIn(b'1 duplicate line', r.data)
        with m.db() as c:
            rows = c.execute('SELECT * FROM domains ORDER BY domain').fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['manual_pending'], 1)
        self.assertGreater(rows[0]['due'], 0)
        r = self.add_text('example.com,Changed', policy='none')
        self.assertIn(b'Domain already exists', r.data)
        with m.db() as c:
            row = c.execute("SELECT * FROM domains WHERE domain='example.com'").fetchone()
        self.assertEqual(row['label'], 'Label A')
        self.assertEqual(row['policy'], 'quarantine')

    def test_bulk_invalid_atomic(self):
        self.auth()
        r = self.add_text('example.com\nnot a domain\nexample.net')
        self.assertIn(b'Nothing was added', r.data)
        self.assertIn(b'Line 2', r.data)
        with m.db() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM domains').fetchone()[0], 0)

    def test_bulk_auth_csrf(self):
        self.assertEqual(self.client.get('/new').status_code, 302)
        self.auth()
        self.assertEqual(self.client.post('/new', data={'domain': 'example.com'}).status_code, 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)
