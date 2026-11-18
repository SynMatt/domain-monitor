import unittest
from unittest.mock import patch
import app as m

A_WARNING=('Error when processing {host}: An a mechanism points to {host}, '
           'but that domain/subdomain does not have any A/AAAA records.')

def spf_raw(include=None,warnings=None):
    mechanisms=[]
    if include:
        mechanisms=[{'mechanism':'include','value':include,'parsed':{'mechanisms':[]}}]
    return {'valid':True,'record':'v=spf1 -all','dns_lookups':1,
            'warnings':warnings or [],'parsed':{'all':'fail','mechanisms':mechanisms}}

class Release0150Tests(unittest.TestCase):
    def test_direct_spf_warning_is_not_external(self):
        raw=spf_raw(warnings=[A_WARNING.format(host='direct.example.com')])
        result=m.friendly_spf_warning('direct.example.com',raw['warnings'][0],raw)
        self.assertTrue(result.startswith('Action recommended:'))
        self.assertNotIn('External provider:',result)

    def test_included_spf_warning_is_external(self):
        raw=spf_raw('_spf.provider.example.net',[A_WARNING.format(host='_spf.provider.example.net')])
        result=m.friendly_spf_warning('customer.example.com',raw['warnings'][0],raw)
        self.assertTrue(result.startswith('External provider:'))

    def test_unrelated_spf_warning_is_unchanged(self):
        warning='Fixture warning'
        self.assertEqual(m.friendly_spf_warning('example.com',warning,spf_raw()),warning)

    def test_dmarc_obsolete_tags(self):
        for tag in ('pct','ri','rf'):
            result=m.friendly_dmarc_warning(f'Support for the {tag} tag was removed in RFC 9989')
            self.assertIn('Recommendation:',result); self.assertIn(tag,result)

    def test_dmarc_sp_none_and_reporting_messages(self):
        self.assertTrue(m.friendly_dmarc_warning('An sp tag value of none makes DMARC unenforced on email sent as a subdomain of example.com.').startswith('Action recommended:'))
        self.assertIn('aggregate visibility',m.friendly_dmarc_warning('rua tag (destination for aggregate reports) not found.'))
        self.assertIn('More than two rua',m.friendly_dmarc_warning('Some DMARC reporters might not send to more than two rua URIs.'))

    @patch('checkdmarc.spf.check_spf')
    def test_record_check_uses_domain_aware_spf_message(self,check_spf):
        check_spf.return_value=spf_raw('_spf.provider.example.net',[A_WARNING.format(host='_spf.provider.example.net')])
        result=m.record_check('spf','customer.example.com','reject')
        self.assertEqual(result['status'],'warn')
        self.assertTrue(result['warnings'][0].startswith('External provider:'))

    def test_key_messages_are_actionable(self):
        source=open('/app/app.py').read()
        self.assertIn('rotate to 2048-bit when practical',source)
        self.assertIn('Confirm this selector is currently used for signing',source)

if __name__=='__main__': unittest.main(verbosity=2)
