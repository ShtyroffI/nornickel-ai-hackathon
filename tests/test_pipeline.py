from app.services.ingestion.service import IngestionService
from app.services.nlp.service import NLPService


def test_ingestion_loads_text(tmp_path):
    p = tmp_path / "doc.txt"
    p.write_text("Электроэкстракция никеля, сульфаты ≤300 мг/л.", encoding="utf-8")
    doc = IngestionService().load(p)
    assert doc.text
    assert doc.language == "ru"


def test_nlp_extracts_synonym_and_numeric():
    text = "Electrowinning of nickel with sulfates <=300 мг/л and climate cold."
    res = NLPService().extract(text, language="en")
    names = {e.name for e in res.entities}
    assert "электроэкстракция" in names
    assert any(e.value == 300.0 for e in res.entities)
