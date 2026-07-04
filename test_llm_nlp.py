import asyncio
from app.services.nlp.service import extract_from_text

text = "В ходе эксперимента установлено, что медный купорос успешно применяется для флотации никелевых руд при температуре 50 °C."
result = extract_from_text(text)

print(f"Triples extracted: {len(result.triples)}")
for t in result.triples:
    print(f"- {t.subject} -> {t.predicate} -> {t.object}")
