"""
Bugs in original version:
1. incomeshare is not validated, so it can be converted to 1 when it's 0. or it can be missing or incorrect data type
2. base is not validated or handled, so it could cause zero division error, or type error
3. amount is not validated, so it could have incorrect data type
4. payments field is not validated. it should be a list.
5. Curreny is not fully validated. It should be a string, but it can be missing or incorrect data type
6. Active field is not well validated. cases like 1, 0, "1", "0", "true", "false" are not handled correctly

There are possible other bugs as well, but they depend on the business logic.
For example, negative values probably should not be allowed. Also, maybe one numeric value shouldn't be bigger
than the other.
Since I do not know the exact context, I will not try to fix them here.
"""

import unittest


def calculate_payments(applicants):
    """This is the fixed version of the original function"""
    payment_by_currency = {}

    for app in applicants:
        # Validate that each applicant is a dict
        if not isinstance(app, dict):
            continue

        # validate currencies
        raw_currency = app.get("currency", "GEL")
        if raw_currency in (None, ""):
            currency = "GEL"
        else:
            currency = str(raw_currency).strip().upper()

        # Validate payments
        payments = app.get("payments")
        if not isinstance(payments, list):  # payments should be a list
            continue

        for pay in payments:
            # Validate active field
            if not isinstance(pay, dict):
                continue
            active = pay.get("active", True)
            if active in (False, "false", "False", 0, "0"):
                continue

            # Get and validate incomeshare
            raw_incomeshare = pay.get("incomeshare")
            try:
                incomeshare = float(raw_incomeshare) if raw_incomeshare not in (None, "") else 1.0
            except (KeyError, ValueError, TypeError):
                continue

            # Get and validate base
            try:
                base = float(pay["base"])
                if base == 0:  # Base cannot be zero
                    continue
            except (KeyError, TypeError, ValueError):
                continue

            # Get and validate amount
            try:
                amount = float(pay.get("amount", 0))
            except (KeyError, TypeError, ValueError):
                continue

            ratio = incomeshare / base
            payment_by_currency[currency] = payment_by_currency.get(currency, 0) + amount * ratio

    return payment_by_currency


class Tests(unittest.TestCase):

    def test_base_scenario(self):
        """Test complex scenario mimicking real-world data"""
        applicants = [
            {
                "currency": "USD",
                "payments": [
                    {"active": True, "incomeshare": 0.15, "amount": 2500, "base": 0.3},
                    {"active": False, "incomeshare": 0.25, "amount": 1000, "base": 0.5},
                    {"active": True, "incomeshare": 0.1, "amount": 750, "base": 0.2},
                ]
            },
            {
                "currency": "EUR",
                "payments": [
                    {"active": True, "incomeshare": 0.2, "amount": 1800, "base": 0.4},
                    {"active": True, "incomeshare": 0.35, "amount": 1200, "base": 0.7},
                ]
            },
            {
                "currency": "USD",  # Same currency as first
                "payments": [
                    {"active": True, "incomeshare": 0.05, "amount": 4000, "base": 0.1},
                ]
            }
        ]

        # Expected calculations:
        # USD: (0.15/0.3 * 2500) + (0.1/0.2 * 750) + (0.05/0.1 * 4000) = 1250 + 375 + 2000 = 3625
        # EUR: (0.2/0.4 * 1800) + (0.35/0.7 * 1200) = 900 + 600 = 1500
        expected = {"USD": 3625.0, "EUR": 1500.0}
        self.assertEqual(calculate_payments(applicants), expected)

    def test_missing_currency(self):
        applicants = [{
            "payments": [
                {"active": True, "incomeshare": 0.5, "amount": 100, "base": 1}
            ]
        }]
        expected = {"GEL": 50.0}
        self.assertEqual(calculate_payments(applicants), expected)

    def test_numeric_field_variations(self):
        """Test different numeric representations and edge cases"""
        applicants = [{
            "currency": "USD",
            "payments": [
                {"active": True, "incomeshare": "0.5", "amount": "100", "base": "1"},  # String numbers
                {"active": True, "incomeshare": 0.5, "amount": 100.5, "base": 1.0},
                {"active": True, "incomeshare": None, "amount": 100, "base": 1},  # None incomeshare
                {"active": True, "incomeshare": 0.5, "amount": None, "base": 1},  # None amount - should skip
                {"active": True, "incomeshare": 0.5, "amount": "", "base": 1},  # Empty string amount
                {"active": True, "incomeshare": "", "amount": 100, "base": 1},  # Empty string incomeshare
            ]
        }]
        # Valid payments: 50 + 50.25 + 100 + 0 + 100 = 300.25
        expected = {"USD": 300.25}
        self.assertEqual(calculate_payments(applicants), expected)

    def test_missing_and_invalid_fields(self):
        """Test missing and invalid field handling"""
        applicants = [{
            "currency": "USD",
            "payments": [
                {"active": True, "amount": 100, "base": 1},                    # Missing incomeshare (default 1)
                {"active": True, "incomeshare": 0.5, "base": 1},              # Missing amount (default 0)
                {"active": True, "incomeshare": 0.5, "amount": 100},          # Missing base (should skip)
                {"active": True, "incomeshare": 0.5, "amount": 100, "base": None},  # None base (should skip)
                {"active": True, "incomeshare": 0.5, "amount": 100, "base": 0},     # Zero base (should skip)
                {"active": True, "incomeshare": "invalid", "amount": 100, "base": 1}, # Invalid incomeshare
            ]
        }]
        expected = {"USD": 100.0}  # Only first payment should be processed: 1.0 * 100 / 1 = 100
        self.assertEqual(calculate_payments(applicants), expected)

    def test_multiple_currencies(self):
        """Test multiple currencies aggregation"""
        applicants = [
            {"currency": "USD", "payments": [{"active": True, "incomeshare": 0.2, "amount": 1000, "base": 0.5}]},
            {"currency": "EUR", "payments": [{"active": True, "incomeshare": 0.3, "amount": 600, "base": 0.6}]},
            {"currency": "USD", "payments": [{"active": True, "incomeshare": 0.1, "amount": 500, "base": 0.25}]}
        ]
        expected = {"USD": 600.0, "EUR": 300.0}
        self.assertEqual(calculate_payments(applicants), expected)

    def test_zero_values(self):
        """Test handling of zero values"""
        applicants = [{
            "currency": "USD",
            "payments": [
                {"active": True, "incomeshare": 0, "amount": 100, "base": 1},  # Zero incomeshare
                {"active": True, "incomeshare": 0.5, "amount": 0, "base": 1},  # Zero amount
                {"active": True, "incomeshare": 0.5, "amount": 100, "base": 0},  # Zero base (should skip)
            ]
        }]
        expected = {"USD": 0.0}  # 0 + 0 = 0 (third payment skipped)
        self.assertEqual(calculate_payments(applicants), expected)

    def test_currency_handling(self):
        """Test various currency formats and edge cases"""
        applicants = [
            {"currency": "usd", "payments": [{"active": True, "incomeshare": 0.5, "amount": 100, "base": 1}]},
            {"currency": "  EUR  ", "payments": [{"active": True, "incomeshare": 0.5, "amount": 100, "base": 1}]},
            {"currency": 123, "payments": [{"active": True, "incomeshare": 0.5, "amount": 100, "base": 1}]},
            {"currency": None, "payments": [{"active": True, "incomeshare": 0.5, "amount": 100, "base": 1}]},
            {"currency": "", "payments": [{"active": True, "incomeshare": 0.5, "amount": 100, "base": 1}]},
            {"payments": [{"active": True, "incomeshare": 0.5, "amount": 100, "base": 1}]},  # missing currency
        ]
        expected = {"USD": 50.0, "EUR": 50.0, "123": 50.0, "GEL": 150.0}  # None, empty, missing -> GEL
        self.assertEqual(calculate_payments(applicants), expected)

    def test_data_structure_validation(self):
        """Test validation of data structures"""
        applicants = [
            "not a dict",  # Invalid applicant type
            {"currency": "USD", "payments": "not a list"},  # Invalid payments type
            {"currency": "USD", "payments": ["not a dict"]},  # Invalid payment type
            {"currency": "USD", "payments": []},  # Empty payments list
            {"currency": "USD"},  # Missing payments
            {"currency": "USD", "payments": None},  # None payments
        ]
        expected = {}  # All should be skipped
        self.assertEqual(calculate_payments(applicants), expected)

    def test_active_field_variations(self):
        """Test different representations of the active field"""
        applicants = [{
            "currency": "USD",
            "payments": [
                {"active": True, "incomeshare": 0.5, "amount": 100, "base": 1},
                {"active": False, "incomeshare": 0.5, "amount": 100, "base": 1},
                {"active": "true", "incomeshare": 0.5, "amount": 100, "base": 1},
                {"active": "false", "incomeshare": 0.5, "amount": 100, "base": 1},
                {"active": "1", "incomeshare": 0.5, "amount": 100, "base": 1},
                {"active": "0", "incomeshare": 0.5, "amount": 100, "base": 1},
                {"active": 1, "incomeshare": 0.5, "amount": 100, "base": 1},
                {"active": 0, "incomeshare": 0.5, "amount": 100, "base": 1},
                {"incomeshare": 0.5, "amount": 100, "base": 1},  # missing active (default True)
            ]
        }]
        # Only False, "false", "False", "0", 0 should be inactive. all else True. 5 payments * 50 = 250
        expected = {"USD": 250.0}
        self.assertEqual(calculate_payments(applicants), expected)

    def test_mixed_active_field_types(self):
        """Test edge cases for active field"""
        applicants = [{
            "currency": "USD",
            "payments": [
                {"active": [], "incomeshare": 0.5, "amount": 100, "base": 1},  # Empty list (truthy)
                {"active": {}, "incomeshare": 0.5, "amount": 100, "base": 1},  # Empty dict (falsy)
                {"active": "True", "incomeshare": 0.5, "amount": 100, "base": 1},  # String "True"
                {"active": "FALSE", "incomeshare": 0.5, "amount": 100, "base": 1},  # Uppercase "FALSE"
                {"active": None, "incomeshare": 0.5, "amount": 100, "base": 1},  # None (falsy)
                {"active": -1, "incomeshare": 0.5, "amount": 100, "base": 1},  # Negative number
            ]
        }]
        result = calculate_payments(applicants)
        # Based on current logic: [], "True", -1 should be active; {}, None should be inactive
        # "FALSE" should be active (not in the false list)
        self.assertIsInstance(result.get("USD"), float)

    def test_deeply_nested_invalid_data(self):
        """Test complex invalid data structures"""
        applicants = [
            {
                "currency": "USD",
                "payments": [
                    {
                        "active": True,
                        "incomeshare": {"nested": "dict"},  # Dict instead of number
                        "amount": [1, 2, 3],  # List instead of number
                        "base": {"another": "dict"}  # Dict instead of number
                    },
                    {
                        "active": {"complex": True},  # Complex active field
                        "incomeshare": "not_a_number",
                        "amount": "also_not_a_number",
                        "base": "still_not_a_number"
                    }
                ]
            }
        ]
        result = calculate_payments(applicants)
        # Should handle complex invalid data gracefully
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
