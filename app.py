
import hashlib
import io
import json
import wave

import requests
import streamlit as st
from deep_translator import GoogleTranslator


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

OUTPUT_OPTIONS = {
    "Original mixed-language transcript": None,
    "English": "en",
    "Telugu (తెలుగు)": "te",
    "Hindi (हिन्दी)": "hi"
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
# API KEY
# ==========================================

try:
    API_KEY = st.secrets["GNANI_API_KEY"]
except Exception:
    st.error(
        "Gnani API key is missing. "
        "Check .streamlit/secrets.toml"
    )
    st.stop()


# ==========================================
# FUNCTIONS
# ==========================================

def audio_duration(audio_bytes):
    """Read duration of a WAV recording."""
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
        return (
            wav.getnframes() /
            wav.getframerate()
        )


def call_gnani(
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
            "X-API-Key-ID": API_KEY
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

    if result.get("success") is not True:
        raise ValueError(
            "Gnani did not complete transcription."
        )

    return result


def translate_transcript(text, target):
    """Translate text using a third-party service."""

    result = GoogleTranslator(
        source="auto",
        target=target
    ).translate(text)

    if not isinstance(result, str) or not result.strip():
        raise ValueError("Empty translation")

    return result


# ==========================================
# APPLICATION UI
# ==========================================

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

st.subheader("1. Language settings")

input_choice = st.selectbox(
    "Which languages will you speak?",
    list(INPUT_OPTIONS.keys()),
    index=0
)

output_choice = st.selectbox(
    "Which language should display the result?",
    list(OUTPUT_OPTIONS.keys()),
    index=0
)

format_choice = st.selectbox(
    "Speech recognition format",
    list(FORMAT_OPTIONS.keys()),
    index=0
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
st.subheader("2. Record transaction")

audio = st.audio_input(
    "Speak a transaction (maximum 30 seconds)",
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
    "Transcribe with Gnani",
    type="primary",
    disabled=audio_bytes is None
):
    st.session_state.pop("latest_result", None)

    try:
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

    except requests.HTTPError as error:
        code = error.response.status_code
        st.error(
            f"Gnani API returned HTTP {code}. "
            "Check your account, settings and credits."
        )

    except requests.RequestException:
        st.error(
            "Network error while contacting Gnani. "
            "Check your internet connection."
        )

    except (wave.Error, EOFError, ZeroDivisionError):
        st.error(
            "The recorded audio could not be read."
        )

    except (ValueError, json.JSONDecodeError):
        st.error(
            "Gnani returned an invalid or "
            "unsuccessful response."
        )


# ==========================================
# DISPLAY TRANSCRIPTION
# ==========================================

latest = st.session_state.get("latest_result")

if latest is not None:

    if latest["fingerprint"] != fingerprint:
        st.info(
            "Audio or recognition settings changed. "
            "Click Transcribe with Gnani again."
        )

    else:
        st.divider()
        st.subheader("3. Original Gnani transcription")

        original = latest["transcript"]

        st.text_area(
            "Recognized speech",
            value=original,
            height=130,
            disabled=True
        )

        language = latest.get("detected_language")

        if language:
            st.caption(
                f"Reported transcript language: {language}"
            )

        st.caption(
            "The language label may represent the "
            "dominant script, not every spoken language."
        )

        # ==================================
        # CHOOSE OUTPUT LANGUAGE
        # ==================================

        st.divider()
        st.subheader("4. Selected output language")

        target = OUTPUT_OPTIONS[output_choice]

        if "translation_cache" not in st.session_state:
            st.session_state["translation_cache"] = {}

        cache = st.session_state["translation_cache"]

        cache_key = (original, target)

        displayed_text = original
        output_ready = True

        if target is not None:

            st.info(
                "Translation uses a third-party service. "
                "Use fictional or consented data only."
            )

            if cache_key not in cache:
                if st.button(
                    "Translate to " + output_choice
                ):
                    try:
                        with st.spinner(
                            "Translating..."
                        ):
                            cache[cache_key] = (
                                translate_transcript(
                                    original,
                                    target
                                )
                            )

                        st.success("Translation completed.")

                    except Exception:
                        st.error(
                            "Translation failed. "
                            "Try again or use the "
                            "original transcript."
                        )

            if cache_key in cache:
                displayed_text = cache[cache_key]
            else:
                output_ready = False
                st.caption(
                    "Click Translate to generate "
                    "the selected language."
                )

        # ==================================
        # EDIT AND EXPORT DISPLAYED TEXT
        # ==================================

        if output_ready:

            editor_id = hashlib.sha256(
                (
                    latest["fingerprint"] +
                    str(target)
                ).encode("utf-8")
            ).hexdigest()[:16]

            editor_key = "editor_" + editor_id

            if editor_key not in st.session_state:
                st.session_state[editor_key] = displayed_text

            edited_text = st.text_area(
                "Review or edit displayed text",
                key=editor_key,
                height=130
            )

            st.download_button(
                "Download reviewed text",
                data=edited_text.encode("utf-8"),
                file_name="bhashakhata_transcript.txt",
                mime="text/plain"
            )

            st.warning(
                "Always verify names, quantities "
                "and rupee amounts against the audio. "
                "Translated text is not a verified "
                "financial transaction."
            )

        with st.expander("Gnani API information"):
            st.write("Model: Prisma v3.0")
            st.write(
                "Request ID:",
                latest.get("request_id") or "Not provided"
            )

        st.caption(
            "Milestone 2: transcription and language "
            "display only. No ledger transaction is saved."
        )


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "BhashaKhata | Powered by Gnani Prisma v3.0"
)
