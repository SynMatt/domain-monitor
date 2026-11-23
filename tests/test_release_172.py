import unittest
import app as m

class ExpiryChangeExplanationTests(unittest.TestCase):
    def payload(self,expires=None,manual=False,error=None):
        return {'domain_expiry':{'status':'ok' if expires else 'unknown','expires_at':expires,'manual':manual,'error':error}}
    def one(self,new,old):
        items=m.history_change_details(new,old)
        self.assertEqual(len(items),1)
        return items[0]
    def test_lookup_unavailable_does_not_claim_date_removed(self):
        item=self.one(self.payload(None,error='RDAP timeout'),self.payload(1834106400))
        self.assertEqual(item['label'],'Expiry lookup unavailable')
        self.assertIn('does not mean the registration date was removed',item['note'])
        self.assertIn('RDAP timeout',item['note'])
    def test_lookup_available_again(self):
        item=self.one(self.payload(1834106400),self.payload(None))
        self.assertEqual(item['label'],'Expiry date available again')
        self.assertIn('usable expiry date again',item['note'])
    def test_published_and_manual_date_changes_are_distinct(self):
        item=self.one(self.payload(1834106400),self.payload(1802570400))
        self.assertEqual(item['label'],'Published expiry date changed')
        item=self.one(self.payload(1834106400,True),self.payload(1802570400,True))
        self.assertEqual(item['label'],'Manual expiry date changed')
