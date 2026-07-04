"""Верхний уровень NLP-сервиса.

Содержит функции, которые:
- читают файл (txt/docx/pdf) и достают текст;
- прогоняют текст через словарные экстракторы;
- собирают `ExtractionResult` с разнесёнными по полям сущностями (entities,
  numbers, geography, years, experts) и тройками (triples).

Глобальный пайплайн создаётся один раз и переиспользуется.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.services.nlp.extractors import (
    RelationExtractor,
    get_default_pipeline,
)

from app.services.nlp.models import Entity, ExtractionResult, Triple
from app.utils.file_parsers import parse_file

logger = logging.getLogger(__name__)


_extractors: list | None = None
_resolver = None
_relation_extractor: RelationExtractor | None = None


def _init_pipeline() -> None:
    global _extractors, _resolver, _relation_extractor
    if _extractors is None:
        _extractors, _resolver, _relation_extractor = get_default_pipeline()


def _run_extractors(text: str) -> list[Entity]:
    """Прогоняет текст через все экстракторы и схлопывает синонимы."""
    _init_pipeline()
    assert _extractors is not None and _resolver is not None
    all_hits: list[Entity] = []
    for ex in _extractors:
        all_hits.extend(ex.extract(text))
    return _resolver.collapse(all_hits)


def _dedup(entities: list[Entity]) -> list[Entity]:
    seen: set[tuple[str, str]] = set()
    unique: list[Entity] = []
    for ent in entities:
        key = (ent.text.lower(), ent.label)
        if key in seen:
            continue
        seen.add(key)
        unique.append(ent)
    return unique


def extract_entities(text: str) -> list[Entity]:
    """Словарные сущности (Process/Material/Equipment/Geography/Year/Expert).

    Числовые ограничения сюда не попадают — они идут в `extract_numbers` /
    `ExtractionResult.numbers`.
    """
    collapsed = _run_extractors(text)
    return _dedup(
        [e for e in collapsed if e.label != "numeric_constraint"]
    )


def extract_numbers(text: str) -> list[Entity]:
    """Числовые ограничения: «сульфаты ≤300 мг/л», «350 °C» и т.п."""
    _init_pipeline()
    assert _extractors is not None
    numeric = next((ex for ex in _extractors if getattr(ex, "name", None) == "numeric"), None)
    if numeric is None:
        return []
    return numeric.extract(text)


def extract_triples(text: str) -> list[Triple]:
    """Тройки (субъект-предикат-объект) по шаблонам «X применяется для Y»."""
    _init_pipeline()
    assert _relation_extractor is not None
    entities = extract_entities(text)
    return _relation_extractor.extract(text, entities=entities)


def _split_special_labels(entities: list[Entity]) -> dict[str, list[Entity]]:
    special_labels = {"geography", "year", "expert"}
    out: dict[str, list[Entity]] = {label: [] for label in special_labels}
    filtered: list[Entity] = []
    for e in entities:
        if e.label in special_labels:
            out[e.label].append(e)
        else:
            filtered.append(e)
    return {**out, "_main": filtered}


def _detect_language(text: str) -> str:
    if not text:
        return "ru"
    cyrillic = sum(1 for c in text if "Ѐ" <= c <= "ӿ")
    return "ru" if cyrillic > len(text) * 0.05 else "en"


def extract_from_text(text: str) -> ExtractionResult:
    """Полный прогон текста: сущности + числа + тройки."""
    all_entities = extract_entities(text)
    numbers = extract_numbers(text)
    triples = extract_triples(text)

    parts = _split_special_labels(all_entities)

    return ExtractionResult(
        entities=parts["_main"],
        triples=triples,
        numbers=numbers,
        geography=parts["geography"],
        years=parts["year"],
        experts=parts["expert"],
        source_text=text,
        language=_detect_language(text),
    )


def extract_from_file(file_path: str | Path) -> ExtractionResult:
    """Читает файл через `parse_file` и прогоняет через пайплайн."""
    text = parse_file(file_path)
    if not text:
        logger.warning("Empty text from %s", file_path)
    return extract_from_text(text)
