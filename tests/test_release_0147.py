import re,unittest
from pathlib import Path
from test_app import Base
class Release0147Tests(Base):
    def setUp(self):
        super().setUp()
        text=Path('/app/README.md').read_text()
        self.body=text[:text.index('<!-- BEGIN UPDATE COMMANDS -->')]
    def test_manual_example_sticks(self):
        example=self.body[self.body.index('Example for a larger host'):]
        example=example[:example.index('```',example.index('```')+3)]
        self.assertIn("RESOURCE_TUNING='manual'",example)
    def test_configuration_example_marks_values_as_automatic(self):
        example=self.body[self.body.index("HOST_BIND_IP='127.0.0.1'"):]
        example=example[:example.index('```')]
        self.assertIn("RESOURCE_TUNING='auto'",example)
        self.assertIn('Set automatically by the tuner',example)
        self.assertLess(example.index('Set automatically'),example.index('CONTAINER_CPUS='))
    def test_details_page_described(self):
        for text in ('Summary tiles','Current status','what changed since the entry before it'):
            self.assertIn(text,self.body)
    def test_no_release_notes_in_readme_body(self):
        self.assertEqual(re.findall(r'(?:Since|From) (?:version )?0\.14\.[1-9]',self.body),[])
if __name__=='__main__': unittest.main(verbosity=2)
