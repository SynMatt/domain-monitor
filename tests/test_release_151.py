from pathlib import Path
import unittest

class DomainNavigationDedupTests(unittest.TestCase):
    def test_dashboard_collects_one_id_per_card(self):
        s=Path('/app/static/dashboard-return.js').read_text()
        self.assertIn("querySelectorAll('.grid article.card')",s)
        self.assertIn("card.querySelector('h2 a[href^=\"/domain/\"]')",s)
        self.assertIn('ids: orderedDomainIds()',s)
        self.assertNotIn("querySelectorAll('.grid a[href^=\"/domain/\"]')",s)
    def test_details_deduplicates_existing_saved_sequences(self):
        s=Path('/app/static/domain-navigation.js').read_text()
        self.assertIn('new Set(saved.ids.filter',s)
        self.assertIn('ids[current + 1]',s)
        self.assertIn('ids[current - 1]',s)
