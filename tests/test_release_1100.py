import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def current_version():
    source = (ROOT / "app.py").read_text()
    match = re.search(
        r"^APP_VERSION\s*=\s*([\"'][^\"']+[\"'])",
        source,
        re.MULTILINE,
    )
    if not match:
        raise AssertionError("APP_VERSION was not found in app.py")
    return ast.literal_eval(match.group(1))


class GlobalCheckProgressTests(unittest.TestCase):
    def test_version_has_matching_changelog_entry(self):
        version = current_version()
        changelog = (ROOT / "CHANGELOG.md").read_text()
        self.assertIn(f"## {version} - ", changelog)

    def test_progress_panel_is_in_shared_base(self):
        base = (ROOT / "templates" / "base.html").read_text()
        self.assertIn('id="global-check-progress"', base)
        self.assertIn('id="check-progress-title"', base)
        self.assertIn('id="check-progress-bar"', base)
        self.assertIn('id="check-progress-detail"', base)
        self.assertIn('id="cancel-check-all"', base)
        self.assertIn(
            '<script src="/static/check-progress.js" defer></script>',
            base,
        )

    def test_dashboard_no_longer_owns_progress_panel(self):
        index = (ROOT / "templates" / "index.html").read_text()
        self.assertNotIn('id="check-progress"', index)
        self.assertNotIn(
            '<script src="/static/check-progress.js" defer></script>',
            index,
        )

    def test_global_script_polls_status_endpoint(self):
        script = (ROOT / "static" / "check-progress.js").read_text()
        self.assertIn('fetch("/check-all/status"', script)
        self.assertIn('data.status === "active"', script)
        self.assertIn('data.status === "stalled"', script)
        self.assertIn("scheduleNextPoll(3000)", script)

    def test_progress_markup_is_authenticated_only(self):
        base = (ROOT / "templates" / "base.html").read_text()
        header_end = base.find("</header>")
        authenticated = base.find(
            "{% if session.get('authenticated') %}",
            header_end,
        )
        progress = base.find('id="global-check-progress"')
        self.assertGreaterEqual(header_end, 0)
        self.assertGreaterEqual(authenticated, 0)
        self.assertGreater(progress, authenticated)

    def test_only_one_global_progress_panel_exists(self):
        count = sum(
            template.read_text().count('id="global-check-progress"')
            for template in (ROOT / "templates").glob("*.html")
        )
        self.assertEqual(count, 1)

    def test_readme_describes_global_progress(self):
        version = current_version()
        readme = (ROOT / "README.md").read_text()
        self.assertIn(
            "cancellation visible on every authenticated page",
            readme,
        )
        self.assertIn(
            f"<!-- README reviewed for release: {version} -->",
            readme,
        )
        self.assertIn(
            f"Latest documented release: **v{version}**",
            readme,
        )


if __name__ == "__main__":
    unittest.main()
