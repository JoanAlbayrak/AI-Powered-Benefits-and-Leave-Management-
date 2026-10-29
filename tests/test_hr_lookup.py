"""Run with:  python3 -m unittest"""

import unittest

from benefits_leave.hr_lookup import lookup_employee_leave_balance as lookup


class RealZeroIsNotAnError(unittest.TestCase):
    def test_zero_balance_is_ok(self):
        result = lookup("E1002")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["facts"]["leave_balance"]["value"], 0)
        self.assertEqual(result["facts"]["leave_balance"]["units"], "hours")
        self.assertIn("as_of", result)

    def test_normal_employee(self):
        result = lookup("E1001")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["facts"]["hours_worked_12mo"]["value"], 1850)
        for fact in result["facts"].values():
            self.assertIn("source", fact)
            self.assertIn("units", fact)


class ErrorsAreNeverZero(unittest.TestCase):
    def assert_error(self, result, reason):
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], reason)
        # The key safety rule: an error carries no numbers at all.
        self.assertNotIn("facts", result)
        self.assertNotIn("balance", result)

    def test_unknown_id(self):
        self.assert_error(lookup("E9999"), "not_found")

    def test_name_instead_of_id(self):
        self.assert_error(lookup("Maria Lopez"), "invalid_employee_id")

    def test_timeout(self):
        def slow_hr_system():
            raise TimeoutError
        self.assert_error(lookup("E1001", fetch=slow_hr_system), "timeout")

    def test_hr_system_down(self):
        def broken_hr_system():
            raise ConnectionError
        self.assert_error(lookup("E1001", fetch=broken_hr_system), "hr_system_unavailable")

    def test_balance_not_a_number(self):
        self.assert_error(lookup("E1004"), "bad_data")

    def test_balance_missing(self):
        self.assert_error(lookup("E1005"), "bad_data")


if __name__ == "__main__":
    unittest.main()
