from core.recommend import recommend_rate


def test_high_demand_raises_rate():
    rate, _ = recommend_rate("high", comp_avg=4800, base=4000)
    assert rate == 4600  # 4000 * 1.15


def test_low_demand_discounts():
    rate, _ = recommend_rate("low", comp_avg=4000, base=4000)
    assert rate == 3600


def test_capped_by_competitor_premium():
    rate, reason = recommend_rate("high", comp_avg=3000, base=4000)
    assert rate == 3450 and "capped" in reason


def test_guardrails_respected():
    rate, _ = recommend_rate("low", comp_avg=1000, base=4000, min_rate=2800, max_rate=8000)
    assert rate == 2800
    rate, _ = recommend_rate("high", comp_avg=50000, base=4000, min_rate=2800, max_rate=4000)
    assert rate == 4000


def test_rounds_to_nearest_50():
    rate, _ = recommend_rate("medium", comp_avg=4010, base=4010)
    assert rate % 50 == 0
