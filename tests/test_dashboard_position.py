import unittest
from pathlib import Path
from test_app import Tests
import app as m
class DashboardPositionTests(Tests):
 def test_assets_csp_and_sticky_header(self):
  self.auth(); response=self.client.get('/')
  self.assertEqual(response.status_code,200)
  self.assertIn(b'/static/dashboard-position.js',response.data)
  csp=response.headers.get('Content-Security-Policy','')
  self.assertIn("script-src 'self'",csp)
  self.assertNotIn("'unsafe-inline'",csp.split('script-src',1)[1].split(';',1)[0])
  script=Path('/app/static/dashboard-position.js').read_text()
  self.assertIn('sessionStorage',script)
  self.assertIn('window.scrollY',script)
  self.assertIn('window.scrollTo',script)
  self.assertNotIn('scrollIntoView',script)
  self.assertIn('header{position:sticky;top:0;',Path('/app/templates/base.html').read_text())
 def test_pending_card_feedback(self):
  self.auth(); self.add()
  with m.db() as c:
   ident=c.execute('SELECT id FROM domains').fetchone()['id']; c.execute('UPDATE domains SET manual_pending=0 WHERE id=?',(ident,))
  page=self.client.get('/?q=example&sort=domain')
  self.assertIn(b'class="domain-check-form"',page.data); self.assertIn(b'Check now',page.data)
  self.post(f'/domain/{ident}/check',next='/?q=example&sort=domain')
  page=self.client.get('/?q=example&sort=domain')
  self.assertIn(b'Check queued',page.data); self.assertIn(b'disabled',page.data)
if __name__=='__main__': unittest.main(verbosity=2)
