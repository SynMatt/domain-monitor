import unittest
import app

class Release182Tests(unittest.TestCase):
    def test_recent_changes_uses_registry_utc_date(self):
        older = {"domain_expiry": {"expires_at": None}}
        newer = {"domain_expiry": {"expires_at": 1804546186.0}}

        changes = app.history_change_details(newer, older)

        self.assertEqual(changes[0]["label"], "Expiry date available again")
        self.assertEqual(changes[0]["before"], "Unknown expiry")
        self.assertEqual(changes[0]["after"], "08 Mar 2027")

if __name__ == "__main__":
    unittest.main()
