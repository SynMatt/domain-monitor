import unittest
from pathlib import Path
from test_app import Base as Tests

class DashboardPositionExactTests(Tests):
 def test_exact_scroll_and_refresh_hook(self):
  self.auth(); response=self.client.get('/')
  self.assertEqual(response.status_code,200)
  self.assertIn(b'id="dashboard-refresh"',response.data)
  self.assertIn(b'/static/dashboard-position.js',response.data)
  script=Path('/app/static/dashboard-position.js').read_text()
  self.assertIn('window.scrollY',script)
  self.assertIn("document.getElementById('dashboard-refresh')",script)
  self.assertIn("savePosition('refresh')",script)
  self.assertIn("behavior: 'auto'",script)
  self.assertNotIn('scrollIntoView',script)
  self.assertIn('120000',script)
 def test_security_policy_stays_same_origin(self):
  self.auth(); response=self.client.get('/')
  csp=response.headers.get('Content-Security-Policy','')
  self.assertIn("script-src 'self'",csp)
  self.assertNotIn("'unsafe-inline'",csp.split('script-src',1)[1].split(';',1)[0])

if __name__=='__main__': unittest.main(verbosity=2)
