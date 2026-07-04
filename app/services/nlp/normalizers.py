from __future__ import annotations

import re
import unicodedata
from typing import Iterable


_LOWER_DASHES = "‐‑‒–—―"
_DASH_RE = re.compile(f"[{re.escape(_LOWER_DASHES)}]")
_WHITESPACE_RE = re.compile(r"\s+")

_UNIT_ALIASES: dict[str, str] = {
    "мг/л": "мг/л",
    "мг\\л": "мг/л",
    "г/л": "г/л",
    "г\\л": "г/л",
    "т/сут": "т/сут",
    "т/сут.": "т/сут",
    "т/день": "т/сут",
    "мпа": "МПа",
    "°c": "°C",
    "°с": "°C",
    "м/с": "м/с",
    "м/сек": "м/с",
    "м3/ч": "м³/ч",
    "м³/ч": "м³/ч",
    "м3/час": "м³/ч",
    "кг/т": "кг/т",
    "ppm": "ppm",
    "мг/кг": "мг/кг",
}

_RUSSIAN_UNIT_RE = re.compile(
    r"\b(" + "|".join(sorted({re.escape(k) for k in _UNIT_ALIASES}, key=len, reverse=True)) + r")\b",
    flags=re.IGNORECASE,
)

_DOMAIN_ABBREVIATIONS: dict[str, str] = {
    "пвп": "печь взвешенной плавки",
    "впвп": "печь взвешенной плавки",
    "кв": "кучное выщелачивание",
    "квв": "кучное выщелачивание",
    "ээ": "электроэкстракция",
    "ew": "электроэкстракция",
    "пзпу": "печь",
    "пв": "печь взвешенной плавки",
    "ниэ": "никель",
    "ни": "никель",
    "ау": "золото",
    "аг": "серебро",
    "мпг": "металлы платиновой группы",
    "пгм": "металлы платиновой группы",
    "сульф": "сульфаты",
    "хлор": "хлориды",
}


def normalize_whitespace(text: str) -> str:
    """Схлопывает любые пробелы/переносы строк в один пробел и триммит края."""
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_unicode(text: str, form: str = "NFKC") -> str:
    """Приводит юникод к нормальной форме (NFKC по умолчанию) — снимает
    проблемы неразличимых символов вроде кириллической «а» vs латинской «a»."""
    if not text:
        return ""
    return unicodedata.normalize(form, text)


def replace_dashes(text: str) -> str:
    """Заменяет разные виды тире и минусов на обычный '-'."""
    return _DASH_RE.sub("-", text)


def strip_punctuation(text: str, keep: str = "/°.%≤≥<>≈+-") -> str:
    """Удаляет пунктуацию, кроме символов, важных для чисел/единиц."""
    pattern = f"[^{re.escape(keep)}\\w\\s]"
    return re.sub(pattern, " ", text, flags=re.UNICODE)


def to_lower(text: str) -> str:
    return text.lower() if text else ""


def unify_units(text: str) -> str:
    """Приводит разные написания единиц к каноническому виду."""

    def _sub(match: re.Match) -> str:
        token = match.group(0).lower().replace(" ", "")
        return _UNIT_ALIASES.get(token, match.group(0))

    return _RUSSIAN_UNIT_RE.sub(_sub, text)


def normalize_numeric_separators(text: str) -> str:
    """Заменяет десятичные запятые на точки в числовых контекстах: '1,5' -> '1.5',
    '1 500' -> '1500' (только для чисел, не для произвольных пробелов)."""
    out = re.sub(r"(\d),(\d)", r"\1.\2", text)
    out = re.sub(r"(?<=\d)\s(?=\d{3}\b)", "", out)
    return out


def normalize_numbers_and_units(text: str) -> str:
    """Сквозная нормализация: '300 мг/л' -> '300 мг/л', '1,5 г/л' -> '1.5 г/л',
    '350 ° С' -> '350 °C'."""
    text = unify_units(text)
    text = re.sub(r"°\s*с\b", "°C", text, flags=re.IGNORECASE)
    text = normalize_numeric_separators(text)
    return text


def expand_abbreviations(text: str) -> str:
    """Раскрывает отраслевые аббревиатуры (ПВП, КВ, ЭЭ, МПГ и т.д.).
    Делает только безопасные замены — целыми словами, с границами."""
    tokens = re.split(r"(\s+)", text)
    result: list[str] = []
    for tok in tokens:
        if not tok or tok.isspace():
            result.append(tok)
            continue
        normalized = tok.strip(".,;:()").lower()
        expansion = _DOMAIN_ABBREVIATIONS.get(normalized)
        if expansion is not None:
            leading = tok[: len(tok) - len(tok.lstrip(".,;:()"))]
            trailing = tok[len(tok.rstrip(".,;:()")) :]
            result.append(f"{leading}{expansion}{trailing}")
        else:
            result.append(tok)
    return "".join(result)


def normalize_full(
    text: str,
    *,
    lower: bool = True,
    strip_punct: bool = False,
    expand_abbr: bool = True,
) -> str:

    if not text:
        return ""
    text = normalize_unicode(text)
    text = replace_dashes(text)
    text = normalize_numbers_and_units(text)
    if expand_abbr:
        text = expand_abbreviations(text)
    if strip_punct:
        text = strip_punctuation(text)
    if lower:
        text = to_lower(text)
    return normalize_whitespace(text)


def split_sentences(text: str) -> list[str]:
    """Простое разбиение на предложения для дальнейшей обработки."""
    if not text:
        return []
    raw = re.split(r"(?<=[.!?…])\s+(?=[А-ЯЁA-Z])", text.strip())
    return [s.strip() for s in raw if s.strip()]


def iter_chunks(text: str, max_len: int = 500, overlap: int = 50) -> Iterable[str]:
    """Нарезает длинный текст на чанки фиксированной длины с перехлёстом.
    Используется, чтобы длинные отчёты не ломали NER/парсер."""
    if not text or max_len <= 0:
        return
    step = max(1, max_len - overlap)
    for start in range(0, len(text), step):
        piece = text[start : start + max_len]
        if piece:
            yield piece
