
import streamlit as st
import requests

st.set_page_config(page_title="BhashaKhata")
st.title("BhashaKhata")
st.write("Your multilingual voice accounting assistant")

audio = st.audio_input(
    "Record a short transaction",
    sample_rate=16000
)

if audio is not None:
    st.audio(audio)

    if st.button("Transcribe with Gnani"):
        try:
            with st.spinner("Transcribing..."):
                response = requests.post(
                    "https://api.vachana.ai/stt/v3",
                    headers={
                        "X-API-Key-ID": st.secrets[
                            "GNANI_API_KEY"
                        ]
                    },
                    files={
                        "audio_file": (
                            "transaction.wav",
                            audio.getvalue(),
                            "audio/wav"
                        )
                    },
                    data={
                        "model": "prisma-v3.0",
                        "language_code": "indic-auto",
                        "format": "transcribe"
                    },
                    timeout=60
                )

                response.raise_for_status()
                result = response.json()

            if result.get("success"):
                transcript = result.get("transcript", "")
                st.subheader("Transcription")
                st.write(transcript or "No speech detected.")
            else:
                st.error("Transcription was unsuccessful.")

        except requests.RequestException as error:
            st.error(f"API request failed: {error}")
