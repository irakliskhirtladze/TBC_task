import pandas as pd
import unittest


class ApplicantDataValidator:
    """Validates and cleans source data, so cleaned data can be used in many functions"""

    REQUIRED_TRANSFER_FIELDS = {'country', 'period', 'amountgel', 'source'}

    def validate_and_clean(self, applicants) -> list:
        """
        Validates and cleans the entire applicants data structure
        Returns only valid, cleaned data ready for processing
        """
        if not isinstance(applicants, list):
            return []

        valid_applicants = []
        for applicant in applicants:
            cleaned_applicant = self._clean_applicant(applicant)
            if cleaned_applicant:
                valid_applicants.append(cleaned_applicant)

        return valid_applicants

    def _clean_applicant(self, applicant) -> dict | None:
        """Clean and validate a single applicant"""
        if not isinstance(applicant, dict):
            return None

        # Validate applicant_id
        applicant_id = applicant.get("applicant_id")
        if not applicant_id or not isinstance(applicant_id, str) or not applicant_id.strip():
            return None

        # Validate transfers
        transfers = applicant.get("transfers")
        if not isinstance(transfers, list) or len(transfers) == 0:
            return None

        # Clean each transfer
        valid_transfers = []
        for transfer in transfers:
            cleaned_transfer = self._clean_transfer(transfer)
            if cleaned_transfer:
                valid_transfers.append(cleaned_transfer)

        # If no valid transfers remain, remove the whole applicant
        if not valid_transfers:
            return None

        return {
            "applicant_id": applicant_id.strip(),
            "transfers": valid_transfers
        }

    def _clean_transfer(self, transfer) -> dict | None:
        """Clean and validate a single transfer"""
        if not isinstance(transfer, dict):
            return None

        # Check all required fields are present
        if not all(field in transfer for field in self.REQUIRED_TRANSFER_FIELDS):
            return None

        cleaned_transfer = {}

        # Clean and validate period - must be convertible to int
        try:
            period_value = transfer['period']
            if isinstance(period_value, str):
                period_value = period_value.strip()

            # Convert to float first to handle string numbers, then to int
            period_float = float(period_value)
            # Only accept whole numbers
            if period_float != int(period_float):
                return None
            cleaned_transfer['period'] = int(period_float)
        except (ValueError, TypeError, OverflowError):
            return None

        # Clean and validate amountgel - must be convertible to float
        try:
            amount_value = transfer['amountgel']
            if isinstance(amount_value, str):
                amount_value = amount_value.strip()
            cleaned_transfer['amountgel'] = float(amount_value)
        except (ValueError, TypeError, OverflowError):
            return None

        # Clean and validate string fields
        for field in ['country', 'source']:
            value = transfer[field]
            if not isinstance(value, str) or not value.strip():
                return None
            cleaned_transfer[field] = value.strip()

        return cleaned_transfer


def process_applicant_transfers(applicants) -> list:
    """
    Process applicant transfers with built-in validation
    """
    # Validate and clean input data
    validator = ApplicantDataValidator()
    clean_applicants = validator.validate_and_clean(applicants)

    if not clean_applicants:  # cannot process empty list
        return []

    # Flatten all transfers with applicant_id
    all_transfers = []
    for applicant in clean_applicants:
        applicant_id = applicant["applicant_id"]
        transfers = applicant["transfers"]

        for transfer in transfers:
            transfer_copy = transfer.copy()
            transfer_copy['applicant_id'] = applicant_id
            all_transfers.append(transfer_copy)

    # Create dataframe and group
    df = pd.DataFrame(all_transfers)
    grouped = df.groupby(['applicant_id', 'country', 'period']).agg({
        'amountgel': 'sum',
        'source': lambda x: '/'.join(sorted(set(x)))
    }).reset_index()

    # Sort by applicant_id, country, and period
    grouped = grouped.sort_values(['applicant_id', 'country', 'period'])

    # Convert back to required format
    output = []
    for applicant_id, group in grouped.groupby('applicant_id'):
        grouped_transfers = group[['country', 'period', 'amountgel', 'source']].to_dict('records')
        output.append({
            "applicant_id": applicant_id,
            "grouped_transfers": grouped_transfers
        })

    # Sort result by applicant_id
    output.sort(key=lambda x: x["applicant_id"])

    return output


class Tests(unittest.TestCase):
    """Test cases for the process_applicant_transfers function."""
    def test_basic_functionality(self):
        """Test basic functionality with sample data."""
        sample_applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": "USA", "period": 1, "amountgel": 100.0, "source": "A"},
                    {"country": "USA", "period": 1, "amountgel": 50.0, "source": "B"},
                    {"country": "GE", "period": 2, "amountgel": 200.0, "source": "M"},
                    {"country": "USA", "period": 2, "amountgel": 75.0, "source": "A"},
                    {"country": "GE", "period": 1, "amountgel": 120.0, "source": "B"},
                ]
            },
            {
                "applicant_id": "APP_002",
                "transfers": [
                    {"country": "UK", "period": 1, "amountgel": 300.0, "source": "C"},
                    {"country": "UK", "period": 1, "amountgel": 100.0, "source": "A"},
                ]
            }
        ]

        expected_output = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "GE", "period": 1, "amountgel": 120.0, "source": "B"},
                    {"country": "GE", "period": 2, "amountgel": 200.0, "source": "M"},
                    {"country": "USA", "period": 1, "amountgel": 150.0, "source": "A/B"},
                    {"country": "USA", "period": 2, "amountgel": 75.0, "source": "A"},
                ]
            },
            {
                "applicant_id": "APP_002",
                "grouped_transfers": [
                    {"country": "UK", "period": 1, "amountgel": 400.0, "source": "A/C"},
                ]
            }
        ]
        result = process_applicant_transfers(sample_applicants)
        self.assertEqual(result, expected_output)

    def test_empty_input(self):
        """Test with empty applicants list."""
        result = process_applicant_transfers([])
        self.assertEqual(result, [])

    def test_empty_transfers(self):
        """Test applicant with no transfers."""
        applicants = [
            {"applicant_id": "APP_001", "transfers": []},
            {"applicant_id": "APP_002", "transfers": None},
            {"applicant_id": "APP_003"}  # Missing transfers key
        ]

        expected = []

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_missing_applicant_id(self):
        """Test applicants with missing or None applicant_id."""
        applicants = [
            {"transfers": [{"country": "USA", "period": 1, "amountgel": 100.0, "source": "A"}]},
            {"applicant_id": None, "transfers": [{"country": "UK", "period": 1, "amountgel": 200.0, "source": "B"}]},
            {"applicant_id": "APP_001",
             "transfers": [{"country": "GE", "period": 1, "amountgel": 300.0, "source": "C"}]}
        ]

        expected = [
            {"applicant_id": "APP_001", "grouped_transfers": [
                {"country": "GE", "period": 1, "amountgel": 300.0, "source": "C"}
            ]}
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_missing_transfer_fields(self):
        """Test transfers with missing required fields."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": "USA", "period": 1, "amountgel": 100.0, "source": "A"},  # Valid
                    {"country": "USA", "period": 1, "amountgel": 50.0},  # Missing source
                    {"country": "USA", "amountgel": 75.0, "source": "B"},  # Missing period
                    {"period": 1, "amountgel": 25.0, "source": "C"},  # Missing country
                    {"country": "USA", "period": 1, "source": "D"},  # Missing amountgel
                    {"country": "GE", "period": 2, "amountgel": 200.0, "source": "E"}  # Valid
                ]
            }
        ]

        expected = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "GE", "period": 2, "amountgel": 200.0, "source": "E"},
                    {"country": "USA", "period": 1, "amountgel": 100.0, "source": "A"}
                ]
            }
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_invalid_data_types(self):
        """Test transfers with invalid data types."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": "USA", "period": "invalid", "amountgel": 100.0, "source": "A"},  # Invalid period
                    {"country": "USA", "period": 1, "amountgel": "invalid", "source": "B"},  # Invalid amount
                    {"country": "USA", "period": 2, "amountgel": 150.0, "source": "C"}  # Valid
                ]
            }
        ]

        expected = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "USA", "period": 2, "amountgel": 150.0, "source": "C"}
                ]
            }
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_none_values(self):
        """Test transfers with None values."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": None, "period": 1, "amountgel": 100.0, "source": "A"},
                    {"country": "USA", "period": None, "amountgel": 50.0, "source": "B"},
                    {"country": "USA", "period": 1, "amountgel": None, "source": "C"},
                    {"country": "USA", "period": 1, "amountgel": 75.0, "source": None},
                    {"country": "GE", "period": 2, "amountgel": 200.0, "source": "D"}  # Valid
                ]
            }
        ]

        expected = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "GE", "period": 2, "amountgel": 200.0, "source": "D"}
                ]
            }
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_duplicate_sources(self):
        """Test that duplicate sources are deduplicated."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": "USA", "period": 1, "amountgel": 100.0, "source": "A"},
                    {"country": "USA", "period": 1, "amountgel": 50.0, "source": "A"},  # Duplicate source
                    {"country": "USA", "period": 1, "amountgel": 75.0, "source": "B"}
                ]
            }
        ]

        expected = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "USA", "period": 1, "amountgel": 225.0, "source": "A/B"}
                ]
            }
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_source_alphabetical_ordering(self):
        """Test that sources are joined in alphabetical order."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": "USA", "period": 1, "amountgel": 100.0, "source": "Z"},
                    {"country": "USA", "period": 1, "amountgel": 50.0, "source": "A"},
                    {"country": "USA", "period": 1, "amountgel": 75.0, "source": "M"}
                ]
            }
        ]

        expected = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "USA", "period": 1, "amountgel": 225.0, "source": "A/M/Z"}
                ]
            }
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_sorting_order(self):
        """Test that results are sorted by country then period."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": "USA", "period": 2, "amountgel": 100.0, "source": "A"},
                    {"country": "GE", "period": 2, "amountgel": 150.0, "source": "B"},
                    {"country": "USA", "period": 1, "amountgel": 200.0, "source": "C"},
                    {"country": "GE", "period": 1, "amountgel": 250.0, "source": "D"}
                ]
            }
        ]

        expected = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "GE", "period": 1, "amountgel": 250.0, "source": "D"},
                    {"country": "GE", "period": 2, "amountgel": 150.0, "source": "B"},
                    {"country": "USA", "period": 1, "amountgel": 200.0, "source": "C"},
                    {"country": "USA", "period": 2, "amountgel": 100.0, "source": "A"}
                ]
            }
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_numeric_type_coercion(self):
        """Test that numeric types are properly handled."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": "USA", "period": "1", "amountgel": "100.5", "source": "A"},  # String numbers
                    {"country": "USA", "period": 1.0, "amountgel": 50, "source": "B"}  # Different numeric types
                ]
            }
        ]

        expected = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "USA", "period": 1, "amountgel": 150.5, "source": "A/B"}
                ]
            }
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_single_applicant_single_transfer(self):
        """Test minimal valid case."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": "USA", "period": 1, "amountgel": 100.0, "source": "A"}
                ]
            }
        ]

        expected = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "USA", "period": 1, "amountgel": 100.0, "source": "A"}
                ]
            }
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_large_amounts_and_periods(self):
        """Test with large numeric values."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": "USA", "period": 999, "amountgel": 1000000.99, "source": "A"},
                    {"country": "USA", "period": 999, "amountgel": 2000000.01, "source": "B"}
                ]
            }
        ]

        expected = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "USA", "period": 999, "amountgel": 3000001.0, "source": "A/B"}
                ]
            }
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_special_characters_in_sources(self):
        """Test sources with special characters."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": "USA", "period": 1, "amountgel": 100.0, "source": "A-1"},
                    {"country": "USA", "period": 1, "amountgel": 50.0, "source": "B_2"},
                    {"country": "USA", "period": 1, "amountgel": 75.0, "source": "C.3"}
                ]
            }
        ]

        expected = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "USA", "period": 1, "amountgel": 225.0, "source": "A-1/B_2/C.3"}
                ]
            }
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_completely_invalid_applicant(self):
        """Test applicant with completely invalid data structure."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": "invalid_not_a_list"
            },
            {
                "applicant_id": "APP_002",
                "transfers": [
                    {"country": "USA", "period": 1, "amountgel": 100.0, "source": "A"}
                ]
            }
        ]
        result = process_applicant_transfers(applicants)

        # At minimum, valid applicants should still be processed
        self.assertTrue(any(app["applicant_id"] == "APP_002" for app in result))

    def test_zero_amounts(self):
        """Test transfers with zero amounts."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": "USA", "period": 1, "amountgel": 0.0, "source": "A"},
                    {"country": "USA", "period": 1, "amountgel": 100.0, "source": "B"}
                ]
            }
        ]

        expected = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "USA", "period": 1, "amountgel": 100.0, "source": "A/B"}
                ]
            }
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)

    def test_negative_amounts(self):
        """Test transfers with negative amounts."""
        applicants = [
            {
                "applicant_id": "APP_001",
                "transfers": [
                    {"country": "USA", "period": 1, "amountgel": 100.0, "source": "A"},
                    {"country": "USA", "period": 1, "amountgel": -25.0, "source": "B"}
                ]
            }
        ]

        expected = [
            {
                "applicant_id": "APP_001",
                "grouped_transfers": [
                    {"country": "USA", "period": 1, "amountgel": 75.0, "source": "A/B"}
                ]
            }
        ]

        result = process_applicant_transfers(applicants)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
