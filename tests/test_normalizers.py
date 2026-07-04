from app.services.nlp.normalizers import (
    expand_abbreviations,
    iter_chunks,
    normalize_full,
    normalize_numbers_and_units,
    normalize_unicode,
    split_sentences,
    strip_punctuation,
    unify_units,
)


def test_normalize_unicode_drops_combining_marks():
    text = "ни́кель"
    assert normalize_unicode(text) == "никель"


def test_unify_units_canonical_forms():
    assert unify_units("300 мг\\л") == "300 мг/л"
    assert unify_units("350 ° с") == "350 °C"
    assert unify_units("5 м/сек") == "5 м/с"


def test_normalize_numbers_and_units_combined():
    out = normalize_numbers_and_units("сульфаты 1,5 г/л и 350 ° с, 1 500 т/сут")
    assert "1.5 г/л" in out
    assert "350 °C" in out
    assert "1500 т/сут" in out


def test_expand_abbreviations_does_not_touch_random_words():
    assert "печь взвешенной плавки" in expand_abbreviations("В ПВП проводили плавку")
    assert "никель" in expand_abbreviations("Ni-руда (НИ) обработана")


def test_strip_punctuation_keeps_units():
    out = strip_punctuation("Cu, Ni — до 300 мг/л!")
    assert "мг/л" in out
    assert "," not in out
    assert "!" not in out


def test_normalize_full_pipeline():
    out = normalize_full("В  ПВП,  Ni-руда,  1,5 г/л  и  350 ° С")
    assert "печь взвешенной плавки" in out
    assert "никель" in out
    assert "1.5 г/л" in out
    assert "350 °C" in out
    assert out == " ".join(out.split())


def test_split_sentences_basic():
    sents = split_sentences("Никель добывают. Cu и Ni — металлы. Это важно")
    assert len(sents) >= 2
    assert sents[0].startswith("Никель")


def test_iter_chunks_with_overlap():
    text = "абв" * 200
    chunks = list(iter_chunks(text, max_len=50, overlap=10))
    assert all(len(c) <= 50 for c in chunks)
    assert len(chunks) > 1
