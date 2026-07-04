"""Экстракторы для NLP-пайплайна.

Каждый экстрактор — обычный класс с методом `extract(text, language) -> list[Entity]`.
Протокол/ABC не используется, потому что у нас один набор реализаций
и `isinstance`-проверки нигде не нужны.

Перед поиском текст прогоняется через `normalizers.normalize_full`, чтобы
унифицировать регистр, тире, единицы измерения, аббревиатуры.
"""

from __future__ import annotations

import re
from typing import Iterable

from app.services.nlp.models import Entity, Triple
from app.services.nlp.normalizers import (
    normalize_full,
    normalize_numbers_and_units,
    normalize_whitespace,
)


_OP_MAP = {"≤": "<=", "≥": ">=", "~": "≈", "=": "="}


def _normalize_op(op: str | None) -> str:
    if not op:
        return "="
    return _OP_MAP.get(op, op)


def _normalize_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    u = unit.replace(" ", "").lower()
    u = u.replace("°c", "°C").replace("°с", "°C")
    u = u.replace("м3/ч", "м³/ч").replace("м3/час", "м³/ч")
    return u


_NUMERIC_RE = re.compile(
    r"(?P<op><=|>=|≤|≥|<|>|≈|=|~)?\s*"
    r"(?P<value>\d+(?:[.,]\d+)?)"
    r"(?:\s*[eE×xX]?\s*10\s*\^?\s*-?\d+)?"
    r"\s*"
    r"(?P<unit>мг/л|мг\\л|г/л|г\\л|т/сут|т/день|МПа|мПа|°\s*[ССCc]?|м/с|м/сек|м³/ч|м3/ч|м3/час|кг/т|ppm|мг/кг|%)?",
    flags=re.UNICODE,
)


class NumericExtractor:
    name = "numeric"

    def extract(self, text: str, language: str = "ru") -> list[Entity]:
        canonical = normalize_numbers_and_units(text)
        hits: list[Entity] = []
        for m in _NUMERIC_RE.finditer(canonical):
            raw = m.group("value")
            if not raw:
                continue
            try:
                value = float(raw.replace(",", "."))
            except ValueError:
                continue
            unit = _normalize_unit(m.group("unit"))
            op = _normalize_op(m.group("op"))
            hits.append(
                Entity(
                    text=f"{op}{value}" + (f" {unit}" if unit else ""),
                    label="numeric_constraint",
                    attributes={"value": value, "unit": unit, "op": op, "raw": m.group(0).strip()},
                    confidence=0.95,
                    span=m.span(),
                )
            )
        return hits


_PROCESS_TERMS: dict[str, str] = {
    "электроэкстракция",
    "электролиз",
    "обессоливание",
    "кучное выщелачивание",
    "выщелачивание",
    "флотация",
    "обжиг",
    "плавка",
    "взвешенная плавка",
    "очистка",
    "циркуляция",
}

_MATERIAL_TERMS: dict[str, str] = {
    "никель",
    "медь",
    "кобальт",
    "золото",
    "серебро",
    "железо",
    "гипс",
    "сульфаты",
    "хлориды",
    "католит",
    "анолит",
    "электролит",
    "шихта",
    "штейн",
    "шлак",
    "катод",
}

_EQUIPMENT_TERMS: dict[str, str] = {
    "печь взвешенной плавки",
    "пвп",
    "электролизёр",
    "электролизная ванна",
    "диафрагменная ячейка",
    "фильтр-пресс",
    "мельница",
    "сгуститель",
}


def _find_terms(text: str, terms: Iterable[str]) -> Iterable[tuple[str, str, tuple[int, int]]]:
    target = text.lower()
    for canonical in terms:
        start = 0
        while True:
            idx = target.find(canonical, start)
            if idx < 0:
                break
            yield canonical, text[idx : idx + len(canonical)], (idx, idx + len(canonical))
            start = idx + len(canonical)


class DictionaryEntityExtractor:
    """Достаёт сущности из доменных словарей (RU + EN синонимы)."""

    name = "dictionary"

    def __init__(self) -> None:
        self._groups: list[tuple[str, str, Iterable[str]]] = [
            ("Process", "Process", _PROCESS_TERMS),
            ("Material", "Material", _MATERIAL_TERMS),
            ("Equipment", "Equipment", _EQUIPMENT_TERMS),
        ]

    def extract(self, text: str, language: str = "ru") -> list[Entity]:
        normalized = normalize_full(text, lower=True, expand_abbr=True)
        hits: list[Entity] = []
        for type_name, ontology, terms in self._groups:
            for canonical, surface, span in _find_terms(normalized, terms):
                hits.append(
                    Entity(
                        text=canonical,
                        label=type_name,
                        attributes={"surface": surface, "ontology": ontology},
                        confidence=0.9,
                        span=span,
                    )
                )
        return hits


class SynonymResolver:
    """Схлопывает синонимы разных языков в одну каноническую сущность.

    «electrowinning» и «электроэкстракция» дают одну запись с самым длинным
    именем в группе.
    """

    name = "synonyms"

    _SYNONYM_GROUPS: list[set[str]] = [
        {"электроэкстракция", "electrowinning", "ew", "ээ"},
        {"кучное выщелачивание", "heap leaching", "кв", "квв"},
        {"выщелачивание", "leaching"},
        {"печь взвешенной плавки", "fluidized bed furnace", "пвп", "впвп", "пв"},
        {"никель", "ni", "ни", "ниэ"},
        {"золото", "au", "ау"},
        {"серебро", "ag", "аг"},
        {"сульфаты", "sulfates", "сульф"},
        {"хлориды", "chlorides", "хлор"},
    ]

    def canonical(self, term: str) -> str:
        t = term.lower().strip()
        for group in self._SYNONYM_GROUPS:
            if t in group:
                return sorted(group, key=len, reverse=True)[0]
        return term

    def collapse(self, hits: list[Entity]) -> list[Entity]:
        seen: dict[tuple[str, str], Entity] = {}
        for hit in hits:
            key = (hit.label, self.canonical(hit.text))
            if key not in seen or hit.confidence > seen[key].confidence:
                seen[key] = Entity(
                    text=key[1],
                    label=hit.label,
                    attributes=hit.attributes,
                    confidence=hit.confidence,
                    span=hit.span,
                )
        return list(seen.values())


_GEOGRAPHY: dict[str, str] = {
    "россия": "RU",
    "рф": "RU",
    "норникель": "RU",
    "норильск": "RU",
    "красноярск": "RU",
    "мурманск": "RU",
    "кольский": "RU",
    "канада": "CA",
    "австралия": "AU",
    "финляндия": "FI",
    "чили": "CL",
    "перу": "PE",
    "юар": "ZA",
    "южная африка": "ZA",
    "сша": "US",
    "германия": "DE",
    "китай": "CN",
    "казахстан": "KZ",
}

_REGION_KEYWORDS: dict[str, str] = {
    "холодный климат": "cold_climate",
    "арктика": "cold_climate",
    "арктический": "cold_climate",
    "тундра": "cold_climate",
}


class GeographyExtractor:
    name = "geography"

    def extract(self, text: str, language: str = "ru") -> list[Entity]:
        hits: list[Entity] = []
        for name, code in _GEOGRAPHY.items():
            for m in re.finditer(rf"\b{re.escape(name)}\b", text, flags=re.IGNORECASE):
                hits.append(
                    Entity(
                        text=text[m.start() : m.end()],
                        label="geography",
                        attributes={"code": code, "kind": "country", "canonical": name},
                        confidence=0.95,
                        span=m.span(),
                    )
                )
        for keyword, tag in _REGION_KEYWORDS.items():
            for m in re.finditer(rf"\b{re.escape(keyword)}\b", text, flags=re.IGNORECASE):
                hits.append(
                    Entity(
                        text=text[m.start() : m.end()],
                        label="geography",
                        attributes={"code": tag, "kind": "region", "canonical": keyword},
                        confidence=0.8,
                        span=m.span(),
                    )
                )
        return hits


_YEAR_RE = re.compile(r"\b(19[5-9]\d|20\d{2})\b")


class YearExtractor:
    name = "year"

    def extract(self, text: str, language: str = "ru") -> list[Entity]:
        hits: list[Entity] = []
        for m in _YEAR_RE.finditer(text):
            hits.append(
                Entity(
                    text=m.group(1),
                    label="year",
                    attributes={"year": int(m.group(1))},
                    confidence=0.99,
                    span=m.span(),
                )
            )
        return hits


class ExpertExtractor:
    """Грубый эвристический поиск упоминаний авторов/экспертов.

    Полноценное NER-извлечение имён делает spacy/DeepPavlov;
    здесь — fallback на простые паттерны:
        - «Иванов И. И.», «Иванов И.И.», «И. И. Иванов»
        - «Иванов, И.И.», «Иванов, И. И.»
        - латиница: «Ivanov I. I.», «Ivanov I.I.»
    """

    name = "expert"

    _INIT = r"[А-ЯЁ]\.\s?[А-ЯЁ]\."
    _INIT_LATIN = r"[A-Z]\.\s?[A-Z]\."
    _TAIL = r"(?=[\s,\.;:\)\]]|$)"
    _FIO = re.compile(rf"\b([А-ЯЁ][а-яё]+)\s+(?P<init>{_INIT}){_TAIL}")
    _FIO_REV = re.compile(rf"\b([А-ЯЁ][а-яё]+),\s*(?P<init>{_INIT}){_TAIL}")
    _FIO_LEAD = re.compile(rf"(?P<init>{_INIT})\s+([А-ЯЁ][а-яё]+){_TAIL}")
    _FIO_LATIN = re.compile(rf"\b([A-Z][a-z]+)\s+(?P<init>{_INIT_LATIN}){_TAIL}")

    def extract(self, text: str, language: str = "ru") -> list[Entity]:
        hits: list[Entity] = []
        for pattern, kind in (
            (self._FIO, "fio"),
            (self._FIO_REV, "fio"),
            (self._FIO_LEAD, "fio"),
            (self._FIO_LATIN, "fio_en"),
        ):
            for m in pattern.finditer(text):
                surface = normalize_whitespace(m.group(0))
                hits.append(
                    Entity(
                        text=surface,
                        label="expert",
                        attributes={"kind": kind},
                        confidence=0.7,
                        span=m.span(),
                    )
                )
        return hits


class RelationExtractor:
    """Извлекает простые текстовые связи «X применяется для Y», «X показал Y»."""

    name = "relation"

    # Глаголы/предлоги, на которых обрезаем жадный source/target, чтобы не
    # захватить весь фрагмент между двумя подряд идущими предикатами.
    _BOUNDARY = re.compile(
        r"\b(?:применяется|применяют|применялся|применялись|показала|показал|показали|"
        r"используется|используют|использовался|использовались|применяется|"
        r"для|в|что|а|но|или|и)\b",
        flags=re.IGNORECASE,
    )

    _PATTERNS: list[tuple[str, str, re.Pattern]] = [
        (
            "uses_for",
            r"применя(?:ется|ют|лся|лись)\s+(?:для|в)\s+",
            re.compile(
                r"(?P<source>[А-ЯЁа-яёA-Za-z\- ]{2,60}?)\s+"
                r"применя(?:ется|ют|лся|лись)\s+(?:для|в)\s+"
                r"(?P<target>[А-ЯЁа-яёA-Za-z\- ]{2,60}?)(?=[\.\,\;\n]|$)",
                flags=re.IGNORECASE,
            ),
        ),
        (
            "showed",
            r"показал[аи]?\s+(?:что\s+)?",
            re.compile(
                r"(?P<source>[А-ЯЁа-яёA-Za-z\- ]{2,60}?)\s+"
                r"показал[аи]?\s+(?:что\s+)?"
                r"(?P<target>[А-ЯЁа-яёA-Za-z\- ]{2,60}?)(?=[\.\,\;\n]|$)",
                flags=re.IGNORECASE,
            ),
        ),
    ]

    def extract(
        self,
        text: str,
        language: str = "ru",
        entities: list[Entity] | None = None,
    ) -> list[Triple]:
        entities = entities or []
        triples: list[Triple] = []
        for rel_type, _bound, pattern in self._PATTERNS:
            for m in pattern.finditer(text):
                source = self._clip(m.group("source"))
                target = self._clip(m.group("target"))
                src_hit = self._match_entity(source, entities)
                tgt_hit = self._match_entity(target, entities)
                if not src_hit or not tgt_hit:
                    continue
                triples.append(
                    Triple(
                        subject=src_hit,
                        predicate=rel_type,
                        object=tgt_hit,
                        confidence=0.6,
                        span=m.span(),
                    )
                )
        return triples

    @classmethod
    def _clip(cls, fragment: str) -> str:
        """Обрезает жадный фрагмент по стоп-словам/предлогам."""
        text = normalize_whitespace(fragment)
        m = cls._BOUNDARY.search(text)
        if m:
            text = text[: m.start()].strip()
        return text

    @staticmethod
    def _match_entity(text_value: str, entities: list[Entity]) -> str | None:
        t = text_value.lower().strip()
        best: str | None = None
        best_len = 0
        for e in entities:
            name = (e.attributes.get("surface") or e.text).lower()
            if name in t and len(name) > best_len:
                best = e.text
                best_len = len(name)
        return best


def get_default_extractors() -> list:
    """Собирает дефолтный набор экстракторов в порядке выполнения."""
    return [
        DictionaryEntityExtractor(),
        GeographyExtractor(),
        YearExtractor(),
        ExpertExtractor(),
        NumericExtractor(),
    ]


def get_default_pipeline() -> tuple[list, SynonymResolver, RelationExtractor]:
    extractors = get_default_extractors()
    resolver = SynonymResolver()
    relations = RelationExtractor()
    return extractors, resolver, relations
