"""Official Azure Translator; cache successful results within one user session."""
from typing import Protocol
import requests

class Translator(Protocol):
    def translate(self, text: str, target: str) -> str: ...

class AzureTranslator:
    def __init__(self, key, region, cache=None):
        self.key, self.region = key, region
        self.cache = cache if cache is not None else {}

    def translate(self, text, target):
        if not self.key:
            raise ValueError("translation_unavailable")
        if target not in ("en", "hi", "te") or not text.strip():
            raise ValueError("translation_input")
        cache_key = (text, target)
        if cache_key in self.cache:
            return self.cache[cache_key]
        response = requests.post("https://api.cognitive.microsofttranslator.com/translate",
                                 params={"api-version": "3.0", "to": target},
                                 headers={"Ocp-Apim-Subscription-Key": self.key, "Ocp-Apim-Subscription-Region": self.region},
                                 json=[{"Text": text}], timeout=25)
        response.raise_for_status()
        try:
            translated = response.json()[0]["translations"][0]["text"]
            if not isinstance(translated, str) or not translated.strip():
                raise ValueError("translation_response")
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("translation_response") from exc
        if len(self.cache) >= 40:
            self.cache.pop(next(iter(self.cache)))
        self.cache[cache_key] = translated
        return translated
