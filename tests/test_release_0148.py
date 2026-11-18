import unittest
from unittest.mock import patch

import app as m


EXTERNAL_WARNING = (
    "Error when processing _spf.provider.example.net: An a mechanism points to "
    "_spf.provider.example.net, but that domain/subdomain does not have any A/AAAA records."
)

FRIENDLY_WARNING = (
    "External SPF warning: _spf.provider.example.net uses an a mechanism but has no "
    "A/AAAA records. This issue is with the included SPF provider."
)


class Release0148Tests(unittest.TestCase):
    def test_external_spf_a_warning_is_clearer(self):
        self.assertEqual(
            m.friendly_spf_warning(EXTERNAL_WARNING),
            FRIENDLY_WARNING,
        )

    def test_unrelated_spf_warning_is_unchanged(self):
        warning = "SPF record contains a mechanism after the all mechanism."
        self.assertEqual(m.friendly_spf_warning(warning), warning)

    def test_similar_unmatched_warning_is_unchanged(self):
        warning = (
            "An a mechanism points to example.com, but that domain/subdomain "
            "does not have any A/AAAA records."
        )
        self.assertEqual(m.friendly_spf_warning(warning), warning)

    @patch("checkdmarc.spf.check_spf")
    def test_record_check_rewrites_external_warning(self, check_spf):
        check_spf.return_value = {
            "valid": True,
            "record": (
                "v=spf1 include:spf.protection.outlook.com "
                "include:_spf.provider.example.net -all"
            ),
            "dns_lookups": 3,
            "warnings": [EXTERNAL_WARNING],
            "parsed": {"all": "fail"},
        }

        result = m.record_check("spf", "customer.example.com", "reject")

        self.assertEqual(result["status"], "warn")
        self.assertEqual(result["message"], "Valid SPF; DNS lookups: 3")
        self.assertEqual(result["warnings"], [FRIENDLY_WARNING])



if __name__ == "__main__":
    unittest.main(verbosity=2)
