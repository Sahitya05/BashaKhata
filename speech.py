"""Gnani REST adapter; official request fields checked 2026-11-04."""
import hashlib
import io
import json
import wave
import requests

INPUT_OPTIONS = {"Telugu": "te-IN", "Hindi": "hi-IN", "English": "en-IN",
                 "Telugu + Hindi": "te-IN,hi-IN", "Telugu + English": "te-IN,en-IN",
                 "Hindi + English": "hi-IN,en-IN", "Telugu + Hindi + English": "te-IN,hi-IN,en-IN",
                 "Automatic detection": "indic-auto"}

def transcribe(api_key, audio, language, terms=(), cache=None):
    if not api_key:
        raise ValueError("missing_key")
    if not audio or len(audio) > 5 * 1024 * 1024:
        raise ValueError("audio")
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            duration = wav.getnframes() / wav.getframerate()
            if not 0 < duration <= 30:
                raise ValueError("audio")
    except (wave.Error, EOFError, ZeroDivisionError) as exc:
        raise ValueError("audio") from exc
    settings = {"model": "prisma-v3.0", "language_code": language,
                "format": "codemix" if "," in language or language == "indic-auto" else "transcribe",
                "topic": "Indian shop transactions, customer credit, repayments and shop borrowing"}
    if terms:
        settings["keyterms"] = json.dumps(list(terms)[:200], ensure_ascii=False)
    fingerprint = hashlib.sha256(audio + json.dumps(settings, sort_keys=True).encode()).hexdigest()
    if cache is not None and fingerprint in cache:
        return cache[fingerprint]
    response = requests.post("https://api.vachana.ai/stt/v3", headers={"X-API-Key-ID": api_key},
                             files={"audio_file": ("transaction.wav", audio, "audio/wav")},
                             data=settings, timeout=60)
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict) or result.get("success") is not True or not isinstance(result.get("transcript"), str):
        raise ValueError("response")
    if not result["transcript"].strip() or result.get("truncated"):
        raise ValueError("truncated_or_empty")
    result = {"transcript": result["transcript"], "request_id": result.get("request_id"),
              "request_key": hashlib.sha256(audio).hexdigest(), "duration": duration}
    if cache is not None:
        if len(cache) >= 20:
            cache.pop(next(iter(cache)))
        cache[fingerprint] = result
    return result
