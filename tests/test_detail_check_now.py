import unittest
from test_app import Tests
import app as m

class DetailCheckNowTests(Tests):
    def test_button_is_on_detail_page(self):
        self.auth(); self.add()
        with m.db() as c: ident=c.execute('SELECT id FROM domains WHERE domain=?',('example.com',)).fetchone()['id']
        page=self.client.get(f'/domain/{ident}')
        self.assertEqual(page.status_code,200)
        self.assertIn(f'action="/domain/{ident}/check"'.encode(),page.data)
        self.assertIn(b'>Check now</button>',page.data)

    def test_check_now_queues_once_and_preserves_due(self):
        self.auth(); self.add()
        with m.db() as c:
            ident=c.execute('SELECT id FROM domains WHERE domain=?',('example.com',)).fetchone()['id']
            c.execute('UPDATE domains SET manual_pending=0 WHERE id=?',(ident,))
            before=c.execute('SELECT due,revision FROM domains WHERE id=?',(ident,)).fetchone()
        first=self.post(f'/domain/{ident}/check')
        self.assertEqual(first.status_code,302)
        self.assertTrue(first.headers['Location'].endswith(f'/domain/{ident}'))
        with m.db() as c:
            row=c.execute('SELECT due,revision,manual_pending FROM domains WHERE id=?',(ident,)).fetchone()
            self.assertEqual(row['due'],before['due'])
            self.assertEqual(row['revision'],before['revision']+1)
            self.assertEqual(row['manual_pending'],1)
        self.post(f'/domain/{ident}/check')
        with m.db() as c:
            again=c.execute('SELECT due,revision,manual_pending FROM domains WHERE id=?',(ident,)).fetchone()
            self.assertEqual(tuple(again),tuple(row))

    def test_missing_domain_returns_404(self):
        self.auth(); self.assertEqual(self.post('/domain/999999/check').status_code,404)

if __name__=='__main__': unittest.main(verbosity=2)
