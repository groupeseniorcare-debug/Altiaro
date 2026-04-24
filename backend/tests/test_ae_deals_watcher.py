"""Unit tests for AliExpress Deals Watcher helpers."""
from routes.ae_deals_watcher import _parse_orders, _parse_price_eur, _build_queries


def test_parse_orders_variants():
    assert _parse_orders("10,000+") == 10000
    assert _parse_orders("4,000+") == 4000
    assert _parse_orders("500") == 500
    assert _parse_orders("") == 0
    assert _parse_orders(None) == 0
    assert _parse_orders("abc") == 0
    assert _parse_orders("1,234,567") == 1234567


def test_parse_price_eur_target_first():
    # targetSalePrice priorised
    assert _parse_price_eur({"targetSalePrice": "4.69", "salePriceFormat": "4,69€"}) == 4.69
    # Fallback on salePriceFormat
    assert _parse_price_eur({"salePriceFormat": "4,69€"}) == 4.69
    # French decimal comma
    assert _parse_price_eur({"salePriceFormat": "123,45€"}) == 123.45
    # Invalid
    assert _parse_price_eur({"salePriceFormat": "—"}) is None
    assert _parse_price_eur({}) is None


def test_build_queries_from_niche():
    site = {"niche": "fauteuils releveurs"}
    assert _build_queries(site) == ["fauteuils releveurs"]


def test_build_queries_empty_fallback():
    assert len(_build_queries({"niche": ""})) >= 1
    assert len(_build_queries({})) >= 1


def test_parse_orders_float_like():
    assert _parse_orders("1,000.5") == 0  # strict int, don't accept floats
