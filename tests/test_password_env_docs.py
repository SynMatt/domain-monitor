import unittest
from pathlib import Path
from test_app import Tests
import app as m

class PasswordEnvDocumentationTests(Tests):
    def test_example_values_are_quoted(self):
        text=Path('/app/.env.example').read_text()
        self.assertIn("SECRET_KEY='replace-with-random-64-character-hex-value'", text)
        self.assertIn("ADMIN_PASSWORD_HASH='replace-with-a-werkzeug-password-hash'", text)
    def test_password_script_is_documented(self):
        readme=Path('/app/README.md').read_text()
        self.assertIn('scripts/set-admin-password.sh', readme)
        script=Path('/app/scripts/set-admin-password.sh').read_text()
        self.assertIn('check_password_hash', script)
        self.assertIn('.env.backup-', script)
    def test_version_and_changelog(self):
        self.assertEqual(self.client.get('/health').json['version'],'0.9.4')
        self.assertIn('## 0.9.4 - 2026-11-10',Path('/app/CHANGELOG.md').read_text())

if __name__=='__main__':
    unittest.main(verbosity=2)
