from pathlib import Path
from test_app import Base
import app as m

class CapitalStatusEverywhereTests(Base):
    def test_detail_current_and_history_statuses_are_capitalised(self):
        self.auth(); self.add()
        with m.db() as c:
            ident=c.execute('SELECT id FROM domains').fetchone()[0]
            data={k:m.res(v,'Fixture') for k,v in [('spf','pass'),('dkim','warn'),('dmarc','fail')]}
            data['status']='fail'
            import json,time
            encoded=json.dumps(data); now=time.time()
            c.execute('UPDATE domains SET result=?,checked=?,manual_pending=0 WHERE id=?',(encoded,now,ident))
            c.execute('INSERT INTO history(domain_id,checked,result) VALUES(?,?,?)',(ident,now,encoded))
        html=self.client.get(f'/domain/{ident}').get_data(as_text=True)
        for label in ('SPF: Pass','DKIM: Warn','DMARC: Fail'):
            self.assertIn(label,html)
        for label in ('title="SPF: Pass"','title="DKIM: Warn"','title="DMARC: Fail"'):
            self.assertIn(label,html)
        self.assertNotIn('SPF: pass',html)
        self.assertNotIn('DKIM: warn',html)
        self.assertNotIn('DMARC: fail',html)
    def test_filter_labels_are_capitalised_but_values_stay_lowercase(self):
        self.auth()
        html=self.client.get('/?kind=dkim&status=warn').get_data(as_text=True)
        self.assertIn('Show DKIM Warn domains',html)
        self.assertIn('No domains currently match DKIM Warn.',html)
        self.assertIn('name="status" value="warn"',html)
