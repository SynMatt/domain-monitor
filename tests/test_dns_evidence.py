import unittest
from unittest.mock import patch
import dns_evidence as evidence

class EvidenceTests(unittest.TestCase):
    def test_consensus_and_match(self):
        recursive={'status':'ok','records':['v=DMARC1; p=reject'],'servers':['127.0.0.11']}
        direct={'status':'ok','rcode':'NOERROR','records':['v=DMARC1; p=reject'],'ttl':300}
        with patch.object(evidence,'_recursive',return_value=recursive), \
             patch.object(evidence,'_authoritative_servers',return_value=['ns1.example.net','ns2.example.net']), \
             patch.object(evidence,'_addresses',return_value=['192.0.2.53']), \
             patch.object(evidence,'_direct',return_value=direct):
            result=evidence.query_evidence('example.com','_dmarc.example.com','TXT')
        self.assertEqual(result['consensus'],'yes')
        self.assertTrue(result['recursive_matches_authoritative'])

    def test_disagreement_is_visible(self):
        recursive={'status':'ok','records':['old'],'servers':['127.0.0.11']}
        direct={'status':'ok','rcode':'NOERROR','records':['new'],'ttl':60}
        with patch.object(evidence,'_recursive',return_value=recursive), \
             patch.object(evidence,'_authoritative_servers',return_value=['ns1.example.net']), \
             patch.object(evidence,'_addresses',return_value=['192.0.2.53']), \
             patch.object(evidence,'_direct',return_value=direct):
            result=evidence.query_evidence('example.com','_dmarc.example.com','TXT')
        self.assertEqual(result['consensus'],'yes')
        self.assertFalse(result['recursive_matches_authoritative'])

    def test_authoritative_inconsistency(self):
        answers=iter([
            {'status':'ok','rcode':'NOERROR','records':['one'],'ttl':60},
            {'status':'ok','rcode':'NOERROR','records':['two'],'ttl':60},
        ])
        with patch.object(evidence,'_recursive',return_value={'status':'ok','records':['one']}), \
             patch.object(evidence,'_authoritative_servers',return_value=['ns1.example.net','ns2.example.net']), \
             patch.object(evidence,'_addresses',return_value=['192.0.2.53']), \
             patch.object(evidence,'_direct',side_effect=lambda *args: next(answers)):
            result=evidence.query_evidence('example.com','_dmarc.example.com','TXT')
        self.assertEqual(result['consensus'],'inconsistent')

if __name__=='__main__': unittest.main(verbosity=2)
