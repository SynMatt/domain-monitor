import time
import unittest
from datetime import date, timedelta
from urllib.parse import urlparse

from test_app import Base
import app as m


class Release110Tests(Base):
    def submit(self, text, label='', selectors='', policy='quarantine', **extra):
        data = dict(csrf='token', domain=text, label=label, selectors=selectors, policy=policy)
        data.update(extra)
        return self.client.post('/new', data=data, follow_redirects=True)

    def rows(self):
        with m.db() as c:
            return [dict(r) for r in c.execute('SELECT * FROM domains ORDER BY domain')]

    def insert(self, domain, label='Old', selectors='old1', policy='reject', due=123.0, revision=5):
        with m.db() as c:
            c.execute('INSERT INTO domains(domain,label,selectors,policy,revision,due) VALUES(?,?,?,?,?,?)',
                      (domain, label, selectors, policy, revision, due))

    # ---- one workflow for one or many domains
    def test_single_domain_redirects_to_the_dashboard(self):
        self.auth()
        r = self.post('/new', domain='example.com', label='', selectors='', policy='quarantine')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(urlparse(r.headers['Location']).path, '/')
        self.assertIn(b'Saved. Check queued.', self.client.get('/').data)

    def test_several_domains_one_per_line(self):
        self.auth()
        r = self.submit('\n  Example.COM  \n\n example.net\n')
        self.assertIn(b'Added 2 domains', r.data)
        self.assertEqual([x['domain'] for x in self.rows()], ['example.com', 'example.net'])

    def test_shared_label_and_per_line_label(self):
        self.auth()
        self.submit('example.com\nexample.net,Own label', label='Shared label')
        labels = {x['domain']: x['label'] for x in self.rows()}
        self.assertEqual(labels, {'example.com': 'Shared label', 'example.net': 'Own label'})

    def test_quoted_label_may_contain_a_comma(self):
        entries, repeated, errors = m.parse_domain_entries('example.com,"Label, with comma"\nexample.net')
        self.assertEqual(entries, [('example.com', 'Label, with comma'), ('example.net', '')])
        self.assertEqual((repeated, errors), (0, []))

    # ---- DKIM defaults
    def test_blank_selectors_default_and_are_visible_when_editing(self):
        self.auth()
        self.submit('example.com')
        row = self.rows()[0]
        self.assertEqual(row['selectors'], 'selector1,selector2')
        page = self.client.get('/domain/%d/edit' % row['id']).data
        self.assertIn(b'value="selector1,selector2"', page)

    def test_explicit_selectors_replace_the_defaults(self):
        self.auth()
        self.submit('example.com', selectors='Mail, Other')
        self.assertEqual(self.rows()[0]['selectors'], 'mail,other')

    def test_editing_keeps_blank_selectors_as_unknown(self):
        self.auth()
        self.submit('example.com')
        ident = self.rows()[0]['id']
        self.post('/domain/%d/edit' % ident, domain='example.com', label='', selectors='', policy='quarantine')
        self.assertEqual(self.rows()[0]['selectors'], '')

    # ---- existing and repeated domains
    def test_existing_and_repeated_lines_are_skipped_without_changes(self):
        self.auth()
        self.insert('example.com')
        before = self.rows()[0]
        r = self.submit('example.com\nexample.net\nexample.net', label='Other label', policy='none')
        self.assertIn(b'Added 1 domain.', r.data)
        self.assertIn(b'1 existing domain', r.data)
        self.assertIn(b'1 duplicate line', r.data)
        self.assertIn(b'Existing domains were not changed', r.data)
        rows = {x['domain']: x for x in self.rows()}
        self.assertEqual(rows['example.com'], before)
        self.assertEqual(rows['example.net']['policy'], 'none')

    def test_all_existing_adds_nothing(self):
        self.auth()
        self.insert('example.com')
        self.insert('example.net')
        r = self.submit('example.com\nexample.net')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'No domains added. All 2 domains already exist.', r.data)
        self.assertEqual(len(self.rows()), 2)

    # ---- validation
    def test_single_invalid_line_has_a_plain_message(self):
        self.auth()
        r = self.submit('https://bad.example')
        self.assertIn(b'Enter a domain only', r.data)
        self.assertNotIn(b'Line 1', r.data)
        self.assertEqual(self.rows(), [])

    def test_invalid_lines_add_nothing_and_are_numbered(self):
        self.auth()
        r = self.submit('example.com\nhttps://bad.example\nexample.net\n10.0.0.1')
        self.assertIn(b'Nothing was added', r.data)
        self.assertIn(b'Line 2', r.data)
        self.assertIn(b'Line 4', r.data)
        self.assertEqual(self.rows(), [])

    def test_bad_policy_and_selectors_add_nothing(self):
        self.auth()
        self.assertIn(b'Invalid policy', self.submit('example.com\nexample.net', policy='bogus').data)
        self.assertIn(b'Enter selector names only', self.submit('example.com', selectors='not a selector!').data)
        self.assertEqual(self.rows(), [])

    def test_blank_input(self):
        self.auth()
        self.assertIn(b'Enter at least one domain', self.submit('  \n \n').data)

    # ---- limits
    def test_two_hundred_domains_are_accepted_and_two_hundred_and_one_are_not(self):
        self.auth()
        names = ['d%d.example.com' % i for i in range(201)]
        r = self.submit('\n'.join(names))
        self.assertIn(b'at most 200', r.data)
        self.assertEqual(self.rows(), [])
        r = self.submit('\n'.join(names[:200]))
        self.assertIn(b'Added 200 domains', r.data)
        self.assertEqual(len(self.rows()), 200)

    def test_text_length_is_limited_on_the_server(self):
        self.auth()
        too_long = 'a' * (m.MAX_DOMAIN_TEXT + 1)
        with self.assertRaises(ValueError) as caught:
            m.parse_domain_entries(too_long)
        self.assertIn('Too much text', str(caught.exception))
        # Flask may refuse a body this large before the form code runs (413). Either way nothing is added.
        r = self.submit(too_long)
        self.assertTrue(r.status_code == 413 or b'Too much text' in r.data, r.status_code)
        self.assertEqual(self.rows(), [])

    def test_total_domain_limit(self):
        self.auth()
        with m.db() as c:
            c.executemany('INSERT INTO domains(domain,label,selectors,policy) VALUES(?,?,?,?)',
                          [('seed%d.example.com' % i, '', '', 'quarantine') for i in range(450)])
        r = self.submit('\n'.join('n%d.example.com' % i for i in range(51)))
        self.assertIn(b'Initial version limit', r.data)
        self.assertEqual(len(self.rows()), 450)
        self.submit('\n'.join('n%d.example.com' % i for i in range(50)))
        self.assertEqual(len(self.rows()), 500)

    # ---- manual expiry
    def test_manual_expiry_only_for_a_single_domain(self):
        self.auth()
        when = (date.today() + timedelta(days=400)).isoformat()
        r = self.submit('example.com\nexample.net', manual_expiry=when)
        self.assertIn(b'only be set when adding a single domain', r.data)
        self.assertEqual(self.rows(), [])
        self.submit('example.com', manual_expiry=when)
        row = self.rows()[0]
        self.assertEqual(row['manual_expiry'], when)
        self.assertTrue(row['manual_expiry_source'])

    # ---- scheduling
    def test_new_domains_are_queued_and_share_the_daily_schedule(self):
        self.auth()
        self.insert('existing.example.com')
        self.submit('example.com\nexample.net\nexample.org')
        rows = {x['domain']: x for x in self.rows()}
        new = [rows[d] for d in ('example.com', 'example.net', 'example.org')]
        self.assertTrue(all(x['manual_pending'] == 1 for x in new))
        self.assertEqual(len({x['due'] for x in new}), 1)
        self.assertGreater(new[0]['due'], time.time())
        self.assertEqual(rows['existing.example.com']['due'], 123.0)
        self.assertEqual(rows['existing.example.com']['manual_pending'], 0)

    # ---- the old Bulk add address
    def test_old_bulk_address_redirects_to_add_domain(self):
        self.assertIn('login', self.client.get('/bulk-add').headers['Location'])
        self.auth()
        r = self.client.get('/bulk-add')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(urlparse(r.headers['Location']).path, '/new')
        r = self.post('/bulk-add', domains='example.com')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(urlparse(r.headers['Location']).path, '/new')
        self.assertEqual(self.rows(), [])

    # ---- pages
    def test_navigation_order_and_no_bulk_add(self):
        self.auth()
        for path in ('/', '/new'):
            page = self.client.get(path).get_data(as_text=True)
            header = page.split('<header>', 1)[1].split('</header>', 1)[0]
            order = ['>Dashboard<', '>Add domain<', '>Settings<', '>Change log<', '>Refresh<', '>Check all domains<', '>Log out<']
            positions = [header.find(item) for item in order]
            self.assertNotIn(-1, positions, path)
            self.assertEqual(positions, sorted(positions), path)
            self.assertNotIn('Bulk add', page, path)
            self.assertNotIn('/bulk-add', page, path)
        home = self.client.get('/').get_data(as_text=True)
        self.assertRegex(home, r'href="/"\s+aria-current="page">Dashboard')
        add = self.client.get('/new').get_data(as_text=True)
        self.assertRegex(add, r'href="/new"\s+aria-current="page">Add domain')

    def test_add_page_and_edit_page_use_different_domain_fields(self):
        self.auth()
        add = self.client.get('/new').get_data(as_text=True)
        self.assertIn('<textarea id="domain" name="domain"', add)
        self.assertIn('Domain(s)', add)
        self.assertIn('Add domain(s)', add)
        self.assertIn('Leave blank to check', add)
        self.submit('example.com')
        edit = self.client.get('/domain/%d/edit' % self.rows()[0]['id']).get_data(as_text=True)
        self.assertIn('<input id="domain" name="domain"', edit)
        self.assertNotIn('<textarea id="domain"', edit)
        self.assertIn('Save and queue check', edit)
        self.assertNotIn('Leave blank to check', edit)

    def test_typed_text_and_labels_are_escaped(self):
        self.auth()
        self.submit('example.com', label='<script>alert(1)</script>')
        self.assertNotIn(b'<script>alert(1)</script>', self.client.get('/').data)
        r = self.submit('<script>alert(1)</script>')
        self.assertNotIn(b'<script>alert(1)</script>', r.data)
        self.assertEqual(len(self.rows()), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
