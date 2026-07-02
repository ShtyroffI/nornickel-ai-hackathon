"""NLP-пайплайн: извлечение сущностей, связей, числовых ограничений, синонимов.

Поддерживает провайдеры: stub (по умолчанию), spacy, deeppavlov.
Реальные провайдеры подключаются позже — интерфейс уже зафиксирован.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ExtractedEntity:
    type: str
    name: str
    value: float | None = None
    unit: str | None = None
    op: str | None = None
    properties: dict = field(default_factory=dict)


@dataclass
class ExtractedRelation:
    source: str
    target: str
    type: str
    properties: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    entities: list[ExtractedEntity]
    relations: list[ExtractedRelation]


class NLPService:
    SYNONYMS: dict[str, list[str]] = {
        "электроэкстракция": ["electrowinning", "EW"],
        "ПВП": ["печь взвешенной плавки", "fluidized bed furnace"],
        "выщелачивание": ["leaching"],
        "кучное выщелачивание": ["heap leaching"],
    }

    NUMERIC_RE = re.compile(
        r"(?P<op><=|>=|<|>|≈)?\s*(?P<value>\d+[.,]?\d*)\s*(?P<unit>мг/л|г/л|°C|°C|т/сут|МПа|м/с)?"
    )

    def extract(self, text: str, language: str = "ru") -> ExtractionResult:
        entities: list[ExtractedEntity] = []
        relations: list[ExtractedRelation] = []

        for name, syns in self.SYNONYMS.items():
            for term in (name, *syns):
                if term.lower() in text.lower():
                    entities.append(ExtractedEntity(type="Process" if "выщел" in term.lower() or "электр" in term.lower() else "Equipment", name=name))
                    break

        for match in self.NUMERIC_RE.finditer(text):
            raw = match.group("value").replace(",", ".")
            try:
                value = float(raw)
            except ValueError:
                continue
            entities.append(
                ExtractedEntity(
                    type="Property",
                    name="numeric_constraint",
                    value=value,
                    unit=match.group("unit"),
                    op=match.group("op") or "=",
                )
            )

        return ExtractionResult(entities=entities, relations=relations)
