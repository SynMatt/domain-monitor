import time
import unittest
from pathlib import Path
from test_app import Base
import app as m

class DetailExpirySummaryTests(Base):
    def test_template_uses_latest_automatic_expiry_result(self):
        source=Path('/app/templates/detail.html').read_text()
        self.assertIn('expiry_label(latest.data if latest else none,domain.manual_expiry,domain.manual_expiry_source)',source)
        self.assertNotIn('expiry_label(none,domain.manual_expiry,domain.manual_expiry_source)',source)

    def test_successful_expiry_is_shown_on_detail_summary(self):
        self.auth(); self.add()
        expiry=time.time()+700*86400
        with m.db() as c:
            row=c.execute('SELECT * FROM domains LIMIT 1').fetchone()
            data={k:m.res('pass','Fixture') for k in ('spf','dkim','dmarc')}
            data.update(status='pass',domain_expiry={'status':'ok','expires_at':expiry,'days_remaining':700,'source':'RDAP','error':None})
            import json
            encoded=json.dumps(data)
            c.execute('UPDATE domains SET checked=?,result=?,manual_pending=0 WHERE id=?',(time.time(),encoded,row['id']))
            c.execute('INSERT INTO history(domain_id,checked,first_checked,result) VALUES(?,?,?,?)',(row['id'],time.time(),time.time(),encoded))
        html=self.client.get(f"/domain/{row['id']}").get_data(as_text=True)
        self.assertIn('Source: RDAP',html)
        self.assertNotIn('Source: Not checked yet',html)
