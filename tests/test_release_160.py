from pathlib import Path
import unittest

class LiveFilteredNavigationTests(unittest.TestCase):
    def test_uses_server_rendered_dashboard_and_updates_saved_ids(self):
        s=Path('/app/static/domain-navigation.js').read_text()
        for token in ('fetch(dashboardUrl.pathname + dashboardUrl.search', 'DOMParser',
                      ".grid article.card h2 a[href^=\"/domain/\"]", 'saved.ids = ids',
                      'sessionStorage.setItem(viewKey', "cache: 'no-store'", "credentials: 'same-origin'"):
            self.assertIn(token,s)
    def test_resolved_domain_message_and_nearest_neighbours(self):
        s=Path('/app/static/domain-navigation.js').read_text()
        for token in ('No longer matches filter', 'No domains match this filter',
                      'oldIds.slice(0, oldIndex).reverse()', 'oldIds.slice(oldIndex + 1)',
                      "ids.length + ' remaining'"):
            self.assertIn(token,s)
