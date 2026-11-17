import json,stat,time,unittest
from pathlib import Path
from unittest.mock import patch
from test_app import Base
import app as m
def payload(spf='v=spf1 -all',noise=0):
    data={}
    data['spf']=m.res('pass','Valid SPF; DNS lookups: 1',warnings=[],raw={'record':spf,'valid':True,'dns_lookups':1,'void_dns_lookups':0,'warnings':[],'parsed':{'include':['x'*4000]}})
    data['dkim']=m.res('pass','All configured selectors must pass.',selectors=[{'selector':'selector1','query':'selector1._domainkey.example.com.','status':'pass','message':'RSA 2048-bit key','warnings':[],'record':'v=DKIM1; p=abc'}])
    data['dmarc']=m.res('pass','Valid DMARC; effective policy reject; required quarantine.',warnings=[],raw={'record':'v=DMARC1; p=reject','valid':True,'location':'example.com','tags':{'p':{'value':'reject'}},'warnings':[]})
    timing={'status':'ok','records':[spf],'ttl':300-noise,'elapsed_ms':10+noise,'servers':['127.0.0.11']}
    data['dns_evidence']={'status':'ok','warnings':[],'queries':{
        'spf':{'query_name':'example.com.','record_type':'TXT','recursive':timing,'authoritative':[{'nameserver':'ns1.example.net','status':'ok','elapsed_ms':5+noise,'records':[spf]}],'consensus':'yes','authoritative_records':[spf],'recursive_matches_authoritative':True},
        'dmarc':{'query_name':'_dmarc.example.com.','recursive':timing,'authoritative':[],'consensus':'yes','recursive_matches_authoritative':True},
        'dkim':{'selector1':{'recursive':timing,'authoritative':[],'consensus':'yes'}}}}
    data['dns_host']={'lookup_status':'ok','nameservers':['ns1.example.net'],'provider':None}
    data['domain_expiry']={'status':'ok','checked_at':time.time()-noise,'expires_at':2000000000.0,'days_remaining':400-noise,'source':'RDAP','error':None}
    return data
class Release0142Tests(Base):
    def row(self):
        self.auth(); self.add()
        with m.db() as c:
            return dict(c.execute("SELECT * FROM domains WHERE domain='example.com'").fetchone())
    def check(self,row,result,scheduled=False):
        with patch.object(m,'isolated_domain',return_value=result):
            m.run_domain_check(row,None,scheduled)
    def history(self,ident):
        with m.db() as c:
            return [dict(r) for r in c.execute('SELECT * FROM history WHERE domain_id=? ORDER BY id',(ident,))]
    def test_slim_result_drops_bulky_detail_only(self):
        full=payload(); slim=m.slim_result(full)
        self.assertNotIn('parsed',slim['spf']['raw'])
        self.assertEqual(slim['spf']['raw']['record'],'v=spf1 -all')
        self.assertEqual(slim['dkim'],full['dkim'])
        self.assertEqual(slim['dmarc'],full['dmarc'])
        self.assertEqual(set(slim['dns_evidence']['queries']),{'spf','dmarc'})
        self.assertNotIn('recursive',slim['dns_evidence']['queries']['spf'])
        self.assertTrue(slim['dns_evidence']['compact'])
        self.assertIn('parsed',full['spf']['raw'])
        self.assertLess(len(json.dumps(slim)),len(json.dumps(full))/3)
        self.assertEqual(m.slim_result(slim),slim)
    def test_unchanged_results_extend_one_entry(self):
        row=self.row()
        self.check(row,payload(noise=0),scheduled=False)
        self.check(row,payload(noise=7),scheduled=True)
        rows=self.history(row['id'])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['checks'],2)
        self.assertLessEqual(rows[0]['first_checked'],rows[0]['checked'])
        self.assertEqual(json.loads(rows[0]['result'])['trigger'],'scheduled')
    def test_changed_result_adds_entry_and_compacts_previous(self):
        row=self.row()
        self.check(row,payload())
        self.check(row,payload(spf='v=spf1 include:spf.example.net -all'))
        rows=self.history(row['id'])
        self.assertEqual(len(rows),2)
        older,newest=(json.loads(r['result']) for r in rows)
        self.assertNotIn('parsed',older['spf']['raw'])
        self.assertTrue(older['dns_evidence']['compact'])
        self.assertIn('parsed',newest['spf']['raw'])
        self.assertIn('recursive',newest['dns_evidence']['queries']['spf'])
    def test_one_time_upgrade_compaction(self):
        row=self.row(); full=json.dumps(payload())
        with m.db() as c:
            for offset in (300,200,100):
                c.execute('INSERT INTO history(domain_id,checked,result) VALUES(?,?,?)',(row['id'],time.time()-offset,full))
            c.execute('UPDATE history SET first_checked=NULL')
            c.execute('DELETE FROM state WHERE key=?',(m.HISTORY_COMPACT_KEY,))
        m.init()
        rows=self.history(row['id'])
        self.assertEqual(len(rows),3)
        self.assertTrue(all(r['first_checked']==r['checked'] for r in rows))
        sizes=[len(r['result']) for r in rows]
        self.assertLess(sizes[0],len(full)); self.assertLess(sizes[1],len(full)); self.assertEqual(sizes[2],len(full))
        with m.db() as c:
            self.assertIsNotNone(c.execute('SELECT 1 FROM state WHERE key=?',(m.HISTORY_COMPACT_KEY,)).fetchone())
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        before=[r['result'] for r in rows]; m.init()
        self.assertEqual([r['result'] for r in self.history(row['id'])],before)
    def test_detail_page_shows_grouped_checks(self):
        row=self.row(); self.check(row,payload()); self.check(row,payload(noise=3))
        page=self.client.get(f"/domain/{row['id']}")
        self.assertEqual(page.status_code,200)
        self.assertIn(b'Same result for 2 checks',page.data)
    def test_dependencies_and_fast_test_tooling(self):
        self.assertIn('Flask==3.1.3',Path('/app/requirements.txt').read_text().splitlines())
        update=Path('/app/scripts/update.sh').read_text()
        self.assertIn('unittest discover -s /app/tests',update)
        self.assertNotIn('for test in tests/test_',update)
        runner=Path('/app/scripts/run-tests.sh')
        self.assertTrue(runner.stat().st_mode & stat.S_IXOTH)
        self.assertIn('unittest discover',runner.read_text())
    def test_rdap_https_only_and_current_user_agent(self):
        import domain_expiry
        self.assertIn("startswith('https://')",Path('/app/domain_expiry.py').read_text())
        self.assertNotRegex(domain_expiry.USER_AGENT,r'/\d+\.\d+')
if __name__=='__main__': unittest.main(verbosity=2)
