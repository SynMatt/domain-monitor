import importlib.util,logging,os,re,subprocess,sys,tempfile,unittest
from pathlib import Path
from test_app import Base
import app as m
ROOT=Path('/app')
GIB=1024**3
def top_release(text):
    """Return the text of the newest changelog release."""
    parts=re.split(r'^## (?=\d+\.\d+\.\d+ - )',text,flags=re.M)
    return parts[1] if len(parts)>1 else ''
class Release0144Tests(Base):
    def test_readme_reviewed_for_this_release(self):
        readme=(ROOT/'README.md').read_text()
        marker=re.search(r'<!-- README reviewed for release: (\d+\.\d+\.\d+) -->',readme)
        self.assertIsNotNone(marker,'README review marker missing')
        self.assertEqual(marker.group(1),m.APP_VERSION,'README not reviewed for this release: update the README and its marker')
        self.assertLess(marker.start(),readme.index('<!-- BEGIN UPDATE COMMANDS -->'),'marker must sit outside the generated block')
    def test_changelog_says_what_changed_in_readme(self):
        release=top_release((ROOT/'CHANGELOG.md').read_text())
        self.assertTrue(release.startswith(m.APP_VERSION+' - '))
        self.assertIn('README',release,'Newest changelog entry must include a README line')
    def test_user_facing_scripts_are_documented(self):
        readme=(ROOT/'README.md').read_text()
        docs=readme+''.join(p.read_text() for p in (ROOT/'docs').glob('*.md'))
        for name in ('set-admin-password.sh','update.sh','backup.sh','restore.sh','tune-resources.sh','run-tests.sh'):
            self.assertIn(name,readme,f'{name} is not in the README')
        for name in ('monitor-check-all.sh','cleanup-images.sh'):
            self.assertIn(name,docs,f'{name} is not documented')
    def test_readme_covers_recent_releases(self):
        readme=(ROOT/'README.md').read_text()
        for phrase in ('Same result for N checks','Summary only','range of CPUs is from 0.01 to N','Dynamic Memory','DM_TEST_LOGS=1','set automatically to suit the host'):
            self.assertIn(phrase,readme)
    def test_tuner_ignores_memory_on_hyperv(self):
        path=ROOT/'scripts/tune_resources.py'
        spec=importlib.util.spec_from_file_location('tune_resources_0144',path)
        tune=importlib.util.module_from_spec(spec); spec.loader.exec_module(tune)
        self.assertEqual(tune.recommend(2,int(1.5*GIB))['CHECK_WORKERS'],'2')
        self.assertEqual(tune.recommend(2,int(1.5*GIB),ignore_memory=True)['CHECK_WORKERS'],'4')
        self.assertEqual(tune.recommend(1,8*GIB,ignore_memory=True)['CHECK_WORKERS'],'2')
        with tempfile.TemporaryDirectory() as folder:
            env=Path(folder)/'.env'; env.write_text("CONTAINER_CPUS='2'\n")
            result=subprocess.run([sys.executable,str(path),'--env',str(env),'--cpus','2','--mem',str(int(1.5*GIB)),'--ignore-memory','--dry-run'],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('Hyper-V detected',result.stdout); self.assertIn('-> 4',result.stdout)
        shell=(ROOT/'scripts/tune-resources.sh').read_text()
        self.assertIn('hv_balloon',shell); self.assertIn('--ignore-memory',shell)
    def test_expected_test_logs_are_hidden(self):
        if os.environ.get('DM_TEST_LOGS'): self.skipTest('logs requested')
        handlers=logging.getLogger().handlers
        self.assertTrue(handlers)
        self.assertTrue(all(h.level>logging.CRITICAL for h in handlers))
        self.assertIn('DM_TEST_LOGS',(ROOT/'scripts/run-tests.sh').read_text())
if __name__=='__main__': unittest.main(verbosity=2)
