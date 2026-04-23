"""Tests for SEO Coach rule engine (no LLM, no network)."""
from routes.seo_coach import _compute_alerts


BASE_SITE = {"id": "s1", "name": "Test Boutique", "niche": "fauteuils"}


def _pulse(**overrides):
    base = {
        "articles_this_month": 0,
        "articles_total": 0,
        "keywords_covered": 0,
        "keywords_total_informational": 0,
        "coverage_pct": 0,
        "recent_articles": [],
        "avg_eeat_score": 0,
        "next_cluster_at": None,
    }
    base.update(overrides)
    return base


def test_no_articles_triggers_warn():
    alerts = _compute_alerts(_pulse(), BASE_SITE)
    assert any(a["id"].startswith("no-articles-") and a["severity"] == "warn" for a in alerts)


def test_critical_eeat_under_55():
    pulse = _pulse(
        articles_total=3,
        avg_eeat_score=42,
        recent_articles=[{"title": "Article A", "eeat_score": 40}],
    )
    alerts = _compute_alerts(pulse, BASE_SITE)
    assert any(a["severity"] == "critical" and "E-E-A-T" in a["title"] for a in alerts)


def test_warn_eeat_between_55_and_70_with_low_articles():
    pulse = _pulse(
        articles_total=3,
        avg_eeat_score=62,
        recent_articles=[
            {"title": "Article low 1", "eeat_score": 45},
            {"title": "Article low 2", "eeat_score": 50},
            {"title": "Article OK", "eeat_score": 75},
        ],
    )
    alerts = _compute_alerts(pulse, BASE_SITE)
    warn = [a for a in alerts if a["severity"] == "warn" and "E-E-A-T" in a["title"]]
    assert len(warn) == 1
    assert "2" in warn[0]["title"]  # 2 articles à enrichir


def test_coverage_zero_triggers_warn():
    pulse = _pulse(
        articles_total=1,
        avg_eeat_score=80,
        keywords_total_informational=5,
    )
    alerts = _compute_alerts(pulse, BASE_SITE)
    assert any(a["id"].startswith("coverage-zero-") and a["severity"] == "warn" for a in alerts)


def test_coverage_35_triggers_info():
    pulse = _pulse(
        articles_total=3,
        avg_eeat_score=80,
        keywords_total_informational=10,
        coverage_pct=20,
        keywords_covered=2,
    )
    alerts = _compute_alerts(pulse, BASE_SITE)
    assert any(a["id"].startswith("coverage-low-") and a["severity"] == "info" for a in alerts)


def test_cadence_alert_when_nothing_this_month():
    pulse = _pulse(
        articles_total=5,
        articles_this_month=0,
        avg_eeat_score=80,
    )
    alerts = _compute_alerts(pulse, BASE_SITE)
    assert any(a["id"].startswith("cadence-") for a in alerts)


def test_all_healthy_returns_empty():
    pulse = _pulse(
        articles_total=5,
        articles_this_month=5,
        avg_eeat_score=85,
        keywords_total_informational=10,
        coverage_pct=80,
        keywords_covered=8,
    )
    alerts = _compute_alerts(pulse, BASE_SITE)
    # Healthy site has zero alerts
    assert alerts == []
