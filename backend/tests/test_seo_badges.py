"""Tests for the E-E-A-T badges rule engine and snapshot logic."""
from routes.seo_coach import _check_badges


def test_first_cluster_unlocks_on_first_article():
    snaps = [{"avg_eeat_score": 42, "articles_total": 1, "coverage_pct": 0}]
    badges = _check_badges(snaps, set())
    ids = [b["id"] for b in badges]
    assert "first-cluster" in ids
    assert "eeat-75" not in ids


def test_eeat_75_badge():
    snaps = [{"avg_eeat_score": 78, "articles_total": 5, "coverage_pct": 20}]
    badges = _check_badges(snaps, set())
    ids = [b["id"] for b in badges]
    assert "eeat-75" in ids
    assert "eeat-90" not in ids


def test_eeat_90_badge():
    snaps = [{"avg_eeat_score": 92, "articles_total": 3, "coverage_pct": 40}]
    badges = _check_badges(snaps, set())
    ids = [b["id"] for b in badges]
    assert "eeat-90" in ids
    assert "eeat-75" in ids


def test_coverage_50_and_100():
    snaps_50 = [{"avg_eeat_score": 75, "articles_total": 3, "coverage_pct": 55}]
    ids_50 = {b["id"] for b in _check_badges(snaps_50, set())}
    assert "coverage-50" in ids_50
    assert "coverage-100" not in ids_50

    snaps_100 = [{"avg_eeat_score": 80, "articles_total": 5, "coverage_pct": 100}]
    ids_100 = {b["id"] for b in _check_badges(snaps_100, set())}
    assert "coverage-50" in ids_100
    assert "coverage-100" in ids_100


def test_streak_4w_requires_4_consecutive():
    # 3 weeks only — no streak badge
    snaps_3 = [{"avg_eeat_score": 80, "articles_total": 5, "coverage_pct": 30}] * 3
    ids_3 = {b["id"] for b in _check_badges(snaps_3, set())}
    assert "streak-4w-75" not in ids_3

    # 4 weeks all above 75 — streak unlocks
    snaps_4 = [{"avg_eeat_score": 80, "articles_total": 5, "coverage_pct": 30}] * 4
    ids_4 = {b["id"] for b in _check_badges(snaps_4, set())}
    assert "streak-4w-75" in ids_4


def test_streak_4w_breaks_if_one_dip():
    snaps = [
        {"avg_eeat_score": 80, "articles_total": 5, "coverage_pct": 30},
        {"avg_eeat_score": 60, "articles_total": 5, "coverage_pct": 30},  # dip
        {"avg_eeat_score": 82, "articles_total": 6, "coverage_pct": 35},
        {"avg_eeat_score": 85, "articles_total": 7, "coverage_pct": 40},
    ]
    ids = {b["id"] for b in _check_badges(snaps, set())}
    assert "streak-4w-75" not in ids


def test_already_unlocked_badges_not_returned_again():
    snaps = [{"avg_eeat_score": 78, "articles_total": 5, "coverage_pct": 55}]
    already = {"first-cluster", "eeat-75", "coverage-50"}
    badges = _check_badges(snaps, already)
    # No new badges — they're all already unlocked
    assert badges == []
