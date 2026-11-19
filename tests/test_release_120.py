import json,time,unittest
from unittest.mock import patch
from test_app import Base
import app as m

DMARC_RECORD='v=DMARC1; p=quarantine; rua=mailto:a@reports.example.com,mailto:b@reports.example.com,mailto:c@reports.example.com; ruf=mailto:a@forensic.example.com;'
DMARC_WARNING='Recommendation: More than two rua destinations are configured. Some DMARC reporters may skip additional destinations.'
SPF_WARNING='Action recommended: direct.example.com uses an a mechanism but has no A/AAAA records. Remove the ineffective mechanism or publish the intended address record.'


def result(kind='dmarc',warning=DMARC_WARNING,record=DMARC_RECORD,status='warn'):
    return {'status':status,'message':'Valid result.','warnings':[warning],'raw':{'record':record}}

class Release120Tests(Base):
    def row(self,**changes):
        self.auth(); self.add()
        with m.db() as c:
            sets=','.join(k+'=?' for k in changes)
            if changes: c.execute('UPDATE domains SET '+sets+' WHERE domain=?',(*changes.values(),'example.com'))
            return dict(c.execute("SELECT * FROM domains WHERE domain='example.com'").fetchone())

    def test_schema_defaults_and_backup_compatibility(self):
        row=self.row()
        self.assertEqual((row['approved_spf'],row['approved_dmarc'],row['approval_note']),('','',''))
        with m.db() as c:
            self.assertTrue({'approved_spf','approved_dmarc','approval_note'} <= {r[1] for r in c.execute('PRAGMA table_info(domains)')})

    def test_exact_dmarc_fragment_changes_warn_to_pass(self):
        fragment='rua=mailto:a@reports.example.com,mailto:b@reports.example.com,mailto:c@reports.example.com; ruf=mailto:a@forensic.example.com;'
        item=m.apply_approved_exceptions('dmarc',result(),fragment,'Intentional reporting layout')
        self.assertEqual(item['status'],'pass'); self.assertEqual(item['technical_status'],'warn')
        self.assertEqual(item['warnings'],[]); self.assertEqual(len(item['approved_warnings']),1)
        self.assertIn('Manually approved exception',item['manual_approval_message'])

    def test_changed_record_stops_matching(self):
        fragment='rua=mailto:a@reports.example.com,mailto:b@reports.example.com,mailto:c@reports.example.com;'
        item=m.apply_approved_exceptions('dmarc',result(record='v=DMARC1; p=quarantine; rua=mailto:a@reports.example.com,mailto:b@reports.example.com;'),fragment)
        self.assertEqual(item['status'],'warn'); self.assertFalse(item.get('approved_warnings'))

    def test_added_rua_address_stops_matching(self):
        fragment='rua=mailto:a@reports.example.com,mailto:b@reports.example.com,mailto:c@reports.example.com;'
        grown=DMARC_RECORD.replace('mailto:c@reports.example.com;','mailto:c@reports.example.com,mailto:d@reports.example.com;',1)
        item=m.apply_approved_exceptions('dmarc',result(record=grown),fragment)
        self.assertEqual(item['status'],'warn')

    def test_case_and_whitespace_do_not_break_an_exact_match(self):
        fragment=' RUA=mailto:a@reports.example.com,mailto:b@reports.example.com,mailto:c@reports.example.com ; '
        item=m.apply_approved_exceptions('dmarc',result(),fragment)
        self.assertEqual(item['status'],'pass')

    def test_unrelated_fragment_cannot_approve_warning(self):
        item=m.apply_approved_exceptions('dmarc',result(),'p=quarantine;')
        self.assertEqual(item['status'],'warn'); self.assertEqual(item['warnings'],[DMARC_WARNING])

    def test_fail_and_unknown_never_become_pass(self):
        for status in ('fail','unknown'):
            item=m.apply_approved_exceptions('dmarc',result(status=status),'rua=mailto:a@reports.example.com;')
            self.assertEqual(item['status'],status)

    def test_spf_a_fragment(self):
        raw='v=spf1 include:_spf.provider.example.net +a +mx -all'
        item=m.apply_approved_exceptions('spf',result('spf',SPF_WARNING,raw),'+a','Accepted temporarily')
        self.assertEqual(item['status'],'pass'); self.assertEqual(item['approved_warnings'][0]['fragment'],'+a')
        self.assertIn('Ineffective SPF a mechanism',item['warning_details'][0]['title'])
        self.assertIn('MX authorization is separate',item['warning_details'][0]['evidence'])

    def test_external_spf_warning_matches_the_right_include(self):
        warning='External provider: _spf.provider.example.net uses an a mechanism but has no A/AAAA records. The included SPF provider must correct this record.'
        raw='v=spf1 include:_spf.other.example.net include:_spf.provider.example.net -all'
        wrong=m.apply_approved_exceptions('spf',result('spf',warning,raw),'include:_spf.other.example.net')
        right=m.apply_approved_exceptions('spf',result('spf',warning,raw),'include:_spf.provider.example.net')
        self.assertEqual(wrong['status'],'warn')
        self.assertEqual(right['status'],'pass')

    def test_all_warnings_must_be_approved(self):
        item=result(); item['warnings']=[DMARC_WARNING,'Fixture warning']
        item=m.apply_approved_exceptions('dmarc',item,'rua=mailto:a@reports.example.com,mailto:b@reports.example.com,mailto:c@reports.example.com;')
        self.assertEqual(item['status'],'warn'); self.assertEqual(item['warnings'],['Fixture warning'])
        self.assertEqual(len(item['approved_warnings']),1)

    def test_edit_persists_and_validates_fields(self):
        row=self.row(); ident=row['id']
        r=self.post(f'/domain/{ident}/edit',domain='example.com',label='',selectors='selector1',policy='quarantine',
                    approved_spf='+a\n+a',approved_dmarc='rua=mailto:a@reports.example.com;',approval_note='<script>accepted</script>')
        self.assertEqual(r.status_code,302)
        with m.db() as c: saved=dict(c.execute('SELECT * FROM domains WHERE id=?',(ident,)).fetchone())
        self.assertEqual(saved['approved_spf'],'+a'); self.assertEqual(saved['approval_note'],'<script>accepted</script>')
        page=self.client.get(f'/domain/{ident}/edit').data
        self.assertNotIn(b'<script>accepted</script>',page)
        r=self.post(f'/domain/{ident}/edit',domain='example.com',label='',selectors='selector1',policy='quarantine',approved_spf='\n'.join('x%d'%i for i in range(21)))
        self.assertIn(b'Maximum 20',r.data)

    def test_parent_applies_approval_before_overall_status(self):
        row=self.row(approved_dmarc='rua=mailto:a@reports.example.com,mailto:b@reports.example.com,mailto:c@reports.example.com;',approval_note='Reviewed')
        checked={k:m.res('pass','ok') for k in ('spf','dkim')}; checked['dmarc']=result(); checked.update(dns_evidence={},dns_host={},domain_expiry={})
        with patch.object(m,'isolated_domain',return_value=checked): m.run_domain_check(row,None,False)
        with m.db() as c: data=json.loads(c.execute('SELECT result FROM domains WHERE id=?',(row['id'],)).fetchone()[0])
        self.assertEqual(data['dmarc']['status'],'pass'); self.assertEqual(data['status'],'pass')
        self.assertEqual(data['configuration']['approved_dmarc'],row['approved_dmarc'])

    def test_details_show_disclaimer_original_warning_and_explanation(self):
        row=self.row()
        item=m.apply_approved_exceptions('dmarc',result(),'rua=mailto:a@reports.example.com,mailto:b@reports.example.com,mailto:c@reports.example.com;','Reviewed')
        data={k:m.res('pass','ok') for k in ('spf','dkim')}; data['dmarc']=item; data['status']='pass'; data['trigger']='manual'; data['configuration']={}
        with m.db() as c: c.execute('INSERT INTO history(domain_id,checked,result) VALUES(?,?,?)',(row['id'],time.time(),json.dumps(data)))
        html=self.client.get(f"/domain/{row['id']}").get_data(as_text=True)
        for text in ('Manually approved exception','original warnings remain visible','Approved:',DMARC_WARNING,'What is wrong and how to fix it','Matched record section','Reviewed'):
            self.assertIn(text,html)
        self.assertNotIn('<script>accepted</script>',html)

    def test_history_fingerprint_includes_approvals(self):
        a={'dmarc':m.apply_approved_exceptions('dmarc',result(),'rua=mailto:a@reports.example.com,mailto:b@reports.example.com,mailto:c@reports.example.com;')}
        b={'dmarc':result()}
        self.assertNotEqual(m.history_fingerprint(a),m.history_fingerprint(b))

if __name__=='__main__': unittest.main(verbosity=2)
