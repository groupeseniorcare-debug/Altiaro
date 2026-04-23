"""Tests for blog auto-plan keyword picker logic (no LLM needed)."""
from routes.blog_posts import _pick_informational_keywords, _slugify, _used_keywords_from_posts


def _make_site(keywords, country="FR"):
    return {
        "design": {
            "niche_analysis": {
                "results": [{"country": country, "keywords": keywords}]
            }
        }
    }


def test_picker_ranks_informational_by_volume():
    site = _make_site([
        {"keyword": "comment choisir un fauteuil releveur", "volume_monthly": 2400},
        {"keyword": "fauteuil releveur pas cher", "volume_monthly": 3800},
        {"keyword": "pourquoi utiliser un fauteuil releveur", "volume_monthly": 800},
        {"keyword": "acheter fauteuil releveur", "volume_monthly": 5000},
        {"keyword": "avantages fauteuil releveur", "volume_monthly": 900},
    ])
    result = _pick_informational_keywords(site, "FR", limit=5)
    kws = [r["keyword"] for r in result]
    assert kws[0] == "comment choisir un fauteuil releveur"
    assert "acheter fauteuil releveur" not in kws
    assert "fauteuil releveur pas cher" not in kws
    assert "pourquoi utiliser un fauteuil releveur" in kws


def test_picker_falls_back_to_neutrals_when_no_info():
    site = _make_site([
        {"keyword": "fauteuil releveur senior", "volume_monthly": 1000},
        {"keyword": "fauteuil electric", "volume_monthly": 500},
    ])
    result = _pick_informational_keywords(site, "FR", limit=3)
    assert len(result) == 2
    assert result[0]["keyword"] == "fauteuil releveur senior"


def test_picker_empty_when_no_match():
    site = _make_site([
        {"keyword": "acheter x", "volume_monthly": 100},
        {"keyword": "prix y", "volume_monthly": 50},
    ])
    assert _pick_informational_keywords(site, "FR") == []


def test_picker_handles_missing_market():
    site = _make_site([{"keyword": "comment x", "volume_monthly": 1}], country="DE")
    assert _pick_informational_keywords(site, "FR") == []


def test_picker_excludes_used_keywords():
    site = _make_site([
        {"keyword": "comment choisir X", "volume_monthly": 1000},
        {"keyword": "pourquoi Y", "volume_monthly": 800},
        {"keyword": "guide complet Z", "volume_monthly": 500},
    ])
    used = {"comment choisir x"}  # lower-cased
    result = _pick_informational_keywords(site, "FR", limit=5, exclude_used=used)
    kws = [r["keyword"] for r in result]
    assert "comment choisir X" not in kws
    assert "pourquoi Y" in kws


def test_used_keywords_extraction():
    posts = [
        {"type": "pillar", "pillar_keyword": "Guide Fauteuil", "satellite_keywords": ["Astuces X", "Entretien Y"]},
        {"type": "satellite", "satellite_keyword": "Avantages Z"},
        {"title": "Manual post, no AI keyword"},
    ]
    used = _used_keywords_from_posts(posts)
    assert "guide fauteuil" in used
    assert "astuces x" in used
    assert "entretien y" in used
    assert "avantages z" in used
    assert len(used) == 4


def test_slugify_basic():
    assert _slugify("Comment Choisir un Fauteuil Releveur !") == "comment-choisir-un-fauteuil-releveur"
    assert _slugify("").startswith("article-")
