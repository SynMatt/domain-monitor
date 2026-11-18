import unittest
from unittest.mock import patch

import app as m

EXTERNAL_WARNING = (
    "Error when processing _spf.provider.example.net: An a mechanism points to "
    "_spf.provider.example.net, but that domain/subdomain does not have any A/AAAA records."
)


def included_record():
    return {
        "valid": True,
        "record": "v=spf1 include:_spf.provider.example.net -all",
        "dns_lookups": 3,
        "warnings": [EXTERNAL_WARNING],
        "parsed": {
            "all": "fail",
            "mechanisms": [
                {"mechanism": "include", "value": "_spf.provider.example.net", "parsed": {"mechanisms": []}}
            ],
        },
    }


class Release0148Tests(unittest.TestCase):
    def test_included_spf_a_warning_names_the_external_provider(self):
        result = m.friendly_spf_warning("customer.example.com", EXTERNAL_WARNING, included_record())
        self.assertTrue(result.startswith("External provider:"))
        self.assertIn("_spf.provider.example.net", result)

    def test_unrelated_spf_warning_is_unchanged(self):
        warning = "SPF record contains a mechanism after the all mechanism."
        self.assertEqual(m.friendly_spf_warning("example.com", warning, included_record()), warning)

    def test_similar_unmatched_warning_is_unchanged(self):
        warning = (
            "An a mechanism points to example.com, but that domain/subdomain "
            "does not have any A/AAAA records."
        )
        self.assertEqual(m.friendly_spf_warning("example.com", warning, included_record()), warning)

    @patch("checkdmarc.spf.check_spf")
    def test_record_check_marks_included_warning_as_external(self, check_spf):
        check_spf.return_value = included_record()
        result = m.record_check("spf", "customer.example.com", "reject")
        self.assertEqual(result["status"], "warn")
        self.assertEqual(result["message"], "Valid SPF; DNS lookups: 3")
        self.assertTrue(result["warnings"][0].startswith("External provider:"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
