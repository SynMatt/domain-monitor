import time,unittest
from test_app import Tests
import app as m
class BatchTests(Tests):
 def add_name(self,n): return self.post('/new',domain=n,label='',selectors='',policy='quarantine')
 def test_one_batch_for_repeated_clicks(self):
  self.auth();self.add_name('one.example');self.add_name('two.example');self.post('/check-all',next='/');self.post('/check-all',next='/')
  with m.db() as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM check_batches').fetchone()[0],1);self.assertEqual(c.execute('SELECT COUNT(*) FROM check_batch_items').fetchone()[0],2)
  self.assertEqual(self.client.get('/check-all/status').get_json()['total'],2)
 def test_status_auth_and_schema(self):
  self.assertEqual(self.client.get('/check-all/status').status_code,302);m.init();m.init()
  with m.db() as c: names={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  self.assertIn('check_batches',names);self.assertIn('check_batch_items',names)
if __name__=='__main__':unittest.main(verbosity=2)
