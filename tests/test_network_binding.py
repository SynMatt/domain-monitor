import unittest
from pathlib import Path
from test_app import Tests

class NetworkBindingTests(Tests):
    def test_compose_uses_safe_environment_defaults(self):
        text=Path('/app/compose.yaml').read_text()
        self.assertIn('${HOST_BIND_IP:-127.0.0.1}',text)
        self.assertIn('${HOST_PORT:-8282}',text)
    def test_env_example_documents_binding(self):
        text=Path('/app/.env.example').read_text()
        self.assertIn("HOST_BIND_IP='127.0.0.1'",text)
        self.assertIn("HOST_PORT='8282'",text)

if __name__=='__main__': unittest.main(verbosity=2)
