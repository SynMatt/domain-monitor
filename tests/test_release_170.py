import json,time
from datetime import datetime,timedelta
from pathlib import Path
from test_app import Base
import app as m

class ExpiryAndRecentChangesTests(Base):
    def add_with_result(self,name,days=None,status='pass'):
        response=self.post(
            '/new',
            domain=name,
            label='',
            selectors='selector1',
            policy='quarantine',
            manual_expiry='',
            manual_expiry_source=''
        )
        self.assertEqual(response.status_code,302)
        with m.db() as c:
            row=c.execute('SELECT * FROM domains WHERE domain=?',(name,)).fetchone(); ident=row['id']
            expiry=None if days is None else time.time()+days*86400
            data={k:m.res(status,'Fixture') for k in ('spf','dkim','dmarc')}
            data.update(status=status,trigger='scheduled',dns_host={'nameservers':['ns1.example.net']},domain_expiry={'status':'unknown' if days is None else 'ok','expires_at':expiry})
            c.execute('UPDATE domains SET result=?,checked=?,manual_pending=0 WHERE id=?',(json.dumps(data),time.time(),ident))
        return ident,data
    def test_expiry_buckets_and_filter(self):
        self.auth(); self.add_with_result('expired.example',-1); self.add_with_result('soon.example',20); self.add_with_result('later.example',70); self.add_with_result('unknown.example',None)
        cases=(('expired','expired.example'),('30','soon.example'),('90','later.example'),('unknown','unknown.example'))
        for bucket,name in cases:
            html=self.client.get('/?expiry='+bucket).get_data(as_text=True)
            self.assertIn(name,html)
        self.assertIn('name="expiry"',self.client.get('/').get_data(as_text=True))
    def test_manual_expiry_takes_priority(self):
        now=time.time(); zone=m.selected_zone(); future=(datetime.fromtimestamp(now,zone).date()+timedelta(days=10)).isoformat()
        domain={'manual_expiry':future,'data':{'domain_expiry':{'status':'ok','expires_at':now+200*86400}}}
        self.assertEqual(m.expiry_bucket(domain,now,zone),'30')
    def test_recent_changes_backfills_only_differences(self):
        self.auth(); ident,data=self.add_with_result('change.example',100,'pass'); now=time.time()
        with m.db() as c:
            c.execute('INSERT INTO history(domain_id,checked,first_checked,result) VALUES(?,?,?,?)',(ident,now-20,now-20,json.dumps(data)))
            same=dict(data); same['trigger']='manual / new or edited domain'
            c.execute('INSERT INTO history(domain_id,checked,first_checked,result) VALUES(?,?,?,?)',(ident,now-10,now-10,json.dumps(same)))
            changed=json.loads(json.dumps(data)); changed['dkim']['status']='warn'; changed['status']='warn'
            c.execute('INSERT INTO history(domain_id,checked,first_checked,result) VALUES(?,?,?,?)',(ident,now,now,json.dumps(changed)))
        html=self.client.get('/recent-changes').get_data(as_text=True)
        self.assertEqual(
            html.count('<strong>DKIM status</strong>'),
            1
        )
        self.assertIn('<code>Pass</code>',html)
        self.assertIn('<code>Warn</code>',html)
        self.assertIn(
            '<span class="change-arrow" aria-label="changed to">→</span>',
            html
        )
        self.assertIn('change.example',html)
    def test_navigation_and_docs(self):
        self.auth(); page=self.client.get('/recent-changes')
        self.assertEqual(page.status_code,200)
        self.assertIn(b'Recent changes',self.client.get('/').data)
        readme=Path('/app/README.md').read_text(); self.assertIn('90-day / 1,000-entry',readme)
