import unittest

from money import parse_amount
from report import total


class ParseAmountTests(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(parse_amount("12.50"), 12.5)

    def test_thousands_separator(self):
        self.assertEqual(parse_amount("1,200.00"), 1200.0)

    def test_parentheses_negative(self):
        self.assertEqual(parse_amount("(12.50)"), -12.5)


class TotalTests(unittest.TestCase):
    def test_total_mixes_signs(self):
        self.assertEqual(total(["10.00", "(2.50)"]), 7.5)
