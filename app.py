
import hashlib
import io
import json
import wave
import sqlite3
from pathlib import Path
from uuid import uuid4

import requests
import streamlit as st
from ledger import KINDS, Ledger, extract


# ==========================================
# CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="BhashaKhata",
    page_icon="🛒",
    layout="centered"
)

GNANI_URL = "https://api.vachana.ai/stt/v3"

INPUT_OPTIONS = {
    "Hindi + Telugu + English": "hi-IN,te-IN,en-IN",
    "Telugu + English": "te-IN,en-IN",
    "Hindi + English": "hi-IN,en-IN",
    "Hindi + Telugu": "hi-IN,te-IN",
    "Telugu only": "te-IN",
    "Hindi only": "hi-IN",
    "English only": "en-IN",
    "Automatic detection": "indic-auto"
}

FORMAT_OPTIONS = {
    "Mixed scripts (codemix)": "codemix",
    "Numbers and currency (transcribe)": "transcribe"
}

DEFAULT_TERMS = (
    "Ramesh, rice, sugar, milk, "
    "బాకీ, బియ్యం, రూపాయలు, "
    "उधार, रुपये, चावल"
)


# ==========================================
# TRANSCRIPTION
# ==========================================

def audio_duration(audio_bytes):
    """Read duration of a WAV recording."""
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
        return (
            wav.getnframes() /
            wav.getframerate()
        )


def call_gnani(
    api_key,
    audio_bytes,
    language_code,
    output_format,
    keyterms
):
    """Transcribe audio using Prisma v3.0."""

    data = {
        "model": "prisma-v3.0",
        "language_code": language_code,
        "format": output_format,
        "topic": (
            "Indian Kirana shop accounting, "
            "customer credit, cash payments, "
            "products, quantities and rupees"
        )
    }

    if keyterms:
        data["keyterms"] = json.dumps(
            keyterms[:200],
            ensure_ascii=False
        )

    response = requests.post(
        GNANI_URL,
        headers={
            "X-API-Key-ID": api_key
        },
        files={
            "audio_file": (
                "transaction.wav",
                audio_bytes,
                "audio/wav"
            )
        },
        data=data,
        timeout=60
    )

    response.raise_for_status()

    result = response.json()

    if (not isinstance(result, dict) or result.get("success") is not True
            or not isinstance(result.get("transcript"), str)):
        raise ValueError(
            "Gnani did not complete transcription."
        )

    return result


language_index = st.selectbox("Interface · इंटरफ़ेस · ఇంటర్‌ఫేస్", range(3),
                              format_func=("English", "हिन्दी", "తెలుగు").__getitem__)


def label(english, hindi, telugu):
    return (english, hindi, telugu)[language_index]


st.title("🛒 BhashaKhata")

st.write(
    "Your multilingual voice accounting assistant"
)

st.caption(
    "Speak in Hindi, Telugu, English, "
    "or a mixture of these languages."
)

st.divider()


# ==========================================
# LANGUAGE SETTINGS
# ==========================================

st.subheader(label("1. Language settings", "1. भाषा सेटिंग", "1. భాష సెట్టింగులు"))

input_choice = st.selectbox(
    label("Which languages will you speak?", "आप किन भाषाओं में बोलेंगे?", "మీరు ఏ భాషల్లో మాట్లాడతారు?"),
    list(INPUT_OPTIONS.keys()),
    index=0
)

format_choice = st.selectbox(
    label("Speech recognition format", "लिप्यंतरण का प्रारूप", "లిప్యంతరీకరణ ఆకృతి"),
    list(FORMAT_OPTIONS.keys()),
    index=1
)

with st.expander("Improve accuracy with shop vocabulary"):
    terms_input = st.text_input(
        "Important customer names and product words",
        value=DEFAULT_TERMS
    )

keyterms = [
    term.strip()
    for term in terms_input.split(",")
    if term.strip()
]

if len(keyterms) > 200:
    st.warning("Only the first 200 keyterms will be sent.")


# ==========================================
# RECORD AUDIO
# ==========================================

st.divider()
st.subheader(label("2. Record transaction", "2. लेनदेन रिकॉर्ड करें", "2. లావాదేవీని రికార్డ్ చేయండి"))

audio = st.audio_input(
    label("Speak a transaction (maximum 30 seconds)", "लेनदेन बोलें (अधिकतम 30 सेकंड)", "లావాదేవీ చెప్పండి (గరిష్ఠంగా 30 సెకన్లు)"),
    sample_rate=16000
)

audio_bytes = (
    audio.getvalue()
    if audio is not None
    else None
)

if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")


# ==========================================
# BUILD REQUEST FINGERPRINT
# ==========================================

fingerprint = None

if audio_bytes:
    settings = {
        "language": INPUT_OPTIONS[input_choice],
        "format": FORMAT_OPTIONS[format_choice],
        "keyterms": keyterms[:200]
    }

    fingerprint = hashlib.sha256(
        audio_bytes +
        json.dumps(
            settings,
            sort_keys=True,
            ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()


# ==========================================
# TRANSCRIBE
# ==========================================

if st.button(
    label("Transcribe with Gnani", "Gnani से लिखें", "Gnaniతో లిప్యంతరీకరించండి"),
    type="primary",
    disabled=audio_bytes is None
):
    st.session_state.pop("latest_result", None)

    try:
        api_key = st.secrets["GNANI_API_KEY"]
        duration = audio_duration(audio_bytes)

        if duration <= 0:
            st.error("Your recording is empty.")

        elif duration > 30:
            st.error(
                "Please record a clip shorter than 30 seconds."
            )

        elif len(audio_bytes) > 5 * 1024 * 1024:
            st.error("Audio file is too large.")

        else:
            with st.spinner(
                "Processing speech using Gnani..."
            ):
                result = call_gnani(
                    api_key=api_key,
                    audio_bytes=audio_bytes,
                    language_code=INPUT_OPTIONS[input_choice],
                    output_format=FORMAT_OPTIONS[format_choice],
                    keyterms=keyterms
                )

            transcript = result.get(
                "transcript", ""
            ).strip()

            if not transcript:
                st.warning(
                    "No speech recognized. "
                    "Please record again."
                )

            elif result.get("truncated"):
                st.warning(
                    "Gnani truncated this transcript. "
                    "Try a shorter recording."
                )

            else:
                st.session_state["latest_result"] = {
                    "fingerprint": fingerprint,
                    "draft_id": uuid4().hex,
                    "request_key": hashlib.sha256(audio_bytes).hexdigest(),
                    "transcript": transcript,
                    "detected_language": result.get(
                        "detected_language_code"
                    ),
                    "request_id": result.get(
                        "request_id"
                    )
                }

                st.success(
                    "Speech transcription completed!"
                )

    except (KeyError, FileNotFoundError):
        st.error("Set GNANI_API_KEY in .streamlit/secrets.toml to transcribe.")

    except requests.HTTPError as error:
        code = error.response.status_code
        if code in (402, 429):
            st.error(f"Gnani returned HTTP {code}. Check available credits and usage limits.")
        else:
            st.error(f"Gnani returned HTTP {code}. Check your account and settings.")

    except requests.RequestException:
        st.error(
            "Network error while contacting Gnani. "
            "Check your internet connection."
        )

    except (wave.Error, EOFError, ZeroDivisionError):
        st.error(
            "The recorded audio could not be read."
        )

    except ValueError:
        st.error(
            "Gnani returned an invalid or "
            "unsuccessful response."
        )


# ==========================================
# REVIEW AND LEDGER
# ==========================================

try:
    ledger = Ledger(Path(__file__).with_name("bhashakhata.sqlite3"))
    rows, balances = ledger.snapshot()
except sqlite3.Error:
    st.error("Ledger unavailable. Check local storage and retry.")
    st.stop()

saved_keys = {row["request_key"] for row in rows}
latest = st.session_state.get("latest_result")
kind_labels = {
    None: label("Choose a type", "प्रकार चुनें", "రకాన్ని ఎంచుకోండి"),
    "cash": label("Cash sale", "नकद बिक्री", "నగదు అమ్మకం"),
    "credit": label("Credit sale", "उधार बिक्री", "బాకీ అమ్మకం"),
    "repayment": label("Credit repayment", "उधार चुकौती", "బాకీ చెల్లింపు"),
}

if latest and latest["fingerprint"] == fingerprint:
    original = latest["transcript"]
    request_key = latest["request_key"]
    st.subheader(label("3. Original transcript", "3. मूल प्रतिलेख", "3. అసలు లిప్యంతరీకరణ"))
    st.text(original)
    st.download_button("Download original transcript", original, "bhashakhata_transcript.txt")
    with st.expander("Gnani API information"):
        st.write("Model · Prisma v3.0")
        st.text(latest.get("request_id") or "Request ID unavailable")
        if latest.get("detected_language"):
            st.text(latest["detected_language"])
    if request_key in saved_keys:
        st.info("This recording has already been saved.")
    else:
        suggestions = extract(original)
        draft = latest["draft_id"]
        with st.form(f"transaction_{draft}", clear_on_submit=False):
            st.subheader(label("4. Review transaction", "4. लेनदेन जाँचें", "4. లావాదేవీని తనిఖీ చేయండి"))
            customer = st.text_input(label("Customer", "ग्राहक", "కస్టమర్"), suggestions.get("customer", ""))
            kind = st.selectbox(label("Transaction type", "लेनदेन प्रकार", "లావాదేవీ రకం"),
                                [None, *KINDS], index=[None, *KINDS].index(suggestions.get("kind")),
                                format_func=kind_labels.__getitem__)
            product = st.text_input(label("Product (sales)", "उत्पाद (बिक्री)", "ఉత్పత్తి (అమ్మకం)"),
                                    suggestions.get("product", ""))
            quantity = st.text_input(label("Quantity (sales)", "मात्रा (बिक्री)", "పరిమాణం (అమ్మకం)"),
                                     suggestions.get("quantity", ""))
            amount = st.text_input(label("Total amount in rupees", "कुल राशि रुपये में", "మొత్తం రూపాయల్లో"),
                                   suggestions.get("amount", ""))
            confirmed = st.checkbox(label("I verified these details", "मैंने विवरण जाँच लिए हैं",
                                          "నేను వివరాలను తనిఖీ చేశాను"))
            submit = st.form_submit_button(label("Confirm and save", "पुष्टि करके सहेजें", "నిర్ధారించి సేవ్ చేయండి"))
            cancel = st.form_submit_button(label("Cancel", "रद्द करें", "రద్దు చేయండి"))
        if cancel:
            st.session_state.pop("latest_result")
            st.rerun()
        if submit:
            if not confirmed:
                st.warning("Verify the details and tick the confirmation box.")
            else:
                try:
                    inserted = ledger.save(request_key, original, customer, product, quantity, amount, kind)
                except ValueError as error:
                    if str(error) == "amount":
                        st.error("Enter a positive rupee amount with up to two decimal places.")
                    else:
                        st.error("Enter a customer and transaction type. Sales require a product and positive quantity.")
                except sqlite3.Error:
                    st.error("Save failed. Your draft is still available. Retry after checking storage.")
                else:
                    st.session_state["ledger_notice"] = "Transaction saved." if inserted else "Already saved."
                    st.rerun()
elif latest:
    st.info("Audio or settings changed. Transcribe again to review this recording.")

notice = st.session_state.pop("ledger_notice", None)
if notice:
    st.success(notice)


def rupees(paise):
    whole, fraction = divmod(abs(paise), 100)
    sign = "-" if paise < 0 else ""
    return f"{sign}₹{whole:,}.{fraction:02d}"


st.subheader(label("Customer balances", "ग्राहक शेष", "కస్టమర్ బాకీలు"))
if balances:
    st.dataframe([
        {label("Customer", "ग्राहक", "కస్టమర్"): name,
         label("Balance", "शेष", "బాకీ"): rupees(balance)}
        for name, balance in balances
    ], hide_index=True)
else:
    st.caption(label("No credit activity yet.", "अभी कोई उधार गतिविधि नहीं।", "ఇంకా బాకీ లావాదేవీలు లేవు."))

st.subheader(label("Transaction history", "लेनदेन इतिहास", "లావాదేవీల చరిత్ర"))
reversed_ids = {row["reversal_of"] for row in rows}
for row in rows:
    entry_id = row["id"]
    with st.expander(f'{row["created_at"]} UTC · {row["customer"]} · {kind_labels[row["kind"]]}'):
        st.text(f'{rupees(row["paise"])} · {row["quantity"]} {row["product"]}'.strip())
        st.text(entry_id)
        st.text(row["transcript"])
        if row["reversal_of"]:
            st.text(f'Reversal of {row["reversal_of"]}')
        elif entry_id in reversed_ids:
            st.caption("Reversed")
        elif st.button("Reverse this entry", key=f"reverse_{entry_id}"):
            try:
                ledger.reverse(entry_id)
            except sqlite3.Error:
                st.error("Reversal failed. Check storage and retry.")
            else:
                st.session_state["ledger_notice"] = "Reversal recorded."
                st.rerun()

st.caption("BhashaKhata | Powered by Gnani Prisma v3.0")
