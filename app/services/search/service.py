"""Семантический поиск с многоуровневой фильтрацией и числовыми диапазонами.

Здесь реализован GraphRAG: извлечение подграфа из Neo4j по ключевым словам и генерация ответа через YandexGPT.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.db.neo4j.driver import get_neo4j

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    geography: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    min_confidence: float | None = None
    depth: int = 3


class SearchService:
    def __init__(self) -> None:
        self.driver = get_neo4j()
        self.settings = get_settings()
        self.client = OpenAI(
            api_key=self.settings.yandex_api_key,
            base_url="https://llm.api.cloud.yandex.net/v1"
        )
        self.model_uri = f"gpt://{self.settings.yandex_folder_id}/yandexgpt/latest"

    def _get_context_from_graph(self, query: str, depth: int) -> str:
        from app.services.nlp.service import extract_from_text
        
        # Extract entities from the user query
        extraction = extract_from_text(query)
        
        # Combine extracted entities and long words from the query
        raw_keywords = [e.text.lower() for e in extraction.entities]
        raw_keywords.extend([w.lower() for w in query.split() if len(w) > 4])
        
        keywords = []
        for kw in raw_keywords:
            # Simple stemming for Russian: strip last 1-2 chars for matching
            stemmed = kw[:-2] if len(kw) > 5 else kw
            if stemmed not in keywords:
                keywords.append(stemmed)

        if not keywords:
            return ""

        # Build Cypher query to match any of the keywords
        conditions = " OR ".join([f"toLower(n.name) CONTAINS $kw_{i}" for i in range(len(keywords))])
        params = {f"kw_{i}": kw for i, kw in enumerate(keywords)}
        
        cypher = (
            f"MATCH (n) WHERE {conditions} "
            "WITH n LIMIT 5 "
            f"MATCH path = (n)-[*0..{depth}]-(m) "
            "UNWIND nodes(path) as node "
            "RETURN DISTINCT node.name AS name, node.raw_text AS raw_text LIMIT 20"
        )
        try:
            results = self.driver.run(cypher, params)
            context_lines = []
            for record in results:
                name = record.get("name")
                raw_text = record.get("raw_text")
                if raw_text:
                    # Limit raw text to avoid blowing up context window
                    context_lines.append(f"Текст ({name}): {raw_text[:3000]}")
                elif name:
                    context_lines.append(f"Термин: {name}")
            return "\n".join(context_lines)
        except Exception as e:
            logger.error("Ошибка при поиске в графе: %s", e)
            return ""

    def search(self, text: str, filters: SearchFilters) -> dict[str, Any]:
        context = self._get_context_from_graph(text, depth=filters.depth)
        
        if not context:
            return {
                "query": text,
                "filters": filters.__dict__,
                "results": [],
                "took_ms": 0,
                "answer": "Не знаю.",
            }

        # Strict Python-level filter check for Hackathon MVP
        if filters.geography:
            geo = filters.geography.lower()
            if geo not in context.lower():
                return {
                    "query": text,
                    "filters": filters.__dict__,
                    "results": [],
                    "took_ms": 0,
                    "answer": "Не знаю.",
                }

        if filters.year_from or filters.year_to:
            import re
            years_in_context = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', context)]
            min_y = filters.year_from or 0
            max_y = filters.year_to or 9999
            
            # If context mentions years, check them. If no years, it fails the strict year filter.
            if not years_in_context or not any(min_y <= y <= max_y for y in years_in_context):
                return {
                    "query": text,
                    "filters": filters.__dict__,
                    "results": [],
                    "took_ms": 0,
                    "answer": "Не знаю.",
                }

        prompt = f"""
        Используй следующие факты из базы знаний (представлены как фрагменты графа) для ответа на вопрос.
        
        ВНИМАНИЕ! КРИТИЧЕСКОЕ ПРАВИЛО:
        Пользователь установил жесткие фильтры для поиска:
        - География: {filters.geography if filters.geography else 'Любая'}
        - Период: с {filters.year_from if filters.year_from else 'любого года'} по {filters.year_to if filters.year_to else 'любой год'}
        
        Если факты в базе знаний явно не относятся к указанной Географии или Периоду (или в них вообще нет дат/стран), ты ОБЯЗАН ответить 'Не знаю'. Игнорировать фильтры строго запрещено!
        Если фактов недостаточно, также отвечай 'Не знаю'.

        Факты:
        {context}

        Вопрос: {text}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_uri,
                messages=[
                    {"role": "system", "content": "Ты эксперт-металлург. Отвечай кратко и по делу на основе предоставленных фактов."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )
            answer = response.choices[0].message.content
        except Exception as e:
            logger.error("Ошибка генерации ответа: %s", e)
            answer = f"Произошла ошибка при генерации ответа: {e}"

        return {
            "query": text,
            "filters": filters.__dict__,
            "results": [{"context": context}],
            "took_ms": 0,
            "answer": answer,
        }
