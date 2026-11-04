"""BhashaKhata: record -> review -> preview -> explicitly confirm -> append."""
import csv
import hashlib
import hmac
import io
import json
import sqlite3
from datetime import date
from pathlib import Path
from uuid import uuid4

import requests
import streamlit as st
from extraction import extract, correct_amount
from i18n import label
from ledger import Ledger, Transaction, KINDS, EFFECT, amount_paise, rupees
from speech import INPUT_OPTIONS, transcribe
from translation import AzureTranslator

st.set_page_config(page_title="BhashaKhata", page_icon="🛒", layout="wide")

def secret(key, default=""):
    try:
        return st.secrets.get(key, default)
    except FileNotFoundError:
        return default

language = st.sidebar.selectbox("Output language · भाषा · భాష", ["en", "hi", "te"],
                               format_func={"en": "English", "hi": "हिन्दी", "te": "తెలుగు"}.get,
                               key="output_language")
def t(key):
    return label(key, language)

if secret("DEPLOYMENT_MODE", "local") != "local":
    st.error("Hosted mode is blocked until a persistent hosted database and per-shop authentication are configured and tested.")
    st.stop()

password = secret("APP_PASSWORD")
if password and not st.session_state.get("authenticated"):
    supplied = st.text_input("Shop password", type="password")
    if st.button("Sign in"):
        if hmac.compare_digest(supplied.encode(), str(password).encode()):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error(t("error"))
    st.stop()

try:
    ledger = Ledger(secret("DATABASE_PATH", str(Path(__file__).with_name("bhashakhata.sqlite3"))))
    accounts = ledger.accounts()
except sqlite3.Error:
    st.error(t("error"))
    st.stop()

st.title("🛒 BhashaKhata")
st.caption("Speak Your Business. Track Every Rupee.")
st.sidebar.caption(t("local"))
page = st.sidebar.radio("BhashaKhata", ["dashboard", "record", "ledger", "reports"], format_func=t, key="page")
st.session_state.setdefault("audio_epoch", 0)
st.session_state.setdefault("speech_cache", {})
st.session_state.setdefault("translation_cache", {})

# Keep editable values when a correction or preview temporarily hides widgets.
for field in ("account", "customer", "note", "kind", "product", "quantity", "unit", "amount", "description"):
    key = "draft_" + field
    if key in st.session_state:
        st.session_state[key] = st.session_state[key]

def reset():
    for key in list(st.session_state):
        if key.startswith("draft_") or key in ("pending", "prepared"):
            del st.session_state[key]
    st.session_state.audio_epoch += 1

def new_draft(result, source):
    reset()
    st.session_state.pending = result | {"source_language": source, "corrections": []}
    fields = extract(result["transcript"])
    for field in ("customer", "kind", "product", "quantity", "unit", "amount"):
        st.session_state["draft_" + field] = fields.get(field, None if field == "kind" else "")

def failure(exc):
    st.error(t("error"))
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        st.caption(f"HTTP {exc.response.status_code}")
    elif isinstance(exc, ValueError):
        messages = {
            "amount": ("Enter a positive INR amount with at most two decimals.", "सही धनात्मक राशि लिखें।", "సరైన ధనాత్మక మొత్తం నమోదు చేయండి."),
            "excess": ("Repayment exceeds this account's outstanding balance.", "चुकौती बकाया से अधिक है।", "చెల్లింపు బాకీ కంటే ఎక్కువగా ఉంది."),
            "stale": ("Balance changed. Reopen the preview and confirm the new balance.", "शेष बदल गया। नया पूर्वावलोकन देखें।", "బాకీ మారింది. కొత్త ప్రివ్యూ చూడండి."),
            "account": ("Select an existing account or enter a new person's name.", "खाता चुनें या नया नाम लिखें।", "ఖాతా ఎంచుకోండి లేదా కొత్త పేరు నమోదు చేయండి."),
            "reversal_balance": ("Reverse later repayments first; this reversal would make the balance negative.", "पहले बाद की चुकौती वापस करें।", "ముందుగా తర్వాతి చెల్లింపులను రివర్స్ చేయండి."),
        }
        if str(exc) in messages:
            st.info(messages[str(exc)][["en", "hi", "te"].index(language)])
        else:
            st.caption(str(exc))

def show_rows(rows):
    if not rows:
        st.info(t("empty"))
        return
    st.dataframe([{t("name"): r["name"] or "—", t("kind"): t(r["kind"]),
                   t("amount"): rupees(r["paise"] * (-1 if r["reversal_of"] else 1)),
                   "UTC": r["created_at"], "ID": r["id"]} for r in rows], hide_index=True, use_container_width=True)

if notice := st.session_state.pop("notice", None):
    st.success(t(notice))

if page == "dashboard":
    totals = ledger.totals()
    for col, bucket in zip(st.columns(4), ("receivable", "payable", "cash", "loan")):
        col.metric(t(bucket), rupees(totals[bucket]))
    st.caption(f'{t("account")}: {len(accounts)}')
    def go_record():
        st.session_state.page = "record"
    st.button(t("new"), type="primary", on_click=go_record)
    show_rows(ledger.history()[:10])

elif page == "record":
    input_choice = st.selectbox(t("input"), list(INPUT_OPTIONS), key="input_language")
    input_code = INPUT_OPTIONS[input_choice]
    if not st.session_state.get("pending"):
        audio = st.audio_input(t("mic"), sample_rate=16000, key=f'audio_{st.session_state.audio_epoch}')
        if audio is not None:
            st.audio(audio.getvalue(), format="audio/wav")
        if st.button(t("process"), type="primary", disabled=audio is None):
            try:
                result = transcribe(secret("GNANI_API_KEY"), audio.getvalue(), input_code,
                                    cache=st.session_state.speech_cache)
                new_draft(result, input_code)
                st.rerun()
            except (requests.RequestException, ValueError) as exc:
                failure(exc)
        with st.expander(t("manual")):
            manual = st.text_area(t("text"), key=f'manual_{st.session_state.audio_epoch}')
            if st.button(t("review"), disabled=not manual.strip()):
                new_draft({"transcript": manual, "request_key": "manual:" + uuid4().hex}, input_code)
                st.rerun()
    pending = st.session_state.get("pending")
    if pending:
        with st.expander(t("original"), expanded=True):
            st.text(pending["transcript"])
            st.caption("Gnani Prisma v3.0" if not pending["request_key"].startswith("manual:") else t("manual"))
        translator = AzureTranslator(secret("AZURE_TRANSLATOR_KEY"), secret("AZURE_TRANSLATOR_REGION"), st.session_state.translation_cache)
        if not translator.key:
            st.info(t("translation_unavailable"))
        else:
            attempts = pending.setdefault("translation_attempts", [])
            retry = st.button(t("translate"))
            if language not in attempts or retry:
                if language not in attempts:
                    attempts.append(language)
                try:
                    translator.translate(pending["transcript"], language)
                except (requests.RequestException, ValueError) as exc:
                    failure(exc)
            if (pending["transcript"], language) not in st.session_state.translation_cache:
                st.info(t("translation_unavailable"))
        translated = st.session_state.translation_cache.get((pending["transcript"], language))
        if translated:
            st.success(translated)

        if not st.session_state.get("prepared"):
            st.info(t("unsupported"))
            with st.expander(t("correction")):
                st.caption('“No, amount 130 ka badle 150 karo.” / “Change amount from 130 to 150.”')
                correction_audio = st.audio_input(t("correction"), sample_rate=16000,
                                                  key=f'correction_{st.session_state.audio_epoch}')
                correction_text = st.text_input(t("text"), key="draft_correction_text")
                if st.button(t("apply")):
                    try:
                        if correction_audio is not None:
                            correction_text = transcribe(secret("GNANI_API_KEY"), correction_audio.getvalue(), input_code,
                                                         cache=st.session_state.speech_cache)["transcript"]
                        replacement = correct_amount(correction_text, st.session_state.draft_amount)
                        pending["corrections"].append({"text": correction_text, "before": st.session_state.draft_amount, "after": replacement})
                        st.session_state.draft_amount = replacement
                        st.session_state.audio_epoch += 1
                        st.rerun()
                    except (requests.RequestException, ValueError) as exc:
                        failure(exc)
            choices = {"": t("choose"), "new": t("create"), "cash": t("walkin")}
            choices.update({a["id"]: f'{a["name"]} · {a["note"]} · {a["id"][:8]}' for a in accounts})
            selected = st.selectbox(t("account"), list(choices), format_func=choices.get, key="draft_account")
            name = st.text_input(t("name"), key="draft_customer", disabled=selected != "new")
            note = st.text_input(t("note"), key="draft_note", disabled=selected != "new")
            kind = st.selectbox(t("kind"), [None, *KINDS], format_func=lambda k: t(k or "choose"), key="draft_kind")
            product = st.text_input(t("product"), key="draft_product")
            cols = st.columns(2)
            quantity = cols[0].text_input(t("quantity"), key="draft_quantity")
            unit = cols[1].text_input(t("unit"), key="draft_unit")
            amount = st.text_input(t("amount"), key="draft_amount", disabled=kind == "settlement")
            description = st.text_area(t("description"), key="draft_description")
            if st.button(t("preview"), type="primary"):
                try:
                    if not selected or (selected == "new" and not name.strip()) or (selected == "cash" and kind != "cash"):
                        raise ValueError("account")
                    if not kind:
                        raise ValueError("fields")
                    account_id = selected if selected not in ("new", "cash") else None
                    bucket, sign = EFFECT[kind]
                    before = ledger.balance(account_id, bucket)
                    paise = before if kind == "settlement" else amount_paise(amount)
                    if paise <= 0:
                        raise ValueError("amount")
                    if sign < 0 and paise > before:
                        raise ValueError("excess")
                    tx = Transaction(pending["request_key"], pending["transcript"], account_id, kind, paise,
                                     product, quantity, unit, pending["source_language"], language,
                                     description, json.dumps(pending["corrections"], ensure_ascii=False), True)
                    st.session_state.prepared = {"tx": tx, "before": before, "after": before + sign * paise,
                                                 "name": name if selected == "new" else choices[selected],
                                                 "new_name": name if selected == "new" else "", "note": note}
                    st.rerun()
                except (ValueError, sqlite3.Error) as exc:
                    failure(exc)
        else:
            preview = st.session_state.prepared
            tx = preview["tx"]
            st.subheader(t("review"))
            st.write(preview["name"])
            st.write(t(tx.kind), rupees(tx.paise))
            st.text(f'{tx.quantity} {tx.unit} {tx.product}'.strip())
            st.text(tx.description)
            if tx.kind != "cash":
                st.write(t(EFFECT[tx.kind][0]))
                a, b = st.columns(2)
                a.metric(t("before"), rupees(preview["before"]))
                b.metric(t("after"), rupees(preview["after"]))
            verified = st.checkbox(t("verify"), key="draft_verified")
            if st.button(t("save"), type="primary", disabled=not verified):
                try:
                    saved = ledger.save(tx, new_name=preview["new_name"], new_note=preview["note"], expected_balance=preview["before"])
                    reset()
                    st.session_state.notice = "saved" if saved else "duplicate"
                    st.rerun()
                except (ValueError, sqlite3.Error) as exc:
                    failure(exc)
            if st.button(t("edit")):
                del st.session_state.prepared
                st.session_state.pop("draft_verified", None)
                st.rerun()
    if st.button(t("cancel")):
        reset()
        st.rerun()

elif page == "ledger":
    search = st.text_input(t("search"))
    matches = [a for a in accounts if search.casefold() in a["name"].casefold()]
    if matches or (not search and ledger.history()):
        by_id = {a["id"]: a for a in matches}
        account_id = st.selectbox(t("account"), [None, *by_id], format_func=lambda k: t("all_accounts") if k is None else f'{by_id[k]["name"]} · {by_id[k]["note"]} · {k[:8]}')
        for col, bucket in zip(st.columns(3), ("receivable", "payable", "loan")):
            col.metric(t(bucket), rupees(ledger.balance(account_id, bucket) if account_id else ledger.totals()[bucket]))
        rows = ledger.history(account_id)
        show_rows(rows)
        reversed_ids = {r["reversal_of"] for r in rows}
        for row in rows:
            with st.expander(f'{row["created_at"]} · {t(row["kind"])} · {rupees(row["paise"])} · {row["id"][:8]}'):
                st.text(row["transcript"])
                st.json(json.loads(row["details"]))
                if row["reason"]:
                    st.text(row["reason"])
                if not row["reversal_of"] and row["id"] not in reversed_ids:
                    reason = st.text_input(t("reason"), key="reason_" + row["id"])
                    check = st.checkbox(t("confirm_reverse"), key="reverse_check_" + row["id"])
                    if st.button(t("reverse"), key="reverse_" + row["id"], disabled=not (check and reason.strip())):
                        try:
                            ledger.reverse(row["id"], reason, confirmed=check)
                            st.rerun()
                        except (ValueError, sqlite3.Error) as exc:
                            failure(exc)
    else:
        st.info(t("empty"))

elif page == "reports":
    start = st.date_input(t("start"), value=date(2020, 1, 1))
    end = st.date_input(t("end"), value=date.today())
    rows = [r for r in ledger.history() if str(start) <= r["created_at"][:10] <= str(end)]
    show_rows(rows)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "account_id", "name", "type", "paise", "UTC", "reversal_of", "reason"])
    def safe(value):
        value = str(value or "")
        return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value
    for row in rows:
        writer.writerow([safe(row[k]) for k in ("id", "account_id", "name", "kind", "paise", "created_at", "reversal_of", "reason")])
    st.download_button(t("export"), output.getvalue().encode("utf-8-sig"), "reviewed-ledger.csv", "text/csv")
