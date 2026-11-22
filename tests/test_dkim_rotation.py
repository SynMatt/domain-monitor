import json,time,unittest
from datetime import datetime,timedelta
from unittest.mock import patch
from test_app import Base
import app as m

class DKIMRotationTests(Base):
    def setUp(self):
        super().setUp(); self.auth(); self.add()
        with m.db() as c: self.ident=c.execute('SELECT id FROM domains').fetchone()[0]
        self.today=datetime.now(m.selected_zone()).date()
    def row(self):
        with m.db() as c: return dict(c.execute('SELECT * FROM domains WHERE id=?',(self.ident,)).fetchone())
    def start(self,value=None):
        return self.post(f'/domain/{self.ident}/dkim-rotation',dkim_rotation_started=value or self.today.isoformat())
    def fixture(self,status='warn',age=0):
        data={k:m.res('pass','Fixture') for k in ('spf','dkim','dmarc')}
        data['dkim']=m.res(status,'Fixture'); data['status']=m.worst(list(data.values()))
        now=time.time()-age
        with m.db() as c:
            c.execute('UPDATE domains SET result=?,checked=?,manual_pending=0 WHERE id=?',(json.dumps(data),now,self.ident))
            c.execute('INSERT INTO history(domain_id,checked,result) VALUES(?,?,?)',(self.ident,now,json.dumps(data)))
        return data
    def test_calendar_days_boundaries_and_dst(self):
        zone=m.ZoneInfo('Pacific/Auckland')
        for offset in range(5):
            now=datetime(2030,1,10+offset,12,tzinfo=zone).timestamp()
            info=m.dkim_rotation_info('2030-01-10',now,zone)
            self.assertEqual(info['active'],offset<4)
            self.assertEqual(info['day'],min(offset+1,4))
        boundary=datetime(2030,1,14,tzinfo=zone).timestamp()
        self.assertTrue(m.dkim_rotation_info('2030-01-10',boundary-1,zone)['active'])
        self.assertFalse(m.dkim_rotation_info('2030-01-10',boundary,zone)['active'])
        for value in ('','bad','2030-01-15'): self.assertIsNone(m.dkim_rotation_info(value,boundary,zone))
        now=datetime(2026,9,29,23,59,tzinfo=zone).timestamp()
        self.assertEqual(m.dkim_rotation_info('2026-09-26',now,zone)['day'],4)
        self.assertFalse(m.dkim_rotation_info('2026-09-26',datetime(2026,9,30,tzinfo=zone).timestamp(),zone)['active'])
    def test_validation(self):
        for bad in ('bad','2026-02-30','2026-1-01',(self.today+timedelta(days=1)).isoformat()):
            with self.assertRaises(ValueError): m.validate_dkim_rotation_date(bad)
        self.assertEqual(m.validate_dkim_rotation_date(''),'')
        self.assertEqual(m.validate_dkim_rotation_date(self.today.isoformat()),self.today.isoformat())
    def test_save_preserves_result_schedule_and_warn_totals(self):
        self.fixture(); before=self.row(); self.assertEqual(self.start().status_code,302); after=self.row()
        for key in ('result','checked','due'): self.assertEqual(before[key],after[key])
        self.assertEqual(after['manual_pending'],1)
        self.assertEqual(after['revision'],before['revision']+1)
        html=self.client.get('/?kind=dkim&status=warn').get_data(as_text=True)
        for text in ('DKIM: Warn<span class="rotation-marker"','DKIM rotation: Day 1 of 4','Warn: 1','example.com'): self.assertIn(text,html)
        html=self.client.get(f'/domain/{self.ident}').get_data(as_text=True)
        self.assertEqual(html.count('class="rotation-marker"'),1)
    def test_no_star_for_other_statuses_or_stale(self):
        self.start()
        for status in ('pass','fail','unknown'):
            self.fixture(status)
            self.assertNotIn('class="rotation-marker"',self.client.get('/').get_data(as_text=True))
        self.fixture('warn',27*3600)
        for path in ('/',f'/domain/{self.ident}'):
            self.assertNotIn('class="rotation-marker"',self.client.get(path).get_data(as_text=True))
    def test_expiry_and_clear(self):
        self.fixture(); self.start((self.today-timedelta(days=4)).isoformat())
        html=self.client.get('/').get_data(as_text=True)
        self.assertNotIn('class="rotation-marker"',html); self.assertIn('DKIM rotation window ended',html)
        before=self.row(); self.post(f'/domain/{self.ident}/dkim-rotation',rotation_action='clear'); after=self.row()
        self.assertEqual(after['dkim_rotation_started'],'')
        for key in ('result','checked','due','manual_pending'): self.assertEqual(before[key],after[key])
    def test_today_invalid_missing_and_csrf(self):
        path=f'/domain/{self.ident}/dkim-rotation'
        self.post(path,rotation_action='today'); self.assertEqual(self.row()['dkim_rotation_started'],self.today.isoformat())
        before=self.row(); self.start('bad'); self.assertEqual(self.row(),before)
        self.assertEqual(self.post('/domain/999999/dkim-rotation',rotation_action='today').status_code,404)
        self.assertEqual(self.post(path,rotation_action='bad').status_code,400)
        self.assertEqual(self.client.post(path,data={}).status_code,400)
        with self.client.session_transaction() as s: s.pop('authenticated',None)
        self.assertEqual(self.post(path,rotation_action='clear').status_code,302)
        self.assertEqual(self.row(),before)
    def test_fresh_pass_clears_but_other_results_do_not(self):
        self.start()
        for status in ('warn','fail','unknown'):
            data=self.fixture(status)
            with patch.object(m,'isolated_domain',return_value=data): m.run_domain_check(self.row(),None,False)
            self.assertEqual(self.row()['dkim_rotation_started'],self.today.isoformat())
        data=self.fixture('pass')
        with patch.object(m,'isolated_domain',return_value=data): m.run_domain_check(self.row(),None,False)
        self.assertEqual(self.row()['dkim_rotation_started'],'')
        with m.db() as c: saved=json.loads(c.execute('SELECT result FROM history ORDER BY id DESC LIMIT 1').fetchone()[0])
        self.assertEqual(saved['configuration']['dkim_rotation_started'],self.today.isoformat())
    def test_old_worker_cannot_clear_new_date(self):
        self.start((self.today-timedelta(days=1)).isoformat()); old=self.row(); self.start()
        data={k:m.res('pass','Fixture') for k in ('spf','dkim','dmarc')}
        with patch.object(m,'isolated_domain',return_value=data): m.run_domain_check(old,None,False)
        self.assertEqual(self.row()['dkim_rotation_started'],self.today.isoformat())
    def test_repeatable_migration_and_edit_roundtrip(self):
        self.start(); m.init(); m.init()
        self.assertEqual(self.row()['dkim_rotation_started'],self.today.isoformat())
        with m.db() as c: self.assertEqual([r[1] for r in c.execute('PRAGMA table_info(domains)')].count('dkim_rotation_started'),1)
        html=self.client.get(f'/domain/{self.ident}/edit').get_data(as_text=True)
        self.assertIn('name="dkim_rotation_started"',html)
        response=self.post(f'/domain/{self.ident}/edit',domain='example.com',label='',selectors='selector1',policy='quarantine',dkim_rotation_started=self.today.isoformat())
        self.assertEqual(response.status_code,302); self.assertEqual(self.row()['dkim_rotation_started'],self.today.isoformat())

if __name__=='__main__': unittest.main()
