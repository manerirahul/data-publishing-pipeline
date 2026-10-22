"""Unit tests for the validation gates. Run: python -m unittest discover tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from validate import validate_records, rule_summary

CONFIG = {
    "validation": {
        "required_fields": ["order_id", "customer_id"],
        "key_fields": ["order_id"],
        "numeric_ranges": {"quantity": [1, 1000]},
        "domains": {"state": ["TX", "CA"]},
        "date_fields": {"order_date": "%Y-%m-%d"},
    }
}

GOOD = {"order_id": "1", "customer_id": "C1", "quantity": "2",
        "state": "TX", "order_date": "2026-09-01"}


class TestValidate(unittest.TestCase):
    def test_good_record_passes(self):
        valid, rejects = validate_records([GOOD], CONFIG)
        self.assertEqual(len(valid), 1)
        self.assertEqual(rejects, [])

    def test_missing_required_is_quarantined(self):
        bad = dict(GOOD, customer_id="")
        valid, rejects = validate_records([bad], CONFIG)
        self.assertEqual(valid, [])
        self.assertIn("MISSING_REQUIRED:customer_id", rejects[0]["reject_reason"])

    def test_duplicate_key_flagged_on_second_occurrence(self):
        valid, rejects = validate_records([GOOD, dict(GOOD)], CONFIG)
        self.assertEqual(len(valid), 1)
        self.assertIn("DUPLICATE_KEY", rejects[0]["reject_reason"])

    def test_out_of_range_and_domain(self):
        bad = dict(GOOD, quantity="-3", state="ZZ")
        _, rejects = validate_records([bad], CONFIG)
        summary = rule_summary(rejects)
        self.assertEqual(summary.get("OUT_OF_RANGE"), 1)
        self.assertEqual(summary.get("DOMAIN_VIOLATION"), 1)

    def test_bad_date(self):
        bad = dict(GOOD, order_date="09/01/2026")
        _, rejects = validate_records([bad], CONFIG)
        self.assertIn("BAD_DATE", rejects[0]["reject_reason"])


if __name__ == "__main__":
    unittest.main()
