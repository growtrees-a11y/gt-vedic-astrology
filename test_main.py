"""
PROJ-05 Tests — Vedic astrology chart calculations.
Uses mock_swe (mathematical approximation) instead of pyswisseph.
pytest test_main.py
"""
import json
import os
import pytest
from datetime import datetime
from main import (
    VedicChart,
    AstroRulesEngine,
    degrees_to_sign,
    SIGN_NAMES,
    load_rules,
    tropical_to_sidereal,
    datetime_to_jd,
)


# ─── Helper / utility tests ─────────────────────────────────────────

def test_degrees_to_sign():
    assert degrees_to_sign(0) == 0  # Aries
    assert degrees_to_sign(15) == 0  # Aries
    assert degrees_to_sign(30) == 1  # Taurus
    assert degrees_to_sign(89) == 2  # Gemini
    assert degrees_to_sign(119) == 3  # Cancer
    assert degrees_to_sign(359) == 11  # Pisces
    assert degrees_to_sign(360) == 0  # wraps


def test_degrees_to_sign_boundary():
    """Check sign boundaries (every 30°)."""
    for i in range(12):
        assert degrees_to_sign(i * 30 - 1) == (i - 1) % 12
        assert degrees_to_sign(i * 30) == i


def test_sign_names():
    assert len(SIGN_NAMES) == 12
    assert SIGN_NAMES[0] == "Aries"
    assert SIGN_NAMES[11] == "Pisces"


def test_datetime_to_jd():
    # Known: 2000-01-01 12:00 UTC → JD 2451545.0 (J2000.0)
    dt = datetime(2000, 1, 1, 12, 0)
    jd = datetime_to_jd(dt)
    assert abs(jd - 2451545.0) < 1


def test_tropical_to_sidereal_normal():
    # 30° tropical − 23° ayanamsa = 7° sidereal (Aries)
    assert tropical_to_sidereal(30, 23) == pytest.approx(7, abs=0.01)


def test_tropical_to_sidereal_wrap():
    # 10° − 23° = -13° → 347°
    assert tropical_to_sidereal(10, 23) == pytest.approx(347, abs=0.01)


# ─── VedicChart tests ───────────────────────────────────────────────

def test_chart_creation():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    assert chart.lat == 40.0
    assert chart.lon == -74.0
    assert isinstance(chart.jd, float)
    assert chart.jd > 2400000


def test_ayanamsa_positive():
    """Ayanamsa should be positive for post-1000 CE dates."""
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    assert chart.ayanamsa > 0
    # Roughly 23-24° for year 2000
    assert 20 < chart.ayanamsa < 27


def test_planet_positions_exist():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    planets = chart.calculate_planets()
    for body in ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]:
        assert body in planets, f"Missing {body}"
        assert 0 <= planets[body] < 360, f"{body} degree out of range: {planets[body]}"


def test_planet_signs_exist():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    signs = chart.get_planet_signs()
    assert "sun" in signs
    assert "moon" in signs
    assert "mars" in signs
    for s in signs.values():
        assert s in SIGN_NAMES, f"Invalid sign name: {s}"


def test_ascendant_in_range():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    asc = chart.calculate_ascendant()
    assert 0 <= asc < 360


def test_ascendant_sign_valid():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    asc_deg = chart.calculate_ascendant()
    asc_sign = SIGN_NAMES[degrees_to_sign(asc_deg)]
    assert asc_sign in SIGN_NAMES


def test_houses_count():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    houses = chart.calculate_houses()
    assert len(houses) == 12
    for h in houses:
        assert 0 <= h < 360


def test_house_planets_mapping():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    mapping = chart.get_house_planets()
    # Should have 12 house keys
    assert len(mapping) == 12
    for h in range(1, 13):
        assert h in mapping
        assert isinstance(mapping[h], list)


def test_full_chart_structure():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    result = chart.full_chart()
    assert "date" in result
    assert "lat" in result
    assert "lon" in result
    assert "ayanamsa" in result
    assert "ascendant_deg" in result
    assert "ascendant_sign" in result
    assert "planets" in result
    assert "houses" in result
    assert isinstance(result["planets"], dict)
    assert isinstance(result["houses"], dict)
    assert result["ascendant_sign"] in SIGN_NAMES


def test_full_chart_planet_count():
    """Full chart should contain all 7 classical planets."""
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    result = chart.full_chart()
    expected = {"sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"}
    assert set(result["planets"].keys()) == expected


def test_different_dates_produce_different_charts():
    dt1 = datetime(2000, 1, 1, 12, 0)
    dt2 = datetime(2005, 6, 15, 8, 0)
    c1 = VedicChart(dt1, 40.0, -74.0)
    c2 = VedicChart(dt2, 40.0, -74.0)
    # Ascendants should differ for very different dates
    assert c1.calculate_ascendant() != c2.calculate_ascendant()


def test_einstein_chart():
    """Albert Einstein: 1879-03-14, 48.4014°N 9.9897°E."""
    dt = datetime(1879, 3, 14, 8, 0)
    chart = VedicChart(dt, 48.4014, 9.9897)
    result = chart.full_chart()
    assert result["ascendant_sign"] in SIGN_NAMES
    assert len(result["planets"]) == 7
    assert len(result["houses"]) == 12


# ─── Rules Engine tests ─────────────────────────────────────────────

def test_rules_engine_basic():
    rules = [
        {"planet": "sun", "sign": "Aries", "house": 1},
        {"planet": "moon", "sign": "Cancer"},
    ]
    engine = AstroRulesEngine(rules)
    chart = {
        "planets": {"sun": "Aries", "moon": "Cancer"},
        "houses": {},
    }
    triggered = engine.evaluate(chart)
    # moon in cancer matches (sign only, no house constraint)
    # sun in Aries but house 1 is not in chart → does NOT match
    assert len(triggered) == 1
    assert triggered[0]["planet"] == "moon"


def test_rules_engine_all_match():
    rules = [
        {"planet": "sun", "sign": "Aries", "house": 1},
    ]
    engine = AstroRulesEngine(rules)
    chart = {
        "planets": {"sun": "Aries"},
        "houses": {1: ["sun"]},
    }
    triggered = engine.evaluate(chart)
    assert len(triggered) == 1


def test_rules_engine_none_match():
    rules = [
        {"planet": "sun", "sign": "Capricorn"},
    ]
    engine = AstroRulesEngine(rules)
    chart = {
        "planets": {"sun": "Aries"},
        "houses": {},
    }
    triggered = engine.evaluate(chart)
    assert len(triggered) == 0


def test_rules_engine_case_insensitive():
    rules = [{"planet": "SUN", "sign": "ARIES"}]
    engine = AstroRulesEngine(rules)
    chart = {"planets": {"sun": "Aries"}, "houses": {}}
    triggered = engine.evaluate(chart)
    assert len(triggered) == 1


def test_rules_engine_house_check():
    rules = [{"planet": "mars", "house": 5}]
    engine = AstroRulesEngine(rules)
    # Mars is NOT in house 5
    chart = {"planets": {"mars": "Scorpio"}, "houses": {5: ["venus"]}}
    triggered = engine.evaluate(chart)
    assert len(triggered) == 0


def test_rules_engine_house_check_positive():
    rules = [{"planet": "mars", "house": 5}]
    engine = AstroRulesEngine(rules)
    chart = {"planets": {"mars": "Scorpio"}, "houses": {5: ["mars"]}}
    triggered = engine.evaluate(chart)
    assert len(triggered) == 1


def test_load_rules_file():
    rules_path = os.path.join(os.path.dirname(__file__), "rules.json")
    rules = load_rules(rules_path)
    assert len(rules) > 0
    assert isinstance(rules, list)
    for rule in rules:
        assert "planet" in rule


def test_load_rules_and_evaluate():
    """Load real rules.json and evaluate against a chart."""
    rules_path = os.path.join(os.path.dirname(__file__), "rules.json")
    rules = load_rules(rules_path)
    engine = AstroRulesEngine(rules)
    chart = {
        "planets": {"sun": "Aries", "moon": "Cancer", "mars": "Scorpio"},
        "houses": {1: ["sun"], 5: ["mars"]},
    }
    triggered = engine.evaluate(chart)
    assert len(triggered) >= 1


# ─── Mock-specific sanity checks ──────────────────────────────────

def test_mock_swe_importable():
    """Ensure mock_swe module loads without errors."""
    from main import swe
    # Verify key attributes exist
    assert hasattr(swe, "calc_ut")
    assert hasattr(swe, "ayanamsa_ut")
    assert hasattr(swe, "houses_ut")
    assert hasattr(swe, "SUN")
    assert hasattr(swe, "MOON")


def test_mock_calc_ut_returns_typed():
    from main import swe
    pos, _ = swe.calc_ut(2451545.0, swe.SUN)
    assert isinstance(pos, list)
    assert len(pos) == 3


def test_mock_houses_ut_returns_12_cusps():
    from main import swe
    cusps, _ = swe.houses_ut(2451545.0, 40.0, -74.0)
    assert len(cusps) == 12


def test_mock_ayanamsa_is_reasonable():
    from main import swe
    aya, _ = swe.ayanamsa_ut(2451545.0 - 2440587.5, swe.FLAH_IRA)
    assert 20 < aya < 27  # ~23° for J2000