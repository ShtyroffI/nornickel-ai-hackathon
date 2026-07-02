"""Семантический поиск с многоуровневой фильтрацией и числовыми диапазонами.

Заглушка интерфейса — реальный бэкенд (Elasticsearch/Vespa) подключается позже.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchFilters:
    geography: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    min_confidence: float | None = None
    depth: int = 3


class SearchService:
    def search(self, text: str, filters: SearchFilters) -> dict:
        return {
            "query": text,
            "filters": filters.__dict__,
            "results": [],
            "took_ms": 0,
        }
