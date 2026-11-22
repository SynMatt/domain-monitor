from pathlib import Path
from test_app import Base
import app as m

class FilteredDomainNavigationTests(Base):
    def test_detail_navigation_markup_and_assets(self):
        self.auth(); self.add()
        with m.db() as c: ident=c.execute('SELECT id FROM domains').fetchone()[0]
        page=self.client.get(f'/domain/{ident}')
        self.assertEqual(page.status_code,200)
        for token in (b'/static/domain-navigation.js', b'id="previous-domain"', b'id="next-domain"', b'data-domain-id='):
            self.assertIn(token,page.data)
    def test_saved_sequence_validation_and_order(self):
        return_script=Path('/app/static/dashboard-return.js').read_text()
        navigation=Path('/app/static/domain-navigation.js').read_text()
        for token in ('orderedDomainIds', 'ids: orderedDomainIds()', 'slice(0, 1000)'):
            self.assertIn(token,return_script)
        for token in ("url.origin !== window.location.origin", "url.pathname !== '/'", "ids.indexOf", "current - 1", "current + 1", "aria-disabled"):
            self.assertIn(token,navigation)
