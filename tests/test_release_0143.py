import importlib.util,stat,subprocess,sys,tempfile,unittest
from pathlib import Path
from test_app import Base
SCRIPT='/app/scripts/tune_resources.py'
spec=importlib.util.spec_from_file_location('tune_resources',SCRIPT)
tune=importlib.util.module_from_spec(spec); spec.loader.exec_module(tune)
GIB=1024**3
ENV="""SECRET_KEY='test-only'
ADMIN_PASSWORD_HASH='scrypt:32768:8:1$salt$hash'
HOST_BIND_IP='192.0.2.10'
HOST_PORT='8282'
CHECK_WORKERS='4'
CONTAINER_CPUS='4'
DOMAIN_MONITOR_VERSION='0.0.0'
"""
class Release0143Tests(Base):
    def run_tool(self,text,cpus,memory,*extra,runs=1):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'.env'; path.write_text(text); path.chmod(0o600)
            for _ in range(runs):
                result=subprocess.run([sys.executable,SCRIPT,'--env',str(path),'--cpus',str(cpus),'--mem',str(memory),*extra],capture_output=True,text=True,timeout=30)
            backups=[p.name for p in Path(folder).glob('.env.backup-tune-*')]
            return result,path.read_text(),stat.S_IMODE(path.stat().st_mode),backups
    def test_recommendations_fit_the_host(self):
        cases={(1,8*GIB):('1','2'),(2,2*GIB):('2','2'),(2,8*GIB):('2','4'),(3,8*GIB):('3','4'),(4,16*GIB):('4','4'),(32,128*GIB):('4','4')}
        for (cpus,memory),expected in cases.items():
            r=tune.recommend(cpus,memory)
            self.assertEqual((r['CONTAINER_CPUS'],r['CHECK_WORKERS']),expected,(cpus,memory))
    def test_too_many_cpus_is_fixed_and_other_settings_kept(self):
        result,text,mode,backups=self.run_tool(ENV,2,8*GIB)
        self.assertEqual(result.returncode,3,result.stderr)
        self.assertIn("CONTAINER_CPUS='2'",text)
        self.assertIn("RESOURCE_TUNING='auto'",text)
        for line in ENV.splitlines():
            if not line.startswith('CONTAINER_CPUS='): self.assertIn(line,text)
        self.assertEqual(mode,0o600); self.assertEqual(len(backups),1)
    def test_second_run_changes_nothing(self):
        result,text,_,backups=self.run_tool(ENV,2,8*GIB,runs=2)
        self.assertEqual(result.returncode,0)
        self.assertIn('already fit',result.stdout); self.assertEqual(len(backups),1)
    def test_manual_mode_keeps_values_but_caps_cpus(self):
        manual=ENV.replace("CHECK_WORKERS='4'","CHECK_WORKERS='7'")+"RESOURCE_TUNING='manual'\n"
        result,text,_,_=self.run_tool(manual,8,32*GIB)
        self.assertEqual(result.returncode,0); self.assertIn("CHECK_WORKERS='7'",text); self.assertIn("CONTAINER_CPUS='4'",text)
        result,text,_,_=self.run_tool(manual,2,32*GIB)
        self.assertEqual(result.returncode,3); self.assertIn("CONTAINER_CPUS='2'",text); self.assertIn("CHECK_WORKERS='7'",text)
    def test_dry_run_writes_nothing(self):
        result,text,_,backups=self.run_tool(ENV,1,1*GIB,'--dry-run')
        self.assertEqual(result.returncode,0); self.assertEqual(text,ENV); self.assertEqual(backups,[])
        self.assertIn('4 -> 1',result.stdout)
    def test_setup_and_update_scripts_run_the_tuner(self):
        runner=Path('/app/scripts/tune-resources.sh')
        self.assertTrue(runner.stat().st_mode & stat.S_IXOTH)
        self.assertIn('NCPU',runner.read_text())
        update=Path('/app/scripts/update.sh').read_text()
        call=update.index('tune-resources.sh" --no-restart')
        self.assertLess(update.index('git checkout -f "$TARGET_TAG"'),call)
        self.assertLess(call,update.index('compose config --quiet\nFAILED_STEP'))
        password=Path('/app/scripts/set-admin-password.sh').read_text()
        self.assertLess(password.index('tune-resources.sh'),password.index('docker compose run'))
        self.assertNotIn('cat > .env.new',password)
        self.assertIn('not in updates',password)
        self.assertIn("RESOURCE_TUNING='auto'",Path('/app/.env.example').read_text())
        self.assertIn('tune-resources.sh',Path('/app/README.md').read_text())
if __name__=='__main__': unittest.main(verbosity=2)
