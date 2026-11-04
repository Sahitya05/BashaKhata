import io
import sqlite3
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import requests
from streamlit.testing.v1 import AppTest

from ledger import Ledger, amount_paise, extract


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


class AppTests(LedgerFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        audio = io.BytesIO()
        with wave.open(audio, "wb") as wav:
            wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            wav.writeframes(bytes(3200))
        self.app = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=45)
        self.app.secrets["GNANI_API_KEY"] = "mock-key"
        for target, value in (("streamlit.audio_input", audio), ("ledger.Ledger", self.ledger)):
            mocked = patch(target, return_value=value)
            mocked.start()
            self.addCleanup(mocked.stop)
        mocked = patch("requests.post")
        self.post = mocked.start()
        self.addCleanup(mocked.stop)
        self.post.return_value.json.return_value = {"success": True, "transcript": COMMANDS[0][0]}

    def click(self, name):
        next(button for button in self.app.button if button.label == name).click().run()
        self.assertFalse(self.app.exception)

    def test_voice_review_cancel_edit_and_save(self):
        self.app.run()
        self.click("Transcribe with Gnani")
        self.assertEqual(self.post.call_count, 1)
        self.assertEqual(self.app.text_input[-1].value, "125.50")
        self.click("Confirm and save")
        self.assertEqual(self.ledger.snapshot(), ([], []))
        self.click("Cancel")
        self.assertEqual(self.ledger.snapshot(), ([], []))
        self.click("Transcribe with Gnani")
        self.app.text_input[-1].set_value("100.25")
        self.app.checkbox[0].check()
        self.click("Confirm and save")
        self.assertEqual(self.ledger.snapshot()[1], [("Ramesh", 10025)])
        self.assertEqual(self.app.dataframe[0].value.iloc[0]["Balance"], "₹100.25")

    def test_gnani_errors(self):
        self.app.run()
        for status in (402, 429, 500):
            response = requests.Response()
            response.status_code = status
            self.post.return_value.raise_for_status.side_effect = requests.HTTPError(response=response)
            self.click("Transcribe with Gnani")
            self.assertIn(str(status), self.app.error[0].value)
        self.assertEqual(self.post.call_count, 3)
        self.assertEqual(self.ledger.snapshot(), ([], []))
