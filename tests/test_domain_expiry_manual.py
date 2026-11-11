from datetime import datetime,timezone
import json, os, tempfile, unittest
from unittest.mock import patch
from pathlib import Path
from werkzeug.security import generate_password_hash

TEMP=tempfile.TemporaryDirectory()
os.environ.update(DATA_DIR=TEMP.name,SECRET_KEY='test-only',ADMIN_PASSWORD_HASH=generate_password_hash('test-password'))
import app as m
import domain_expiry as de

class DomainExpiryManualTests(unittest.TestCase):
    def setUp(self):
        m.init()
        with m.db() as c:
            c.execute('DELETE FROM domains')
        self.client=m.app.test_client(); m.app.config['TESTING']=True
        with self.client.session_transaction() as s: s.update(authenticated=True,csrf='token')

    def post(self,path,**data):
        return self.client.post(path,data=dict(csrf='token',**data))

    def test_nz_whois_without_expiry_is_not_published(self):
        text='''Domain Name: example.co.nz\nUpdated Date: 2026-07-18T04:45:42Z\nCreation Date: 2002-02-21T09:59:00Z\n'''
        result=de.parse_nz_whois(text,datetime(2026,11,11,tzinfo=timezone.utc))
        self.assertEqual(result['status'],'not_published')
        self.assertIsNone(result['expires_at'])
        self.assertEqual(de.label({'domain_expiry':result}),'Not published by registry')

    def test_nz_whois_explicit_expiry_only(self):
        text='Registry Expiry Date: 2027-03-18T00:00:00Z\nUpdated Date: 2026-07-18T04:45:42Z\n'
        result=de.parse_nz_whois(text,datetime(2026,11,11,tzinfo=timezone.utc))
        self.assertEqual(result['status'],'ok')
        self.assertGreater(result['days_remaining'],120)

    def test_manual_date_validation_and_priority(self):
        with self.assertRaises(ValueError): de.validate_manual_date('18/03/2027')
        data={'domain_expiry':{'status':'not_published','source':'.nz WHOIS'}}
        with patch('domain_expiry.datetime') as mocked:
            mocked.now.return_value=datetime(2026,11,11,tzinfo=timezone.utc)
            mocked.combine=datetime.combine
            mocked.min=datetime.min
            mocked.fromtimestamp=datetime.fromtimestamp
            label=de.label(data,'2027-03-18','Registrar portal')
        self.assertIn('18 Mar 2027',label)
        self.assertIn('Manual',label)
        self.assertEqual(de.source_label(data,'2027-03-18','Registrar portal'),'Registrar portal')

    def test_manual_fields_persist_and_render(self):
        response=self.post('/new',domain='example.com',label='',selectors='',policy='quarantine',manual_expiry='2027-03-18',manual_expiry_source='Registrar portal')
        self.assertEqual(response.status_code,302)
        with m.db() as c:
            row=c.execute('SELECT * FROM domains').fetchone()
            ident=row['id']
            self.assertEqual(row['manual_expiry'],'2027-03-18')
            self.assertEqual(row['manual_expiry_source'],'Registrar portal')
        page=self.client.get('/')
        self.assertIn(b'Domain expiry:',page.data)
        self.assertIn(b'Manual',page.data)
        detail=self.client.get(f'/domain/{ident}')
        self.assertIn(b'Registrar portal',detail.data)

    def test_expiry_does_not_change_email_health(self):
        source=Path('/app/app.py').read_text()
        status_line="data['status']=worst(data.values())"
        expiry_line="data['domain_expiry']=isolated('domain_expiry',row)"
        self.assertLess(source.index(status_line),source.index(expiry_line))

if __name__=='__main__': unittest.main(verbosity=2)
