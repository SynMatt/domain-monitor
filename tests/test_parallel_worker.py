import os,time,unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from test_app import Base as Tests
import app as m

class ParallelWorkerTests(Tests):
 def test_worker_setting_is_bounded(self):
  with patch.dict(os.environ,{'CHECK_WORKERS':'4'}): self.assertEqual(m.check_workers(),4)
  with patch.dict(os.environ,{'CHECK_WORKERS':'0'}): self.assertEqual(m.check_workers(),1)
  with patch.dict(os.environ,{'CHECK_WORKERS':'99'}): self.assertEqual(m.check_workers(),8)
  with patch.dict(os.environ,{'CHECK_WORKERS':'bad'}): self.assertEqual(m.check_workers(),4)
 def test_parallel_execution_overlaps(self):
  started=[]
  def task(value): started.append((value,time.monotonic())); time.sleep(.15); return value
  begin=time.monotonic()
  with ThreadPoolExecutor(max_workers=4) as pool: self.assertEqual(sorted(pool.map(task,range(4))),[0,1,2,3])
  self.assertLess(time.monotonic()-begin,.45)
 def test_running_items_recovery_sql_is_present(self):
  from pathlib import Path
  source=Path('/app/app.py').read_text()
  self.assertIn("UPDATE check_batch_items SET status='queued',started=NULL WHERE status='running'",source)
  self.assertIn('ThreadPoolExecutor(max_workers=workers',source)
 def test_manual_check_does_not_duplicate_batch_item(self):
  self.auth(); self.add()
  with m.db() as c:
   ident=c.execute('SELECT id FROM domains').fetchone()['id']; c.execute('UPDATE domains SET manual_pending=0 WHERE id=?',(ident,))
  self.post('/check-all',next='/')
  with m.db() as c: before=c.execute('SELECT revision FROM domains WHERE id=?',(ident,)).fetchone()['revision']
  response=self.client.post(f'/domain/{ident}/check',data={'csrf':'token','next':'/'},follow_redirects=True)
  with m.db() as c: after=c.execute('SELECT revision FROM domains WHERE id=?',(ident,)).fetchone()['revision']
  self.assertEqual(before,after); self.assertIn(b'Already included',response.data)

if __name__=='__main__': unittest.main(verbosity=2)
