import json,time
from pathlib import Path
from test_app import Base
import app as m

class RecentChangeEvidenceAndLayoutTests(Base):
    def test_dashboard_control_order_and_grid(self):
        index=Path('/app/templates/index.html').read_text(); base=Path('/app/templates/base.html').read_text()
        self.assertLess(index.index('for="q"'),index.index('for="expiry"'))
        self.assertLess(index.index('for="expiry"'),index.index('for="sort"'))
        self.assertIn('minmax(260px,1fr) minmax(180px,240px) minmax(190px,260px) auto',base)
    def test_structured_before_after_values(self):
        old={k:m.res('pass','Fixture') for k in ('spf','dkim','dmarc')}
        new=json.loads(json.dumps(old)); new['dkim']['status']='warn'
        old['spf']['raw']={'record':'v=spf1 -all'}; new['spf']['raw']={'record':'v=spf1 include:_spf.example.net -all'}
        details=m.history_change_details(new,old)
        values={item['label']:(item['before'],item['after']) for item in details}
        self.assertEqual(values['DKIM status'],('Pass','Warn'))
        self.assertEqual(values['SPF record'],('v=spf1 -all','v=spf1 include:_spf.example.net -all'))
    def test_recent_page_renders_arrow_and_evidence(self):
        self.auth(); self.add()
        with m.db() as c:
            ident=c.execute('SELECT id FROM domains').fetchone()[0]; now=time.time()
            old={k:m.res('pass','Fixture') for k in ('spf','dkim','dmarc')}; old['status']='pass'; old['trigger']='scheduled'
            new=json.loads(json.dumps(old)); new['dkim']['status']='warn'; new['status']='warn'
            c.execute('INSERT INTO history(domain_id,checked,first_checked,result) VALUES(?,?,?,?)',(ident,now-1,now-1,json.dumps(old)))
            c.execute('INSERT INTO history(domain_id,checked,first_checked,result) VALUES(?,?,?,?)',(ident,now,now,json.dumps(new)))
        html=self.client.get('/recent-changes').get_data(as_text=True)
        self.assertIn('DKIM status',html); self.assertIn('Pass',html); self.assertIn('Warn',html); self.assertIn('→',html)
