
import hashlib
import io
import json
import wave

import requests
import streamlit as st
from deep_translator import GoogleTranslator


# -----------------------------------------
# 1. CONFIGURATION
# -----------------------------------------

st.set_page_config(
    page_title="BhashaKhata",
    page_icon="🛒",
    layout="centered"
)

GNANI_URL = "https://api.vachana.ai/stt/v3"

INPUT_LANGUAGES = {
    "Hindi + Telugu + English": "hi-IN,te-IN,en-IN",
    "Telugu + English": "te-IN,en-IN",
    "Hindi + English": "hi-IN,en-IN",
    "Hindi + Telugu": "hi-IN,te-IN",
    "Auto-detect": "indic-auto",
    "Only Telugu": "te-IN",
    "Only Hindi": "hi-IN",
    "Only English": "en-IN",
}

OUTPUT_LANGUAGES = {
    "English": "en",
    "తెలుగు (Telugu)": "te",
    "हिन्दी (Hindi)": "hi",
    "Original mixed-language text": None,
}

TRANSCRIPTION_STYLES = {
    "Mixed scripts (recommended for testing)": "codemix",
    "Numbers as digits (accounting)": "transcribe",
    "English letters (romanized)": "transliterate",
}

DEFAULT_KEYTERMS = (
    "rice, sugar, milk, Ramesh, "
    "రమేష్, బియ్యం, బాకీ, రూపాయలు, "
    "रमेश, चावल, उधार, रुपये, "
    "credit, payment"
)


# -----------------------------------------
# 2. READ PRIVATE API KEY
# -----------------------------------------

try:
    GNANI_API_KEY = st.secrets["GNANI_API_KEY"]
except Exception:
    st.error(
        "Gnani API key not found. "
        "Add GNANI_API_KEY to "
        ".streamlit/secrets.toml."
    )
    st.stop()


# -----------------------------------------
# 3. HELPER FUNCTIONS
# -----------------------------------------

def get_audio_duration(audio_bytes):
    """Return duration of a WAV recording in seconds."""
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def transcribe_audio(
    audio_bytes,
    language_code,
    output_format,
    keyterms
):
    """Send one short recording to Gnani Prisma v3.0."""

    payload = {
        "model": "prisma-v3.0",
        "language_code": language_code,
        "format": output_format,
        "topic": (
            "Indian Kirana shop transactions, "
            "customer credit, repayments, "
            "product quantities and rupee amounts"
        ),
    }

    if keyterms:
        payload["keyterms"] = json.dumps(
            keyterms[:200],
            ensure_ascii=False
        )

    response = requests.post(
        GNANI_URL,
        headers={
            "X-API-Key-ID": GNANI_API_KEY
        },
        files={
            "audio_file": (
                "transaction.wav",
                audio_bytes,
                "audio/wav"
            )
        },
        data=payload,
        timeout=(10, 60)
    )

    response.raise_for_status()

    result = response.json()

    if result.get("success") is not True:
        raise ValueError(
            "Gnani did not confirm successful transcription."
        )

    return result


def translate_text(text, target_language):
    """
    Prototype translation using an unofficial
    Google Translate interface.

    Do not use translated text as an authoritative
    financial record.
    """
    translator = GoogleTranslator(
        source="auto",
        target=target_language
    )

    return translator.translate(text)


# -----------------------------------------
# 4. APPLICATION HEADER
# -----------------------------------------

st.title("🛒 BhashaKhata")

st.write(
    "Your multilingual voice accounting assistant"
)

st.caption(
    "Speak in Telugu, Hindi, English, "
    "or a mixture of these languages."
)

st.divider()


# -----------------------------------------
# 5. LANGUAGE SETTINGS
# -----------------------------------------

st.subheader("1. Choose your languages")

input_choice = st.selectbox(
    "Languages you will speak",
    list(INPUT_LANGUAGES.keys()),
    index=0
)

output_choice = st.selectbox(
    "Language in which you want the output",
    list(OUTPUT_LANGUAGES.keys()),
    index=0
)

style_choice = st.selectbox(
    "Gnani transcription style",
    list(TRANSCRIPTION_STYLES.keys()),
    index=0
)

st.caption(
    "Changing the output language after transcription "
    "does not call Gnani again."
)


# -----------------------------------------
# 6. OPTIONAL ACCURACY HINTS
# -----------------------------------------

with st.expander("Improve recognition with shop vocabulary"):
    terms_text = st.text_input(
        "Customer names and product words (comma-separated)",
        value=DEFAULT_KEYTERMS
    )

    st.caption(
        "Use relevant names and product terms. "
        "Keyterms are hints, not guaranteed corrections."
    )

keyterms = [
    term.strip()
    for term in terms_text.split(",")
    if term.strip()
]


# -----------------------------------------
# 7. RECORD AUDIO
# -----------------------------------------

st.subheader("2. Record a transaction")

audio = st.audio_input(
    "Speak for up to 30 seconds",
    sample_rate=16000
)

audio_bytes = audio.getvalue() if audio else None

if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")


# -----------------------------------------
# 8. BUILD TRANSCRIPTION SIGNATURE
# -----------------------------------------

signature = None

if audio_bytes:
    audio_hash = hashlib.sha256(
        audio_bytes
    ).hexdigest()

    signature = (
        audio_hash,
        INPUT_LANGUAGES[input_choice],
        TRANSCRIPTION_STYLES[style_choice],
        tuple(keyterms[:200])
    )


# -----------------------------------------
# 9. CALL GNANI
# -----------------------------------------

if st.button(
    "🎤 Transcribe with Gnani",
    type="primary",
    disabled=audio_bytes is None
):
    # Never show an old result as a new result.
    st.session_state.pop("latest_result", None)

    try:
        duration = get_audio_duration(audio_bytes)

        if duration > 30:
            st.error(
                "Recording is longer than 30 seconds. "
                "Please record a shorter command."
            )

        elif duration <= 0:
            st.error("The recording is empty.")

        elif len(audio_bytes) > 5 * 1024 * 1024:
            st.error("Audio file is too large.")

        else:
            with st.spinner("Gnani is transcribing..."):
                result = transcribe_audio(
                    audio_bytes,
                    INPUT_LANGUAGES[input_choice],
                    TRANSCRIPTION_STYLES[style_choice],
                    keyterms
                )

            transcript = result.get(
                "transcript", ""
            ).strip()

            if not transcript:
                st.warning(
                    "No speech was recognized. "
                    "Try speaking more clearly."
                )

            else:
                st.session_state["latest_result"] = {
                    "signature": signature,
                    "transcript": transcript,
                    "language": result.get(
                        "detected_language_code"
                    ),
                    "request_id": result.get(
                        "request_id"
                    )
                }

                st.success(
                    "Transcription completed successfully!"
                )

    except requests.HTTPError as error:
        status = error.response.status_code
        st.error(
            f"Gnani returned HTTP {status}. "
            "Check your API access, settings and credits."
        )

    except requests.RequestException as error:
        st.error(
            f"Network error: {type(error).__name__}. "
            "Please check your connection."
        )

    except (wave.Error, EOFError, ZeroDivisionError):
        st.error(
            "Could not read the WAV recording."
        )

    except (ValueError, json.JSONDecodeError):
        st.error(
            "Gnani returned an invalid or unsuccessful result."
        )


# -----------------------------------------
# 10. SHOW ORIGINAL TRANSCRIPT
# -----------------------------------------

latest = st.session_state.get("latest_result")

if latest:
    if latest["signature"] != signature:
        st.info(
            "Recording or recognition settings changed. "
            "Click Transcribe with Gnani to process them."
        )

    else:
        original_text = latest["transcript"]

        st.divider()
        st.subheader("3. Transcription result")

        st.markdown("**Original Gnani transcription**")

        st.info(original_text)

        if latest.get("language"):
            st.caption(
                "Reported script/language: "
                + latest["language"]
            )

        st.caption(
            "The reported language code may describe "
            "only the dominant script, not every "
            "language spoken."
        )

        # ---------------------------------
        # 11. SELECTED OUTPUT LANGUAGE
        # ---------------------------------

        st.subheader("4. Your chosen language")

        target = OUTPUT_LANGUAGES[output_choice]

        display_text = original_text
        translation_ok = True

        if target is not None:
            if "translations" not in st.session_state:
                st.session_state["translations"] = {}

            cache_key = (
                original_text,
                target
            )

            translations = st.session_state["translations"]

            if cache_key not in translations:
                try:
                    with st.spinner(
                        "Translating the transcript..."
                    ):
                        translated = translate_text(
                            original_text,
                            target
                        )

                    if not translated:
                        raise ValueError("Empty translation")

                    translations[cache_key] = translated

                except Exception:
                    translation_ok = False

                    st.warning(
                        "Translation is unavailable. "
                        "The original transcript is shown below. "
                        "No new Gnani request was made."
                    )

            if cache_key in translations:
                display_text = translations[cache_key]
            else:
                translation_ok = False

        if translation_ok:
            output_id = hashlib.sha256(
                (original_text + str(target)).encode(
                    "utf-8"
                )
            ).hexdigest()[:16]

            st.text_area(
                "Output text (editable)",
                value=display_text,
                height=120,
                key=f"output_{output_id}"
            )

            final_text = st.session_state[
                f"output_{output_id}"
            ]

            st.download_button(
                "Download this text",
                data=final_text.encode("utf-8"),
                file_name="bhashakhata_transcript.txt",
                mime="text/plain"
            )

        else:
            st.write(original_text)

        st.warning(
            "Review customer names, quantities and "
            "rupee amounts against the recording. "
            "Translation can change their meaning."
        )

        with st.expander("API details"):
            st.write(
                "Model: prisma-v3.0"
            )
            st.write(
                "Request ID:",
                latest.get("request_id") or "Not provided"
            )

        st.caption(
            "Prototype only: nothing is saved "
            "to a financial ledger yet."
        )


# -----------------------------------------
# 12. FOOTER
# -----------------------------------------

st.divider()

st.caption(
    "BhashaKhata | Powered by Gnani Prisma v3.0"
)

st.caption(
    "Prototype translation uses a third-party service. "
    "Use fictional or consented recordings only."
)
