"""Аналитика: автогенерация обзоров, выявление пробелов, рекомендации."""

from __future__ import annotations


class AnalyticsService:
    def generate_review(self, topic: str, group_by: list[str]) -> dict:
        from app.services.search.service import SearchService
        search_svc = SearchService()
        
        context = search_svc._get_context_from_graph(topic, depth=2)
        if not context:
            return {
                "topic": topic,
                "groups": {},
                "summary": "Не найдено контекста в базе знаний по данному запросу.",
                "consensus": [],
                "disagreements": ["Нет данных"],
                "sources_count": 0,
                "confidence": 0.0,
            }

        prompt = f"""
        Используй следующие факты из базы знаний:
        {context}
        
        Напиши обзор по теме: "{topic}".
        Источники указаны в начале абзацев как "Текст (Имя_файла)". Сгруппируй эти источники по темам или методам.
        Ответ верни строго в формате JSON:
        {{
            "summary": "Краткое подробное описание (2-3 абзаца)",
            "consensus": ["Доказанный факт 1", "Доказанный факт 2"],
            "disagreements": ["Спорный момент или проблема"],
            "source_groups": {{
                "Технология А": ["Файл1.pdf", "Файл2.pdf"],
                "Технология Б": ["Файл3.pdf"]
            }},
            "confidence": 0.9
        }}
        В выводе не пиши ничего, кроме самого JSON! Не придумывай источники, используй только те, что в тексте.
        """

        try:
            response = search_svc.client.chat.completions.create(
                model=search_svc.model_uri,
                messages=[
                    {"role": "system", "content": "Ты AI-аналитик. Отвечай только валидным JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )
            answer = response.choices[0].message.content.strip()
            if answer.startswith("```"):
                answer = "\n".join(answer.split("\n")[1:-1]).strip()
            
            import json
            import re
            
            parsed = json.loads(answer)
            summary = parsed.get("summary", "")
            consensus = parsed.get("consensus", [])
            disagreements = parsed.get("disagreements", [])
            confidence = float(parsed.get("confidence", 0.8))
            source_groups_raw = parsed.get("source_groups", {})
            
            real_sources = set(re.findall(r"^Текст \((.+?)\):", context, re.MULTILINE))
            
            groups = {}
            for g_name, g_sources in source_groups_raw.items():
                valid_sources = [s for s in g_sources if s in real_sources]
                if valid_sources:
                    groups[g_name] = valid_sources
                    
            if not groups and real_sources:
                groups["Общие источники"] = list(real_sources)

        except Exception as e:
            import logging
            logging.error(f"Error in overview: {e}")
            summary = f"Произошла ошибка при обращении к LLM: {e}"
            consensus = []
            disagreements = []
            groups = {}
            confidence = 0.0

        return {
            "topic": topic,
            "groups": groups,
            "summary": summary,
            "consensus": consensus,
            "disagreements": disagreements,
            "sources_count": len([line for line in context.split('\n') if line.startswith('Текст')]),
            "confidence": confidence,
        }

    def find_gaps(self, materials: list[str], processes: list[str], conditions: list[str]) -> list[dict]:
        from app.services.search.service import SearchService
        search_svc = SearchService()
        
        results = []
        for m in materials:
            for p in processes:
                for c in conditions:
                    query = f"{m} {p} {c}"
                    context = search_svc._get_context_from_graph(query, depth=1)
                    
                    if not context or len(context) < 50:
                        results.append({
                            "material": m,
                            "process": p,
                            "condition": c,
                            "severity": "high",
                            "reason": "В графе знаний полностью отсутствуют публикации или эксперименты по данному пересечению."
                        })
                    else:
                        prompt = f"""
                        Используй факты из базы знаний:
                        {context[:2000]}
                        
                        Оцени, насколько глубоко исследовано применение процесса "{p}" к материалу "{m}" в условиях "{c}".
                        Ответь строго в формате JSON:
                        {{
                            "severity": "low" | "medium" | "high", 
                            "reason": "Краткое обоснование (1-2 предложения)"
                        }}
                        Примечание: "high" (высокий пробел) — если исследований почти нет или они неудачные. "low" (нет пробела) — если технология хорошо изучена.
                        В выводе не пиши ничего, кроме самого JSON!
                        """
                        try:
                            response = search_svc.client.chat.completions.create(
                                model=search_svc.model_uri,
                                messages=[
                                    {"role": "system", "content": "Ты AI-аналитик. Отвечай только валидным JSON."},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=0.1,
                            )
                            ans = response.choices[0].message.content.strip()
                            if ans.startswith("```"):
                                ans = "\n".join(ans.split("\n")[1:-1]).strip()
                            import json
                            parsed = json.loads(ans)
                            severity = parsed.get("severity", "medium").lower()
                            reason = parsed.get("reason", "Нет данных.")
                        except Exception:
                            severity = "medium"
                            reason = "Есть связанные факты, но нейросеть не смогла оценить глубину исследования."

                        results.append({
                            "material": m,
                            "process": p,
                            "condition": c,
                            "severity": severity,
                            "reason": reason
                        })
                        
        return results

    def recommend(self, topic: str) -> dict:
        from app.services.search.service import SearchService
        search_svc = SearchService()
        context = search_svc._get_context_from_graph(topic, depth=2)
        
        if not context:
            return {"related_cases": ["Нет данных"], "experts": ["Нет данных"], "adjacent_topics": ["Нет данных"]}
            
        prompt = f"""
        Контекст:
        {context[:3000]}
        
        Основываясь на контексте по теме "{topic}", порекомендуй похожие кейсы, упомянутых экспертов/авторов и смежные области для изучения.
        Ответ верни строго в формате JSON:
        {{
            "related_cases": ["Кейс 1", "Кейс 2"],
            "experts": ["Эксперт/Организация 1", "Эксперт 2"],
            "adjacent_topics": ["Смежная тема 1"]
        }}
        """
        try:
            response = search_svc.client.chat.completions.create(
                model=search_svc.model_uri,
                messages=[
                    {"role": "system", "content": "Ты AI-советник. Возвращай только JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )
            ans = response.choices[0].message.content.strip()
            if ans.startswith("```"):
                ans = "\n".join(ans.split("\n")[1:-1]).strip()
            import json
            return json.loads(ans)
        except Exception:
            return {"related_cases": ["Ошибка генерации"], "experts": [], "adjacent_topics": []}

    def compare(self, variant_a: str, variant_b: str, criteria: list[str]) -> dict:
        from app.services.search.service import SearchService
        search_svc = SearchService()
        
        ctx_a = search_svc._get_context_from_graph(variant_a, depth=1)
        ctx_b = search_svc._get_context_from_graph(variant_b, depth=1)
        
        crit_str = ", ".join(criteria)
        prompt = f"""
        Данные для варианта А ({variant_a}):
        {ctx_a[:2000] if ctx_a else "Нет данных."}
        
        Данные для варианта Б ({variant_b}):
        {ctx_b[:2000] if ctx_b else "Нет данных."}
        
        Сравни вариант А и вариант Б по следующим критериям: {crit_str}.
        Ответ верни строго в формате JSON:
        {{
            "rows": [
                {{
                    "criterion": "Название критерия",
                    "a_value": "Как это работает для А",
                    "b_value": "Как это работает для Б"
                }}
            ]
        }}
        """
        try:
            response = search_svc.client.chat.completions.create(
                model=search_svc.model_uri,
                messages=[
                    {"role": "system", "content": "Ты AI-аналитик. Возвращай только JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            ans = response.choices[0].message.content.strip()
            if ans.startswith("```"):
                ans = "\n".join(ans.split("\n")[1:-1]).strip()
            import json
            parsed = json.loads(ans)
            rows = parsed.get("rows", [])
        except Exception:
            rows = [{"criterion": "Ошибка", "a_value": "-", "b_value": "-"}]
            
        return {
            "a": variant_a,
            "b": variant_b,
            "criteria": criteria,
            "rows": rows,
        }
