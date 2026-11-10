import unittest
from test_app import Tests
import app as m
class BulkTests(Tests):
    def test_bulk_add_and_skip(self):
        self.auth()
        r=self.post('/bulk-add',domains='EXAMPLE.com,Client A\nexample.net\nexample.com',selectors='selector1,selector2',policy='quarantine')
        self.assertEqual(r.status_code,200)
        self.assertIn(b'Added 2 domains',r.data)
        with m.db() as c:
            rows=c.execute('SELECT * FROM domains ORDER BY domain').fetchall()
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['manual_pending'],1)
        self.assertGreater(rows[0]['due'],0)
        self.post('/bulk-add',domains='example.com,Changed',selectors='',policy='none')
        with m.db() as c: row=c.execute("SELECT * FROM domains WHERE domain='example.com'").fetchone()
        self.assertEqual(row['label'],'Client A')
        self.assertEqual(row['policy'],'quarantine')
    def test_bulk_invalid_atomic(self):
        self.auth()
        self.post('/bulk-add',domains='example.com\nhttps://bad.example',selectors='',policy='none')
        with m.db() as c: self.assertEqual(c.execute('SELECT COUNT(*) FROM domains').fetchone()[0],0)
    def test_bulk_auth_csrf(self):
        self.assertEqual(self.client.get('/bulk-add').status_code,302)
        self.auth()
        self.assertEqual(self.client.post('/bulk-add',data={'domains':'example.com'}).status_code,400)
if __name__=='__main__': unittest.main(verbosity=2)
