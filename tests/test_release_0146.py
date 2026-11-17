import re,unittest
from test_app import Base
from test_release_0142 import payload
from unittest.mock import patch
import app as m
class Release0146Tests(Base):
    def row(self,label='Example client'):
        self.auth(); self.add()
        with m.db() as c:
            c.execute("UPDATE domains SET label=? WHERE domain='example.com'",(label,))
            return dict(c.execute("SELECT * FROM domains WHERE domain='example.com'").fetchone())
    def check(self,row,result):
        with patch.object(m,'isolated_domain',return_value=result):
            m.run_domain_check(row,None,False)
    def page(self,row):
        page=self.client.get(f"/domain/{row['id']}")
        self.assertEqual(page.status_code,200)
        return page.get_data(as_text=True)
    def test_layout_sections(self):
        row=self.row(); self.check(row,payload())
        html=self.page(row)
        for text in ('Current status','History','Current domain expiry','Overall','Last checked','Check now','Edit settings',
                     f'name="next" value="/domain/{row["id"]}"','class="dm-entry"','Oldest entry shown'):
            self.assertIn(text,html)
        self.assertEqual(html.count('class="dm-check '),6)   # current status + one history entry
    def test_change_summary_between_entries(self):
        row=self.row(); self.check(row,payload())
        changed=payload(spf='v=spf1 include:spf.example.net -all')
        changed['dkim']['status']='warn'
        self.check(row,changed)
        html=self.page(row)
        self.assertIn('Changed: SPF record changed · DKIM pass → warn',html)
    def test_grouped_entry_shown_in_summary(self):
        row=self.row(); self.check(row,payload()); self.check(row,payload(noise=3))
        self.assertIn('Same result for 2 checks',self.page(row))
    def test_no_stray_separator_without_label(self):
        row=self.row(label='')
        html=self.page(row)
        self.assertRegex(html,r'<p class="muted">Selectors: ')
        self.assertIn('No completed checks yet',html)
    def test_history_changes_helper(self):
        old=payload(); new=payload()
        self.assertEqual(m.history_changes(new,old),[])
        new['dns_host']['nameservers']=['ns9.example.org']
        self.assertEqual(m.history_changes(new,old),['DNS host changed'])
        self.assertEqual(m.history_changes(None,old),[])
if __name__=='__main__': unittest.main(verbosity=2)
