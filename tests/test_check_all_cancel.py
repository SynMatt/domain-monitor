import time,unittest
from test_app import Tests
import app as m

class CheckAllCancelTests(Tests):
 def add_name(self,name): return self.post('/new',domain=name,label='',selectors='',policy='quarantine')
 def start_three(self):
  self.add_name('one.example'); self.add_name('two.example'); self.add_name('three.example')
  with m.db() as c: c.execute('UPDATE domains SET manual_pending=0')
  self.post('/check-all',next='/?sort=domain')
  with m.db() as c:
   batch=c.execute("SELECT id FROM check_batches WHERE status='active'").fetchone()['id']
   first=c.execute('SELECT domain_id FROM check_batch_items WHERE batch_id=? ORDER BY domain_id LIMIT 1',(batch,)).fetchone()['domain_id']
   c.execute("UPDATE check_batch_items SET status='running',started=? WHERE batch_id=? AND domain_id=?",(time.time(),batch,first))
  return batch,first
 def test_requires_authentication_and_csrf(self):
  self.assertEqual(self.client.post('/check-all/cancel',data={}).status_code,400)
  self.auth(); self.assertEqual(self.client.post('/check-all/cancel',data={}).status_code,400)
 def test_cancel_stops_queued_but_not_running(self):
  self.auth(); batch,running=self.start_three()
  response=self.client.post('/check-all/cancel',data={'csrf':'token','next':'/?sort=domain'},follow_redirects=True)
  self.assertIn(b'Check-all cancelled',response.data)
  with m.db() as c:
   row=c.execute('SELECT status,cancelled,finished FROM check_batches WHERE id=?',(batch,)).fetchone()
   self.assertEqual(row['status'],'complete'); self.assertEqual(row['cancelled'],1); self.assertIsNotNone(row['finished'])
   items=c.execute('SELECT domain_id,status,error FROM check_batch_items WHERE batch_id=? ORDER BY domain_id',(batch,)).fetchall()
   self.assertEqual(next(x for x in items if x['domain_id']==running)['status'],'running')
   cancelled=[x for x in items if x['domain_id']!=running]
   self.assertTrue(all(x['status']=='failed' and x['error']=='Cancelled by administrator' for x in cancelled))
   pending={r['id']:r['manual_pending'] for r in c.execute('SELECT id,manual_pending FROM domains')}
   self.assertEqual(pending[running],1)
   self.assertTrue(all(pending[x['domain_id']]==0 for x in cancelled))
 def test_preexisting_individual_queue_is_preserved(self):
  self.auth(); self.add_name('priority.example'); self.add_name('normal.example')
  with m.db() as c:
   priority=c.execute("SELECT id FROM domains WHERE domain='priority.example'").fetchone()['id']
   c.execute("UPDATE domains SET manual_pending=CASE WHEN id=? THEN 1 ELSE 0 END",(priority,))
  self.post('/check-all',next='/')
  self.post('/check-all/cancel',next='/')
  with m.db() as c:
   self.assertEqual(c.execute('SELECT manual_pending FROM domains WHERE id=?',(priority,)).fetchone()[0],1)
   normal=c.execute("SELECT manual_pending FROM domains WHERE domain='normal.example'").fetchone()[0]
   self.assertEqual(normal,0)
 def test_cancel_without_active_batch_is_safe(self):
  self.auth(); response=self.client.post('/check-all/cancel',data={'csrf':'token','next':'/'},follow_redirects=True)
  self.assertIn(b'No active Check-all run',response.data)
 def test_dashboard_contains_cancel_control(self):
  self.auth(); self.add_name('one.example'); self.post('/check-all',next='/')
  page=self.client.get('/')
  self.assertIn(b'action="/check-all/cancel"',page.data)
  self.assertIn(b'Cancel remaining checks',page.data)

if __name__=='__main__': unittest.main(verbosity=2)
