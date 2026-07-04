"""Доменные модели NLP: сущности, связи, результат извлечения."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Entity:
    text: str
    label: str
    attributes: dict = field(default_factory=dict)
    confidence: float = 1.0
    span: tuple[int, int] = (-1, -1)


@dataclass
class Triple:
    subject: str
    predicate: str
    object: str
    attributes: dict = field(default_factory=dict)
    confidence: float = 1.0
    span: tuple[int, int] = (-1, -1)


@dataclass
class ExtractionResult:
    entities: list[Entity] = field(default_factory=list)
    triples: list[Triple] = field(default_factory=list)
    numbers: list[Entity] = field(default_factory=list)
    geography: list[Entity] = field(default_factory=list)
    years: list[Entity] = field(default_factory=list)
    experts: list[Entity] = field(default_factory=list)
    source_text: str = ""
    language: str = "ru"
