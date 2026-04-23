"""Tests for brand text sanitizer — prevents Claude markdown/preambles from
polluting brand.name / brand.tagline in the storefront."""
from routes.design import _sanitize_brand_text


def test_extracts_bold_token_from_full_markdown_response():
    raw = (
        "# Proposition de nom de marque\n\n"
        "**Soléa**\n\n"
        "Un nom lumineux et enveloppant qui évoque le soleil.\n"
        "La sonorité fluide et chantante le rend mémorable."
    )
    assert _sanitize_brand_text(raw, max_len=40) == "Soléa"


def test_strips_french_preambles():
    assert _sanitize_brand_text("Voici : Aurélia", max_len=40) == "Aurélia"
    assert _sanitize_brand_text("Le nom est Aurélia", max_len=40) == "Aurélia"
    assert _sanitize_brand_text("Proposition de nom : Aurélia", max_len=40) == "Aurélia"


def test_strips_guillemets_and_quotes():
    assert _sanitize_brand_text('"Aurélia"', max_len=40) == "Aurélia"
    assert _sanitize_brand_text("«Aurélia»", max_len=40) == "Aurélia"
    assert _sanitize_brand_text("'Aurélia'", max_len=40) == "Aurélia"


def test_strips_markdown_chars():
    assert _sanitize_brand_text("**Aurélia**", max_len=40) == "Aurélia"
    assert _sanitize_brand_text("# Aurélia", max_len=40) == "Aurélia"
    assert _sanitize_brand_text("_Aurélia_", max_len=40) == "Aurélia"


def test_empty_input_returns_empty():
    assert _sanitize_brand_text("", max_len=40) == ""
    assert _sanitize_brand_text(None, max_len=40) == ""


def test_enforces_max_length_without_cutting_words():
    text = "Maison Clarelle Premium Luxury Silver"
    result = _sanitize_brand_text(text, max_len=20)
    assert len(result) <= 20
    assert not result.endswith(" ")


def test_tagline_keeps_punctuation_inside():
    raw = "Le confort quotidien, retrouvé."
    assert _sanitize_brand_text(raw, max_len=80) == "Le confort quotidien, retrouvé"


def test_first_clean_line_fallback_when_no_bold():
    raw = "Aurélia\nUn nom qui évoque la lumière dorée et l'automne."
    assert _sanitize_brand_text(raw, max_len=40) == "Aurélia"
