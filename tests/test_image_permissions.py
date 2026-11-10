import os
import unittest
from pathlib import Path
from test_app import Tests

class ImagePermissionTests(Tests):
    def test_version(self):
        self.assertEqual(self.client.get('/health').json['version'],'0.10.5')

    def test_test_files_are_world_readable(self):
        for path in Path('/app/tests').glob('test_*.py'):
            self.assertTrue(path.stat().st_mode & 0o004, str(path))

    def test_final_chmod_follows_test_copy(self):
        lines=Path('/app/Dockerfile').read_text().splitlines()
        copy_index=max(i for i,line in enumerate(lines) if line.startswith('COPY tests '))
        chmod_index=max(i for i,line in enumerate(lines) if line.strip()=='RUN chmod -R a+rX /app')
        self.assertGreater(chmod_index,copy_index)

if __name__=='__main__': unittest.main(verbosity=2)
