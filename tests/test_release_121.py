import unittest
from urllib.parse import urlparse
from test_app import Base
import app as m


class Release121Tests(Base):
    def domain_id(self):
        self.auth(); self.add()
        with m.db() as c:
            return c.execute("SELECT id FROM domains WHERE domain='example.com'").fetchone()['id']

    def save(self, ident, **changes):
        data = dict(domain='example.com', label='Example client', selectors='selector1', policy='quarantine')
        data.update(changes)
        return self.post(f'/domain/{ident}/edit', **data)

    def test_save_returns_to_the_domain_page(self):
        ident = self.domain_id()
        r = self.save(ident)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(urlparse(r.headers['Location']).path, f'/domain/{ident}')

    def test_confirmation_shows_on_the_domain_page(self):
        ident = self.domain_id()
        self.save(ident)
        page = self.client.get(f'/domain/{ident}').get_data(as_text=True)
        self.assertIn('Saved. Check queued.', page)

    def test_save_still_queues_a_check_and_keeps_the_schedule(self):
        ident = self.domain_id()
        with m.db() as c:
            c.execute('UPDATE domains SET manual_pending=0 WHERE id=?', (ident,))
            due = c.execute('SELECT due FROM domains WHERE id=?', (ident,)).fetchone()['due']
        self.save(ident)
        with m.db() as c:
            row = c.execute('SELECT due,manual_pending FROM domains WHERE id=?', (ident,)).fetchone()
        self.assertEqual(row['manual_pending'], 1)
        self.assertEqual(row['due'], due)

    def test_invalid_save_stays_on_the_edit_form(self):
        ident = self.domain_id()
        r = self.save(ident, domain='not a domain')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Enter a domain only', r.get_data(as_text=True))

    def test_adding_a_domain_still_returns_to_the_dashboard(self):
        self.auth()
        r = self.post('/new', domain='example.net', label='', selectors='', policy='quarantine')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(urlparse(r.headers['Location']).path, '/')


if __name__ == '__main__':
    unittest.main(verbosity=2)
