import unittest

from client import build_payload


class BuildPayloadTests(unittest.TestCase):
    def test_cents_are_rounded(self):
        self.assertEqual(build_payload("acc-1", 12.34), {"account": "acc-1", "amount_cents": 1234})

    def test_zero(self):
        self.assertEqual(build_payload("acc-1", 0.0)["amount_cents"], 0)
