import unittest
from pathlib import Path
from test_app import Tests

class UpdaterDriftTests(Tests):
    def test_version(self):
        self.assertEqual(self.client.get('/health').json['version'], '0.11.4')

    def test_update_compares_source_running_and_target(self):
        text=Path('/app/scripts/update.sh').read_text()
        for expected in ('SOURCE_VERSION=', 'RUNNING_VERSION=', 'source/container drift detected'):
            self.assertIn(expected, text)

    def test_update_persists_image_and_binding(self):
        text=Path('/app/scripts/update.sh').read_text()
        for expected in ('DOMAIN_MONITOR_VERSION', 'HOST_BIND_IP', 'HOST_PORT', 'compose config --images', 'compose port web 8080'):
            self.assertIn(expected, text)

if __name__ == '__main__':
    unittest.main(verbosity=2)
