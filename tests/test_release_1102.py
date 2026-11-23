import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DashboardRefreshProtectionTests(unittest.TestCase):
    def script(self):
        return (
            ROOT / "static" / "card-status.js"
        ).read_text()

    def test_uses_global_progress_panel_id(self):
        script = self.script()

        self.assertIn(
            "getElementById(\n"
            "      'global-check-progress'",
            script,
        )

        self.assertNotIn(
            "getElementById('check-progress')",
            script,
        )

    def test_reload_is_blocked_during_check_all(self):
        script = self.script()

        self.assertIn(
            "if (stopped || batchActive() || "
            "userIsInteracting())",
            script,
        )

    def test_reload_is_blocked_while_controls_have_focus(self):
        script = self.script()

        self.assertIn(
            "dashboardControls.contains(active)",
            script,
        )

        self.assertIn(
            "controlsInUse() || controlsChanged()",
            script,
        )

    def test_unapplied_search_and_filter_changes_are_detected(self):
        script = self.script()

        self.assertIn(
            "new FormData(dashboardControls)",
            script,
        )

        self.assertIn(
            "currentControls !== initialControls",
            script,
        )

    def test_refresh_can_be_deferred(self):
        script = self.script()

        self.assertIn(
            "let refreshDeferred = false",
            script,
        )

        self.assertIn(
            "function tryDeferredReload()",
            script,
        )

    def test_search_input_does_not_reload_page(self):
        script = self.script()

        input_listener = script.index(
            "search.addEventListener("
        )
        input_section = script[
            input_listener:
            input_listener + 500
        ]

        self.assertNotIn(
            "window.location.reload()",
            input_section,
        )

    def test_check_all_completion_retries_deferred_refresh(self):
        script = self.script()

        self.assertIn(
            "'domain-monitor:check-all-complete'",
            script,
        )

        self.assertIn(
            "tryDeferredReload();",
            script,
        )

    def test_runtime_data_is_not_in_candidate(self):
        self.assertFalse((ROOT / "data").exists())
        self.assertFalse((ROOT / ".env").exists())
        self.assertFalse((ROOT / "backups").exists())


if __name__ == "__main__":
    unittest.main()
