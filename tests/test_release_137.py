from pathlib import Path
from test_app import Base

class DashboardReturnTests(Base):
    def test_global_asset_and_navigation(self):
        self.auth(); self.add()
        with __import__('app').db() as c:
            ident=c.execute('SELECT id FROM domains').fetchone()[0]
        for path in ('/?kind=dkim&status=warn&q=example&sort=severity',f'/domain/{ident}'):
            response=self.client.get(path)
            self.assertEqual(response.status_code,200)
            self.assertIn(b'/static/dashboard-return.js',response.data)
            self.assertEqual(response.data.count(b'data-dashboard-return'),2)
        page=self.client.get('/').get_data(as_text=True)
        self.assertLess(page.index('/static/dashboard-return.js'),page.index('/static/dashboard-position.js'))
    def test_return_validation_and_compatibility(self):
        script=Path('/app/static/dashboard-return.js').read_text()
        for text in ("url.origin !== window.location.origin", "url.pathname !== '/'", "window.scrollY", "'pagehide'", "'/logout'", "savedAt: Date.now()"):
            self.assertIn(text,script)
        old=Path('/app/static/dashboard-position.js').read_text()
        self.assertIn('120000',old)
        self.assertIn('Math.min(Math.max(0, saved.y), maximum)',old)
