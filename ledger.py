import re
import sqlite3
import unicodedata
from contextlib import closing
from decimal import Decimal
from uuid import uuid4

KINDS = ("cash", "credit", "repayment")
NUMBER = r"[0-9]+(?:\.[0-9]+)?"
# Supported commands deliberately use explicit field boundaries and currency.
AMOUNT = rf"(?:₹\s*(?P<symbol_amount>{NUMBER})|(?P<word_amount>{NUMBER})\s*(?:rupees?|रुपये|रुपए|రూపాయలు))"
SALE = re.compile(
    rf"(?P<customer>[^\d,.!?;₹]+?)\s+(?:bought|ने|కొన్నది)\s+"
    rf"(?P<quantity>{NUMBER})\s+(?P<product>[^\d,.!?;₹]+?)\s+"
    rf"(?:for|के लिए|ధర)\s+{AMOUNT}\s+"
    r"(?:on\s+)?(?P<kind>cash|credit|नकद|उधार|నగదు|బాకీ)", re.IGNORECASE
)
REPAYMENT = re.compile(
    rf"(?P<customer>[^\d,.!?;₹]+?)\s+(?:repaid|ने चुकाए|తిరిగి చెల్లించారు)\s+{AMOUNT}",
    re.IGNORECASE
)


def extract(transcript):
    """Suggest fields only when the transcript matches a supported command."""
    normalized = "".join(
        str(unicodedata.decimal(char)) if char.isdecimal() else char
        for char in transcript
    )
    normalized = " ".join(normalized.split()).rstrip(".।")
    sale = SALE.fullmatch(normalized)
    repayment = REPAYMENT.fullmatch(normalized)
    match = sale or repayment
    if not match or re.search(
        r"\b(?:and|or|not|maybe|about|approximately)\b|(?: और | या | नहीं | लगभग | లేదా | కాదు | సుమారు | మరియు )",
        normalized, re.IGNORECASE
    ):
        return {}
    fields = match.groupdict()
    symbol_amount = fields.pop("symbol_amount")
    word_amount = fields.pop("word_amount")
    fields["amount"] = symbol_amount or word_amount
    kind = fields.get("kind", "").casefold()
    fields["kind"] = (
        "repayment" if repayment else
        "cash" if kind in {"cash", "नकद", "నగదు"} else "credit"
    )
    return fields


def amount_paise(value):
    value = value.strip()
    if not re.fullmatch(r"[0-9]{1,12}(?:\.[0-9]{1,2})?", value):
        raise ValueError("amount")
    paise = int(Decimal(value) * 100)
    if paise <= 0:
        raise ValueError("amount")
    return paise


class Ledger:
    def __init__(self, path):
        self.path = path
        with closing(self.connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL,
                    customer TEXT NOT NULL, customer_key TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (kind IN ('cash', 'credit', 'repayment')),
                    product TEXT NOT NULL, quantity TEXT NOT NULL,
                    paise INTEGER NOT NULL CHECK (paise > 0),
                    transcript TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    reversal_of TEXT UNIQUE REFERENCES entries(id)
                )
            """)

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def save(self, request_key, transcript, customer, product, quantity, amount, kind):
        customer = " ".join(unicodedata.normalize("NFC", customer).split())
        product, quantity = product.strip(), quantity.strip()
        if not customer or kind not in KINDS:
            raise ValueError("fields")
        if kind == "repayment":
            product = quantity = ""
        elif not product or not re.fullmatch(NUMBER, quantity) or Decimal(quantity) <= 0:
            raise ValueError("fields")
        paise = amount_paise(amount)
        with closing(self.connect()) as db, db:
            inserted = db.execute("""
                INSERT INTO entries
                (id, request_key, customer, customer_key, kind, product, quantity, paise, transcript)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(request_key) DO NOTHING
            """, (uuid4().hex, request_key, customer, customer.casefold(), kind,
                  product, quantity, paise, transcript))
            return inserted.rowcount == 1

    def reverse(self, entry_id):
        with closing(self.connect()) as db, db:
            inserted = db.execute("""
                INSERT INTO entries
                (id, request_key, customer, customer_key, kind, product, quantity, paise,
                 transcript, reversal_of)
                SELECT ?, ?, customer, customer_key, kind, product, quantity, paise, transcript, id
                FROM entries WHERE id = ? AND reversal_of IS NULL
                ON CONFLICT(reversal_of) DO NOTHING
            """, (uuid4().hex, f"reversal:{entry_id}", entry_id))
            return inserted.rowcount == 1

    def snapshot(self):
        with closing(self.connect()) as db:
            rows = db.execute("SELECT * FROM entries ORDER BY rowid DESC").fetchall()
        balances = {}
        for row in reversed(rows):
            if row["kind"] == "cash":
                continue
            delta = row["paise"] if row["kind"] == "credit" else -row["paise"]
            name, balance = balances.get(row["customer_key"], (row["customer"], 0))
            balances[row["customer_key"]] = (name, balance + (-delta if row["reversal_of"] else delta))
        return rows, list(balances.values())
