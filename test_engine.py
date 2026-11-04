import io
import json
import sqlite3
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from unittest.mock import Mock, patch

import pytest
import requests
from streamlit.testing.v1 import AppTest

from ledger import Ledger, Transaction, amount_paise
from extraction import extract, correct_amount
from speech import transcribe
from translation import AzureTranslator

@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "test.sqlite3")

def tx(key="a", kind="credit", amount=20000, account=None, confirmed=True):
    return Transaction(key, "fictional original", account, kind, amount, confirmed=confirmed)

def seed(ledger):
    ledger.save(tx(), new_name="Fictional Person")
    return ledger.accounts()[0]["id"]

def test_acceptance_four_transactions_and_restart(ledger):
    account = seed(ledger)
    ledger.save(tx("b", amount=8000, account=account))
    assert ledger.balance(account) == 28000
    ledger.save(tx("c", "repayment", 10000, account))
    assert ledger.balance(account) == 18000
    ledger.save(tx("d", "settlement", ledger.balance(account), account), expected_balance=18000)
    reopened = Ledger(ledger.path)
    assert reopened.balance(account) == 0
    assert len(reopened.history()) == 4
    assert all(r["transcript"] == "fictional original" for r in reopened.history())

def test_directions_and_totals(ledger):
    account = seed(ledger)
    for key, kind, value in [("b", "borrow", 50000), ("c", "payback", 20000),
                             ("d", "cash", 12000), ("e", "lend", 9000), ("f", "loan_repayment", 4000)]:
        ledger.save(tx(key, kind, value, account))
    assert ledger.totals() == dict(receivable=20000, payable=30000, cash=12000, loan=5000)

def test_same_names_are_separate(ledger):
    seed(ledger)
    ledger.save(tx("b"), new_name="Fictional Person")
    assert len(ledger.accounts()) == 2

def test_confirmation_and_atomic_rollback(ledger):
    with pytest.raises(ValueError, match="confirmation"):
        ledger.save(tx(confirmed=False), new_name="Not saved")
    with pytest.raises(ValueError, match="excess"):
        ledger.save(tx(kind="repayment"), new_name="Not saved")
    assert ledger.accounts() == []
    assert ledger.history() == []

def test_durable_duplicate_and_concurrency(ledger):
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: ledger.save(tx(), new_name="One account"), range(2)))
    assert sorted(results) == [False, True]
    assert len(ledger.accounts()) == 1
    assert not Ledger(ledger.path).save(tx(), new_name="Duplicate")

def test_excess_stale_and_settlement(ledger):
    account = seed(ledger)
    with pytest.raises(ValueError, match="excess"):
        ledger.save(tx("b", "repayment", 20001, account))
    with pytest.raises(ValueError, match="stale"):
        ledger.save(tx("b", "settlement", 10000, account))
    with pytest.raises(ValueError, match="stale"):
        ledger.save(tx("b", amount=100, account=account), expected_balance=0)
    assert len(ledger.history()) == 1

def test_reversal_audit_and_order(ledger):
    account = seed(ledger)
    original = ledger.history()[0]["id"]
    ledger.save(tx("b", "repayment", 10000, account))
    payment = ledger.history()[0]["id"]
    with pytest.raises(ValueError, match="reversal_balance"):
        ledger.reverse(original, "mistake", True)
    with pytest.raises(ValueError, match="confirmation"):
        ledger.reverse(payment, "mistake")
    assert ledger.reverse(payment, "fictional correction", True)
    assert not ledger.reverse(payment, "duplicate", True)
    assert ledger.reverse(original, "fictional correction", True)
    assert ledger.balance(account) == 0
    assert len(ledger.history()) == 4

def test_migration_preserves_original_tables_and_reversals(tmp_path):
    from legacy_ledger import Ledger as OldLedger
    path = tmp_path / "old.sqlite3"
    old = OldLedger(path)
    old.save("a", "original", "Legacy", "rice", "1", "200", "credit")
    old.reverse(old.snapshot()[0][0]["id"])
    migrated = Ledger(path)
    assert len(migrated.history()) == 2
    assert migrated.totals()["receivable"] == 0
    assert len(Ledger(path).history()) == 2
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM entries").fetchone()[0] == 2

@pytest.mark.parametrize("text,kind,amount", [
    ("Ramesh bought groceries worth 200 rupees on credit.", "credit", "200"),
    ("Sita took milk worth 80 rupees on credit", "credit", "80"),
    ("Anjali paid back 300 rupees", "repayment", "300"),
    ("I borrowed 500 rupees from Kumar", "borrow", "500"),
    ("I paid Kumar 200 rupees", "payback", "200"),
    ("I lent 90 rupees to New Person", "lend", "90"),
    ("Record a cash sale of 120 rupees", "cash", "120"),
    ("Add 450 rupees to Suresh's credit", "credit", "450"),
    ("Ramesh ko 2 kilo rice diya, 130 rupees udhaar mein add karo.", "credit", "130"),
    ("రమేష్ కి రెండు వందల రూపాయలు బాకీ రాయి.", "credit", "200"),
    ("रमेश को दो सौ रुपये उधार लिखो", "credit", "200"),
    ("Ramesh ने 2 rice के लिए 80 रुपये उधार", "credit", "80"),
    ("రమేష్ కొన్నది 2 rice ధర 80 రూపాయలు బాకీ", "credit", "80"),
    ("రమేష్ ने 2 బియ్యం के लिए 80 रुपये उधार", "credit", "80"),
    ("రమేష్ ने 2 rice के लिए 80 रुपये ఉधार", None, None),
    ("రమేష్ నే 2 rice", None, None),
])
def test_supported_languages(text, kind, amount):
    result = extract(text)
    assert result.get("kind") == kind
    assert result.get("amount") == amount

@pytest.mark.parametrize("text", ["Ramesh paid 100 rupees and Sita paid 20 rupees", "Ramesh or Sita repaid ₹25",
    "I borrowed or lent 100 rupees", "Ramesh paid about 100 rupees", "Ramesh paid 100 dollars", "Ramesh paid 100 rupees 200 rupees",
    "Ramesh paid", "Ramesh paid -100 rupees", "Ramesh did not pay 100 rupees"])
def test_ambiguity(text):
    assert extract(text) == {}

@pytest.mark.parametrize("value", ["0", "-1", "NaN", "1.234", "1e3", "", "100 USD"])
def test_invalid_money(value):
    with pytest.raises(ValueError):
        amount_paise(value)

def test_correction():
    assert correct_amount("No, amount 130 ka badle 150 karo.", "130") == "150"
    with pytest.raises(ValueError):
        correct_amount("No, amount 130 ka badle 150 karo", "100")
    with pytest.raises(ValueError):
        correct_amount("make it maybe 150", "130")

def audio():
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        wav.writeframes(bytes(3200))
    return stream.getvalue()

def test_speech_contract_cache_and_no_audio_retention():
    response = Mock()
    response.json.return_value = {"success": True, "transcript": "original"}
    cache = {}
    with patch("speech.requests.post", return_value=response) as post:
        first = transcribe("mock-key", audio(), "te-IN,hi-IN,en-IN", cache=cache)
        assert transcribe("mock-key", audio(), "te-IN,hi-IN,en-IN", cache=cache) == first
        assert post.call_count == 1
        assert post.call_args.kwargs["data"]["format"] == "codemix"
        assert post.call_args.kwargs["headers"] == {"X-API-Key-ID": "mock-key"}
    assert "audio" not in json.dumps(cache)

@pytest.mark.parametrize("result", [{"success": False}, {"success": True, "transcript": ""},
                                      {"success": True, "transcript": "partial", "truncated": True}])
def test_bad_speech_response(result):
    response = Mock()
    response.json.return_value = result
    with patch("speech.requests.post", return_value=response), pytest.raises(ValueError):
        transcribe("mock", audio(), "en-IN")

def test_no_request_for_empty_audio_and_network_failure():
    with patch("speech.requests.post") as post:
        with pytest.raises(ValueError):
            transcribe("mock", b"", "en-IN")
        post.assert_not_called()
        post.side_effect = requests.Timeout()
        with pytest.raises(requests.Timeout):
            transcribe("mock", audio(), "en-IN")

def test_translation_cache_failure_and_unavailable():
    response = Mock()
    response.json.return_value = [{"translations": [{"text": "translated"}]}]
    translator = AzureTranslator("mock", "mock-region")
    with patch("translation.requests.post", return_value=response) as post:
        assert translator.translate("original", "te") == "translated"
        assert translator.translate("original", "te") == "translated"
        assert post.call_count == 1
        response.raise_for_status.side_effect = requests.Timeout()
        with pytest.raises(requests.Timeout):
            translator.translate("original", "hi")
        assert ("original", "hi") not in translator.cache
    with pytest.raises(ValueError, match="unavailable"):
        AzureTranslator("", "").translate("original", "en")

def click(app, label):
    next(b for b in app.button if b.label == label).click().run()
    assert not app.exception

def test_ui_manual_confirmation_reset_and_languages(tmp_path):
    app = AppTest.from_file("app.py", default_timeout=20)
    app.secrets["DATABASE_PATH"] = str(tmp_path / "ui.sqlite3")
    app.run()
    assert not app.exception
    click(app, "New voice transaction")
    app.text_area[0].set_value("Ramesh bought groceries worth 200 rupees on credit.")
    click(app, "Review transaction")
    app.selectbox(key="draft_account").select("new").run()
    click(app, "Preview balance effect")
    assert Ledger(tmp_path / "ui.sqlite3").history() == []
    assert next(b for b in app.button if b.label == "Confirm and save").disabled
    app.checkbox(key="draft_verified").check().run()
    click(app, "Confirm and save")
    assert len(Ledger(tmp_path / "ui.sqlite3").history()) == 1
    assert "pending" not in app.session_state
    app.selectbox(key="output_language").select("te").run()
    assert not app.exception
    assert app.selectbox(key="output_language").value == "te"

def test_hosted_mode_blocked(tmp_path):
    app = AppTest.from_file("app.py")
    app.secrets["DEPLOYMENT_MODE"] = "hosted"
    app.run()
    assert "Hosted mode is blocked" in app.error[0].value

def test_voice_ui_four_recordings_and_no_retranscribe_on_output_change(tmp_path):
    app = AppTest.from_file("app.py", default_timeout=20)
    path = tmp_path / "voice.sqlite3"
    app.secrets["DATABASE_PATH"] = str(path)
    app.secrets["GNANI_API_KEY"] = "mock-key"
    app.secrets["AZURE_TRANSLATOR_KEY"] = ""
    transcripts = ["Ramesh bought groceries worth 200 rupees on credit.",
                   "Ramesh took milk worth 80 rupees on credit.", "Ramesh paid 100 rupees.",
                   "Ramesh cleared the remaining debt."]
    app.run()
    click(app, "New voice transaction")
    with patch("speech.transcribe") as stt, patch("streamlit.audio_input", return_value=io.BytesIO(audio())):
        for n, transcript in enumerate(transcripts):
            stt.return_value = {"transcript": transcript, "request_key": f"mock-recording-{n}"}
            app.run()
            click(app, "Transcribe with Gnani")
            if n == 0:
                app.selectbox(key="output_language").select("hi").run()
                app.selectbox(key="output_language").select("en").run()
                assert stt.call_count == 1
                app.selectbox(key="draft_account").select("new").run()
            else:
                account = Ledger(path).accounts()[0]["id"]
                app.selectbox(key="draft_account").select(account).run()
            click(app, "Preview balance effect")
            assert len(Ledger(path).history()) == n
            app.checkbox(key="draft_verified").check().run()
            click(app, "Confirm and save")
            account = Ledger(path).accounts()[0]["id"]
            assert Ledger(path).balance(account) == [20000, 28000, 18000, 0][n]
        assert stt.call_count == 4
    assert len(Ledger(path).history()) == 4

def test_ui_correction_and_failed_save_retains_draft(tmp_path):
    app = AppTest.from_file("app.py", default_timeout=20)
    app.secrets["DATABASE_PATH"] = str(tmp_path / "correction.sqlite3")
    app.run()
    click(app, "New voice transaction")
    app.text_area[0].set_value("Ramesh ko 2 kilo rice diya, 130 rupees udhaar mein add karo.")
    click(app, "Review transaction")
    app.text_input(key="draft_correction_text").set_value("No, amount 130 ka badle 150 karo")
    click(app, "Apply amount correction")
    assert app.text_input(key="draft_amount").value == "150"
    app.selectbox(key="draft_account").select("new").run()
    click(app, "Preview balance effect")
    app.checkbox(key="draft_verified").check().run()
    with patch("ledger.Ledger.save", side_effect=sqlite3.OperationalError("fixture failure")):
        click(app, "Confirm and save")
    assert "prepared" in app.session_state
    click(app, "Confirm and save")
    row = Ledger(tmp_path / "correction.sqlite3").history()[0]
    assert row["paise"] == 15000
    assert "130 rupees" in row["transcript"]
    assert json.loads(json.loads(row["details"])["corrections"])[0]["after"] == "150"

def test_reports_and_cash_reversal_ui(tmp_path):
    path = tmp_path / "cash.sqlite3"
    store = Ledger(path)
    store.save(tx(kind="cash"))
    app = AppTest.from_file("app.py", default_timeout=20)
    app.secrets["DATABASE_PATH"] = str(path)
    app.run()
    app.radio(key="page").set_value("reports").run()
    assert not app.exception
    assert len(app.dataframe) == 1
    app.radio(key="page").set_value("ledger").run()
    assert not app.exception
    row = store.history()[0]
    app.text_input(key="reason_" + row["id"]).set_value("fictional correction")
    app.checkbox(key="reverse_check_" + row["id"]).check().run()
    click(app, "Reverse transaction")
    assert store.totals()["cash"] == 0

def test_three_language_command_and_native_digits():
    assert extract("రమేష్ ने 2 rice के लिए 80 रुपये उधार")["amount"] == "80"
    assert extract("రమేష్ కి ౨౦౦ రూపాయలు బాకీ రాయి")["amount"] == "200"
    assert amount_paise("125.05") == 12505

def test_missing_account_and_invalid_quantity(ledger):
    with pytest.raises(ValueError, match="account"):
        ledger.save(tx())
    with pytest.raises(ValueError, match="quantity"):
        ledger.save(replace(tx(), quantity="-2"), new_name="Fictional")
    assert not ledger.accounts()
