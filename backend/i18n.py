"""Backend i18n helper for API response messages."""

import json
from pathlib import Path
from typing import Optional

_locales = {}
_locale_dir = Path(__file__).parent / "locales"


def _load(locale: str) -> dict:
    if locale not in _locales:
        path = _locale_dir / f"{locale}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _locales[locale] = json.load(f)
        else:
            _locales[locale] = {}
    return _locales[locale]


def t(key: str, locale: str = "en", **kwargs) -> str:
    """Translate a key with optional interpolation. Falls back to English."""
    data = _load(locale)
    val = data.get(key)
    if val is None:
        val = _load("en").get(key, key)
    if kwargs:
        for k, v in kwargs.items():
            val = val.replace(f"{{{k}}}", str(v))
    return val


def detect_locale(accept_language: Optional[str]) -> str:
    """Pick best locale from Accept-Language header."""
    supported = {"en", "de", "es"}
    if not accept_language:
        return "en"
    for part in accept_language.split(","):
        lang = part.strip().split(";")[0].split("-")[0].lower()
        if lang in supported:
            return lang
    return "en"
