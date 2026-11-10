import os,tempfile,unittest,json,time,base64
from unittest.mock import patch
from werkzeug.security import generate_password_hash
TEMP=tempfile.TemporaryDirectory()
os.environ.update(DATA_DIR=TEMP.name,SECRET_KEY='test-only',ADMIN_PASSWORD_HASH=generate_password_hash('test-password'))
import app as m
class Tests(unittest.TestCase):
    def setUp(self):
        m.init()
        with m.db() as c:
            c.execute('DELETE FROM domains'); c.execute('DELETE FROM attempts')
        self.client=m.app.test_client(); m.app.config['TESTING']=True
    def auth(self):
        with self.client.session_transaction() as s: s.update(authenticated=True,csrf='token')
    def post(self,path,**kw): return self.client.post(path,data=dict(csrf='token',**kw))
    def add(self): return self.post('/new',domain='example.com',label='<script>alert(1)</script>',selectors='selector1',policy='quarantine')
    def test_auth(self):
        self.assertEqual(self.client.get('/').status_code,302)
        self.assertEqual(self.client.get('/health').status_code,200)
    def test_login(self):
        self.client.get('/login')
        with self.client.session_transaction() as s: token=s['csrf']
        self.assertEqual(self.client.post('/login',data=dict(csrf=token,password='test-password')).status_code,302)
        self.assertEqual(self.client.get('/').status_code,200)
    def test_rate_limit(self):
        self.client.get('/login')
        with self.client.session_transaction() as s: token=s['csrf']
        for _ in range(5): self.client.post('/login',data=dict(csrf=token,password='wrong'))
        self.assertIn(b'Too many login attempts',self.client.post('/login',data=dict(csrf=token,password='test-password')).data)
    def test_csrf(self):
        self.auth(); self.assertEqual(self.client.post('/new',data={}).status_code,400)
    def test_domains(self):
        self.assertEqual(m.domain_name('Example.COM.'),'example.com')
        for bad in ('https://example.com','127.0.0.1','-bad.com','a..com','a@b.invalid'):
            with self.assertRaises(ValueError): m.domain_name(bad)
    def test_selectors(self):
        self.assertEqual(m.selectors('Selector1, selector2 selector1'),'selector1,selector2')
        with self.assertRaises(ValueError): m.selectors('bad/name')
    def test_keys(self):
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048).public_key()
        payload=base64.b64encode(key.public_bytes(Encoding.DER,PublicFormat.SubjectPublicKeyInfo)).decode()
        self.assertEqual(m.key_check('v=DKIM1;p='+payload)['status'],'pass')
        for bad in ('p=','p=abc;p=def','v=DKIM2;p=abc','p=!!!!'):
            with self.assertRaises(ValueError): m.key_check(bad)
        self.assertEqual(m.dkim_check('example.com','')['status'],'unknown')
    def test_ed25519(self):
        payload=base64.b64encode(bytes(range(32))).decode()
        self.assertEqual(m.key_check('k=ed25519;p='+payload)['status'],'pass')
        self.assertEqual(m.key_check('k=ed25519;t=y;p='+payload)['status'],'warn')
    def test_pages_and_history(self):
        self.auth(); self.assertEqual(self.add().status_code,302)
        with m.db() as c: ident=c.execute('SELECT id FROM domains').fetchone()[0]
        for path in ('/','/new',f'/domain/{ident}',f'/domain/{ident}/edit'):
            r=self.client.get(path); self.assertEqual(r.status_code,200,path); self.assertNotIn(b'<script>alert(1)</script>',r.data)
        data={k:m.res('pass','Test fixture, not real DNS') for k in ('spf','dkim','dmarc')}; data['status']='pass'
        with m.db() as c:
            c.execute('INSERT INTO history(domain_id,checked,result) VALUES(?,?,?)',(ident,time.time(),json.dumps(data)))
            c.execute('UPDATE domains SET checked=?,result=? WHERE id=?',(time.time()-100000,json.dumps(data),ident))
        self.assertIn(b'STALE',self.client.get('/').data)
        self.assertEqual(self.client.get(f'/domain/{ident}').status_code,200)
        self.assertEqual(self.post(f'/domain/{ident}/check').status_code,302)
        self.assertEqual(self.post(f'/domain/{ident}/delete',confirm='NO').status_code,400)
        self.assertEqual(self.post(f'/domain/{ident}/delete',confirm='DELETE').status_code,302)
        with m.db() as c: self.assertEqual(c.execute('SELECT COUNT(*) FROM history').fetchone()[0],0)
    def test_duplicate(self):
        self.auth(); self.add(); self.assertIn(b'already exists',self.add().data)
    def test_validator_mapping(self):
        import checkdmarc.spf,checkdmarc.dmarc
        with patch.object(checkdmarc.spf,'check_spf',return_value={'valid':True,'parsed':{'all':'pass'}}): self.assertEqual(m.record_check('spf','example.com','none')['status'],'fail')
        with patch.object(checkdmarc.spf,'check_spf',return_value={'valid':False,'error':'DNS timeout'}): self.assertEqual(m.record_check('spf','example.com','none')['status'],'unknown')
        with patch.object(checkdmarc.dmarc,'check_dmarc',return_value={'valid':True,'tags':{'p':{'value':'none'}}}): self.assertEqual(m.record_check('dmarc','example.com','quarantine')['status'],'fail')
        with patch.object(checkdmarc.dmarc,'check_dmarc',return_value={'valid':True,'tags':{'p':{'value':'reject'}},'warnings':[]}): self.assertEqual(m.record_check('dmarc','example.com','quarantine')['status'],'pass')
    def test_status(self): self.assertEqual(m.worst([{'status':'pass'},{'status':'unknown'}]),'unknown')
    def test_manual_preserves_schedule(self):
        self.auth(); self.add()
        with m.db() as c: row=c.execute('SELECT * FROM domains').fetchone(); ident=row['id']; due=row['due']
        self.post(f'/domain/{ident}/check')
        with m.db() as c: row=c.execute('SELECT * FROM domains').fetchone()
        self.assertEqual(row['due'],due)
        self.assertEqual(row['manual_pending'],1)
    def test_global_schedule(self):
        self.auth(); self.add()
        self.assertEqual(self.post('/settings',daily_time='06:30').status_code,302)
        with m.db() as c:
            self.assertEqual(m.get_clock(c),'06:30')
            row=c.execute('SELECT * FROM domains').fetchone()
        local=m.datetime.fromtimestamp(row['due'],m.NZ)
        self.assertEqual((local.hour,local.minute),(6,30))
        self.assertEqual(self.client.get('/settings').status_code,200)
    def test_dst_schedule(self):
        for date,expected in [('2026-09-27T00:00:00',3),('2026-04-05T00:00:00',2)]:
            now=m.datetime.fromisoformat(date).replace(tzinfo=m.NZ).timestamp()
            first=m.next_run(now,'02:30')
            local=m.datetime.fromtimestamp(first,m.NZ)
            self.assertEqual(local.hour,expected)
            second=m.next_run(first,'02:30')
            self.assertGreater(m.datetime.fromtimestamp(second,m.NZ).date(),local.date())
    def test_time_validation(self):
        for value in ('24:00','6:30','12:60',''):
            with self.assertRaises(ValueError): m.validate_time(value)
if __name__=='__main__': unittest.main(verbosity=2)
