import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CheckProgressInitialRenderTests(unittest.TestCase):
    def test_active_batch_controls_initial_hidden_state(self):
        base = (ROOT / "templates" / "base.html").read_text()

        self.assertIn(
            "check_batch.status in ('active','stalled')",
            base,
        )
        self.assertIn(
            "{% if not (check_batch is defined and check_batch",
            base,
        )

    def test_active_batch_initial_title_is_rendered(self):
        base = (ROOT / "templates" / "base.html").read_text()

        self.assertIn(
            "{{ check_batch.done }} / "
            "{{ check_batch.total }} complete",
            base,
        )

    def test_active_batch_initial_progress_value_is_rendered(self):
        base = (ROOT / "templates" / "base.html").read_text()

        self.assertIn(
            "{{ check_batch.percent }}",
            base,
        )

    def test_active_batch_initial_detail_is_rendered(self):
        base = (ROOT / "templates" / "base.html").read_text()

        self.assertIn(
            "{{ check_batch.queued }} queued",
            base,
        )
        self.assertIn(
            "{{ check_batch.running }} checking",
            base,
        )
        self.assertIn(
            "{{ check_batch.failed }} failed",
            base,
        )

    def test_cancel_form_is_visible_only_for_active_batch(self):
        base = (ROOT / "templates" / "base.html").read_text()

        self.assertIn(
            'check_batch.status == "active"',
            base,
        )
        self.assertIn(
            'id="cancel-check-all"',
            base,
        )

    def test_progress_script_still_polls_status_endpoint(self):
        script = (ROOT / "static" / "check-progress.js").read_text()

        self.assertIn(
            'fetch("/check-all/status"',
            script,
        )
        self.assertIn(
            'data.status === "active"',
            script,
        )
        self.assertIn(
            'data.status === "stalled"',
            script,
        )

    def test_data_directory_is_not_part_of_candidate(self):
        self.assertFalse((ROOT / "data").exists())


if __name__ == "__main__":
    unittest.main()
