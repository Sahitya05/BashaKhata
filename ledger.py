"""Atomic append-only local ledger. Balances are derived, never model-generated."""
import json
import sqlite3
import re
from decimal import Decimal
from contextlib import closing
from dataclasses import dataclass, asdict
from uuid import uuid4
from legacy_ledger import amount_paise

KINDS = ("credit", "repayment", "settlement", "cash", "borrow", "payback", "lend", "loan_repayment")
EFFECT = {"credit": ("receivable", 1), "repayment": ("receivable", -1),
          "settlement": ("receivable", -1), "cash": ("cash", 1),
          "borrow": ("payable", 1), "payback": ("payable", -1),
          "lend": ("loan", 1), "loan_repayment": ("loan", -1)}

@dataclass(frozen=True)
class Transaction:
    request_key: str
    transcript: str
    account_id: str | None
    kind: str
    paise: int
    product: str = ""
    quantity: str = ""
    unit: str = ""
    source_language: str = ""
    output_language: str = "en"
    description: str = ""
    corrections: str = "[]"
    confirmed: bool = False

def rupees(paise):
    whole, fraction = divmod(abs(paise), 100)
    return f'{"-" if paise < 0 else ""}₹{whole:,}.{fraction:02d}'

class Ledger:
    def __init__(self, path):
        self.path = path
        with closing(self.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, note TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL,
                    account_id TEXT REFERENCES accounts(id), kind TEXT NOT NULL,
                    paise INTEGER NOT NULL CHECK(paise > 0),
                    transcript TEXT NOT NULL, details TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    reversal_of TEXT UNIQUE REFERENCES transactions(id),
                    reason TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY);
            """)
            if not db.execute("SELECT 1 FROM schema_migrations WHERE version=1").fetchone():
                exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='entries'").fetchone()
                if exists:
                    ids = {}
                    for row in db.execute("SELECT * FROM entries ORDER BY rowid").fetchall():
                        key = row["customer_key"]
                        if key not in ids:
                            ids[key] = uuid4().hex
                            db.execute("INSERT INTO accounts VALUES (?,?,?)", (ids[key], row["customer"], "Legacy name-based account; review identity"))
                        details = json.dumps({"product": row["product"], "quantity": row["quantity"], "confirmed": True, "legacy": True})
                        db.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?)",
                                   (row["id"], row["request_key"], ids[key], row["kind"], row["paise"], row["transcript"], details, row["created_at"], row["reversal_of"], "Legacy reversal" if row["reversal_of"] else ""))
                db.execute("INSERT INTO schema_migrations VALUES (1)")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def accounts(self):
        with closing(self.connect()) as db:
            return [dict(r) for r in db.execute("SELECT * FROM accounts ORDER BY name,id")]

    def history(self, account_id=None):
        with closing(self.connect()) as db:
            query = "SELECT t.*, a.name FROM transactions t LEFT JOIN accounts a ON a.id=t.account_id"
            params = ()
            if account_id:
                query += " WHERE account_id=?"
                params = (account_id,)
            return [dict(r) for r in db.execute(query + " ORDER BY t.rowid DESC", params)]

    @staticmethod
    def _balance(db, account_id, bucket):
        total = 0
        for r in db.execute("SELECT kind,paise,reversal_of FROM transactions WHERE account_id=?", (account_id,)):
            direction, sign = EFFECT[r["kind"]]
            if direction == bucket:
                total += r["paise"] * sign * (-1 if r["reversal_of"] else 1)
        return total

    def balance(self, account_id, bucket="receivable"):
        with closing(self.connect()) as db:
            return self._balance(db, account_id, bucket)

    def save(self, tx, *, new_name="", new_note="", expected_balance=None):
        if not tx.confirmed:
            raise ValueError("confirmation")
        if tx.kind not in KINDS or type(tx.paise) is not int or not 0 < tx.paise <= 99999999999999 or not tx.request_key:
            raise ValueError("fields")
        if tx.quantity and (not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", tx.quantity) or Decimal(tx.quantity) <= 0):
            raise ValueError("quantity")
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT id FROM transactions WHERE request_key=?", (tx.request_key,)).fetchone():
                return False
            account_id = tx.account_id
            if account_id and not db.execute("SELECT 1 FROM accounts WHERE id=?", (account_id,)).fetchone():
                raise ValueError("account")
            if not account_id and new_name.strip():
                account_id = uuid4().hex
                db.execute("INSERT INTO accounts VALUES (?,?,?)", (account_id, new_name.strip(), new_note.strip()))
            if not account_id and tx.kind != "cash":
                raise ValueError("account")
            bucket, sign = EFFECT[tx.kind]
            balance = self._balance(db, account_id, bucket)
            if expected_balance is not None and balance != expected_balance:
                raise ValueError("stale")
            if sign < 0 and tx.paise > balance:
                raise ValueError("excess")
            if tx.kind == "settlement" and tx.paise != balance:
                raise ValueError("stale")
            db.execute("INSERT INTO transactions (id,request_key,account_id,kind,paise,transcript,details) VALUES (?,?,?,?,?,?,?)",
                       (uuid4().hex, tx.request_key, account_id, tx.kind, tx.paise, tx.transcript,
                        json.dumps(asdict(tx) | {"account_id": account_id, "direction": bucket,
                                                "balance_sign": sign, "confirmation_status": "confirmed"}, ensure_ascii=False)))
            return True

    def reverse(self, entry_id, reason, confirmed=False):
        if not confirmed or not reason.strip():
            raise ValueError("confirmation")
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM transactions WHERE id=? AND reversal_of IS NULL", (entry_id,)).fetchone()
            if not row:
                raise ValueError("fields")
            if db.execute("SELECT 1 FROM transactions WHERE reversal_of=?", (entry_id,)).fetchone():
                return False
            bucket, sign = EFFECT[row["kind"]]
            if bucket != "cash" and self._balance(db, row["account_id"], bucket) - sign * row["paise"] < 0:
                raise ValueError("reversal_balance")
            db.execute("INSERT INTO transactions (id,request_key,account_id,kind,paise,transcript,details,reversal_of,reason) VALUES (?,?,?,?,?,?,?,?,?)",
                       (uuid4().hex, "reversal:" + entry_id, row["account_id"], row["kind"], row["paise"], row["transcript"], row["details"], entry_id, reason.strip()))
            return True

    def totals(self):
        totals = dict(receivable=0, payable=0, cash=0, loan=0)
        for row in self.history():
            bucket, sign = EFFECT[row["kind"]]
            totals[bucket] += sign * row["paise"] * (-1 if row["reversal_of"] else 1)
        return totals
