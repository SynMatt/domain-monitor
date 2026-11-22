import json,time,unittest
from test_app import Base
import app as m

class Release122Tests(Base):
    def page_with(self,spf,dkim,dmarc):
        self.auth(); self.add()
        with m.db() as c:
            ident=c.execute("SELECT id FROM domains WHERE domain='example.com'").fetchone()['id']
            data={'spf':spf,'dkim':dkim,'dmarc':dmarc,'status':m.worst([spf,dkim,dmarc]),'trigger':'fixture'}
            encoded=json.dumps(data)
            c.execute('UPDATE domains SET result=?,checked=?,manual_pending=0 WHERE id=?',(encoded,time.time(),ident))
        return self.client.get('/').get_data(as_text=True)

    def item(self,status='pass',approved=False):
        item=m.res(status,'Fixture result')
        if approved:
            item.update(technical_status='warn',approved_warnings=[{'warning':'Fixture warning','fragment':'+a'}],
                        manual_approval_message='Manually approved exception: Fixture')
        return item

    def test_star_only_on_spf_and_dmarc_pass_with_active_approval(self):
        html=self.page_with(self.item(approved=True),self.item(approved=True),self.item(approved=True))
        self.assertIn('SPF: Pass<span class="approved-marker"',html)
        self.assertIn('DMARC: Pass<span class="approved-marker"',html)
        self.assertNotIn('DKIM: Pass<span class="approved-marker"',html)
        self.assertEqual(html.count('class="approved-marker"'),2)

    def test_clean_pass_has_no_star(self):
        html=self.page_with(self.item(),self.item(),self.item())
        self.assertIn('SPF: Pass</span>',html)
        self.assertIn('DMARC: Pass</span>',html)
        self.assertNotIn('class="approved-marker"',html)

    def test_configured_but_unused_approval_has_no_star(self):
        self.auth(); self.add()
        with m.db() as c:
            ident=c.execute("SELECT id FROM domains WHERE domain='example.com'").fetchone()['id']
            c.execute("UPDATE domains SET approved_spf='+a',approved_dmarc='sp=none;' WHERE id=?",(ident,))
            clean=self.item(); data={'spf':clean,'dkim':clean,'dmarc':clean,'status':'pass'}
            c.execute('UPDATE domains SET result=?,checked=?,manual_pending=0 WHERE id=?',(json.dumps(data),time.time(),ident))
        html=self.client.get('/').get_data(as_text=True)
        self.assertNotIn('class="approved-marker"',html)

    def test_warn_fail_unknown_and_stale_never_show_star(self):
        for status in ('warn','fail','unknown'):
            html=self.page_with(self.item(status,True),self.item(),self.item(status,True))
            self.assertNotIn('class="approved-marker"',html,status)
        self.auth(); self.add()
        with m.db() as c:
            ident=c.execute("SELECT id FROM domains WHERE domain='example.com'").fetchone()['id']
            approved=self.item(approved=True); data={'spf':approved,'dkim':self.item(),'dmarc':approved,'status':'pass'}
            c.execute('UPDATE domains SET result=?,checked=?,manual_pending=0 WHERE id=?',(json.dumps(data),time.time()-27*3600,ident))
        self.assertNotIn('class="approved-marker"',self.client.get('/').get_data(as_text=True))

    def test_two_line_legend_is_clear_and_accessible(self):
        self.auth(); html=self.client.get('/').get_data(as_text=True)
        self.assertIn('class="status-legend muted"',html)
        for text in ('🟢','Pass','🟡','Warning','🔴','Fail','⚪','Unknown / error','Pass*','Manually approved exception','Stale','Result is not current'):
            self.assertIn(text,html)
        self.assertNotIn('Green: passes checks',html)

    def test_marker_has_tooltip_and_screen_reader_text(self):
        html=self.page_with(self.item(approved=True),self.item(),self.item())
        self.assertIn('title="Pass includes a manually approved exception"',html)
        self.assertIn('aria-label=" with manually approved exception"',html)

if __name__=='__main__': unittest.main(verbosity=2)
