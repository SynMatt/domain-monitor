from pathlib import Path
from test_app import Base
import app as m

class DomainLiveTests(Base):
    def test_detail_status_asset_and_baseline(self):
        self.auth(); self.add()
        with m.db() as c: ident=c.execute('SELECT id FROM domains').fetchone()[0]
        page=self.client.get(f'/domain/{ident}')
        self.assertEqual(page.status_code,200)
        self.assertIn(b'/static/domain-status.js',page.data)
        self.assertIn(f'data-domain-id="{ident}"'.encode(),page.data)
        self.assertIn(b'data-checked=',page.data)
        response=self.client.get(f'/domains/status?ids={ident}')
        self.assertIn('checked',response.get_json()['domains'][str(ident)])
    def test_polling_guards_and_restoration(self):
        script=Path('/app/static/domain-status.js').read_text()
        for token in ('/domains/status?ids=', 'document.hidden', 'AbortController', 'dirty',
                      'window.scrollY', 'window.scrollTo', 'sessionStorage', 'response.redirected',
                      'rotation.contains(document.activeElement)', 'saved.open'):
            self.assertIn(token,script)
