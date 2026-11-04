import io
import sqlite3
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import requests
from streamlit.testing.v1 import AppTest

from legacy_ledger import Ledger, amount_paise, extract


COMMANDS = [
    ("Ramesh bought 2 rice for ₹125.50 on credit", "Ramesh", "125.50", "credit"),
    ("रमेश ने २ चावल के लिए ८० रुपये नकद", "रमेश", "80", "cash"),
    ("రమేష్ కొన్నది ౨ బియ్యం ధర ౮౦ రూపాయలు బాకీ", "రమేష్", "80", "credit"),
    ("Ramesh ने 2 rice के लिए 80 रुपये उधार", "Ramesh", "80", "credit"),
    ("Ramesh repaid ₹25", "Ramesh", "25", "repayment"),
    ("रमेश ने चुकाए २५ रुपये", "रमेश", "25", "repayment"),
    ("రమేష్ తిరిగి చెల్లించారు 25 రూపాయలు", "రమేష్", "25", "repayment"),
]


class ParserTests(unittest.TestCase):
    def test_supported_commands(self):
        for command, name, amount, kind in COMMANDS:
            with self.subTest(command=command):
                fields = extract(command)
                self.assertEqual((fields["customer"], fields["amount"], fields["kind"]),
                                 (name, amount, kind))
                if kind != "repayment":
                    self.assertEqual(fields["quantity"], "2")
                    self.assertTrue(fields["product"])

    def test_ambiguous_or_incomplete(self):
        for command in ("Ramesh bought rice", "Ramesh or Sita repaid ₹25",
                        "Ramesh repaid about ₹25", "Ramesh repaid ₹20 or ₹25",
                        "bought 2 rice for ₹80 cash"):
            with self.subTest(command=command):
                self.assertEqual(extract(command), {})

    def test_amounts(self):
        self.assertEqual(amount_paise("125.05"), 12505)
        for amount in ("", "-1", "+1", "0", "0.00", "3.141", "1e3", "NaN"):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                amount_paise(amount)


class LedgerFixture:

    def setUp(self):
        self.path = Path(__file__).with_name(f"test-{uuid4().hex}.sqlite3")
        self.addCleanup(self.path.unlink, missing_ok=True)
        self.ledger = Ledger(self.path)


class LedgerTests(LedgerFixture, unittest.TestCase):
    def test_balance_duplicate_reversal_and_reopen(self):
        self.assertTrue(self.ledger.save("a", "original", "Ramesh", "rice", "2", "125.50", "credit"))
        self.assertFalse(self.ledger.save("a", "original", "Ramesh", "rice", "2", "999", "credit"))
        self.ledger.save("b", "", " ramesh ", "", "", "25.25", "repayment")
        self.ledger.save("c", "", "Ramesh", "milk", "1", "30", "cash")
        rows, balances = Ledger(self.path).snapshot()
        self.assertEqual(balances, [("Ramesh", 10025)])
        credit = rows[-1]
        self.assertEqual(credit["transcript"], "original")
        self.assertTrue(self.ledger.reverse(credit["id"]))
        self.assertFalse(self.ledger.reverse(credit["id"]))
        rows, balances = self.ledger.snapshot()
        self.assertEqual(rows[0]["reversal_of"], credit["id"])
        self.assertEqual(balances, [("Ramesh", -2525)])

    def test_database_failure_then_retry(self):
        with patch.object(self.ledger, "connect", side_effect=sqlite3.OperationalError):
            with self.assertRaises(sqlite3.OperationalError):
                self.ledger.save("a", "", "Ramesh", "rice", "2", "80", "cash")
        self.assertEqual(self.ledger.snapshot(), ([], []))
        self.assertTrue(self.ledger.save("a", "", "Ramesh", "rice", "2", "80", "cash"))
