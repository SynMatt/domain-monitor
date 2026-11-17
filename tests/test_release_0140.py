import json,os,subprocess,sys,time,unittest
from pathlib import Path
from unittest.mock import patch
from test_app import Base as Tests
from app import APP_VERSION
import app as m

class Release0140Tests(Tests):
    def row(self):
        self.auth(); self.add()
        with m.db() as c:
            return dict(c.execute("SELECT * FROM domains WHERE domain='example.com'").fetchone())

    def test_collect_domain_isolates_failures(self):
        def boom(*a): raise RuntimeError('fixture failure')
        with patch.object(m,'record_check',side_effect=lambda kind,d,p: m.res('pass',kind)), \
             patch.object(m,'dkim_check',side_effect=boom), \
             patch.object(m.dns_evidence,'lookup',return_value={'status':'ok','queries':{},'warnings':[]}), \
             patch.object(m,'dns_host_lookup',return_value={'lookup_status':'ok','nameservers':[],'provider':None}), \
             patch.object(m.domain_expiry,'lookup',return_value={'status':'not_published'}) as expiry:
            data=m.collect_domain('example.com','selector1','quarantine',True)
            self.assertEqual(data['spf']['status'],'pass')
            self.assertEqual(data['dmarc']['status'],'pass')
            self.assertEqual(data['dkim']['status'],'unknown')
            self.assertIn('fixture failure',data['dkim']['message'])
            self.assertEqual(data['domain_expiry']['status'],'not_published')
            expiry.reset_mock()
            data=m.collect_domain('example.com','selector1','quarantine',False)
            self.assertNotIn('domain_expiry',data); expiry.assert_not_called()

    def test_isolated_domain_uses_one_process(self):
        row=self.row(); payload={'spf':m.res('pass','x')}
        done=subprocess.CompletedProcess([],0,stdout=json.dumps(payload),stderr='')
        with patch.object(m.subprocess,'run',return_value=done) as run:
            self.assertEqual(m.isolated_domain(row,include_expiry=False),payload)
        self.assertEqual(run.call_count,1)
        args=run.call_args[0][0]
        self.assertEqual(args[2:4],['check-domain','example.com']); self.assertEqual(args[-1],'0')
        self.assertEqual(run.call_args[1]['timeout'],m.DOMAIN_CHECK_TIMEOUT)

    def test_isolated_domain_failures_return_none(self):
        row=self.row()
        with patch.object(m.subprocess,'run',side_effect=subprocess.TimeoutExpired('x',1)):
            self.assertIsNone(m.isolated_domain(row))
        with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],1,stdout='',stderr='crash')):
            self.assertIsNone(m.isolated_domain(row))
        with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout='not json',stderr='')):
            self.assertIsNone(m.isolated_domain(row))

    def test_process_failure_saves_unknown_not_stale_pass(self):
        row=self.row()
        with patch.object(m,'isolated_domain',return_value=None):
            m.run_domain_check(row,None,False)
        with m.db() as c:
            saved=json.loads(c.execute('SELECT result FROM domains WHERE id=?',(row['id'],)).fetchone()['result'])
        for kind in ('spf','dkim','dmarc'):
            self.assertEqual(saved[kind]['status'],'unknown')
        self.assertEqual(saved['status'],'unknown')

    def test_expiry_cannot_change_email_health(self):
        row=self.row()
        payload={k:m.res('pass','x') for k in ('spf','dkim','dmarc')}
        payload.update(dns_evidence={'status':'ok'},dns_host={'lookup_status':'ok'},domain_expiry=m.res('fail','expired'))
        with patch.object(m,'isolated_domain',return_value=payload):
            m.run_domain_check(row,None,False)
        with m.db() as c:
            saved=json.loads(c.execute('SELECT result FROM domains WHERE id=?',(row['id'],)).fetchone()['result'])
        self.assertEqual(saved['status'],'pass')

    def test_check_domain_cli_prints_json(self):
        env=dict(os.environ)
        code='import app,json,sys\n'\
             'app.record_check=lambda k,d,p: app.res("pass",k)\n'\
             'app.dkim_check=lambda d,s: app.res("pass","dkim")\n'\
             'app.dns_evidence.lookup=lambda d,s: {"status":"ok"}\n'\
             'app.dns_host_lookup=lambda d: {"lookup_status":"ok"}\n'\
             'print(json.dumps(app.collect_domain("example.com","","quarantine",False)))\n'
        p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,env=env,cwd='/app',timeout=60)
        self.assertEqual(p.returncode,0,p.stderr)
        data=json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(set(data),{'spf','dkim','dmarc','dns_evidence','dns_host'})
        self.assertIn("mode=='check-domain'",Path('/app/app.py').read_text())

    def test_progress_reports_average_seconds(self):
        self.auth(); self.row(); self.post('/check-all',next='/')
        with m.db() as c:
            batch=c.execute("SELECT id FROM check_batches WHERE status='active'").fetchone()['id']
            c.execute("UPDATE check_batch_items SET status='complete',started=?,finished=? WHERE batch_id=?",(100.0,112.5,batch))
        data=self.client.get('/check-all/status').get_json()
        self.assertEqual(data['avg_seconds'],12.5)
        self.assertIn('s per domain',Path('/app/static/check-progress.js').read_text())

    def test_compose_cpu_limit_is_configurable(self):
        compose=Path('/app/compose.yaml').read_text()
        self.assertIn('cpus: ${CONTAINER_CPUS:-2.0}',compose)
        self.assertNotIn('cpus: 1.0',compose)
        self.assertIn("CONTAINER_CPUS='2'",Path('/app/.env.example').read_text())

    def test_version(self):
        self.assertEqual(self.client.get('/health').json['version'],APP_VERSION)

if __name__=='__main__': unittest.main(verbosity=2)
