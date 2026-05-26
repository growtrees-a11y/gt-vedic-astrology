"""PROJ-05 Tests — mock-based, no external dependencies."""
import pytest
import json
from datetime import datetime
from main import (
    VedicChart, AstroRulesEngine, load_rules,
    datetime_to_jd, get_ayanamsa, tropical_to_sidereal,
    degrees_to_sign, compute_aspect, SIGN_NAMES,
    validate_coordinates,
)


# ── Validation ──────────────────────────────────────────────────
def test_validate_coordinates_valid():
    lat, lon = validate_coordinates(40.7, -74.0)
    assert lat == 40.7
    assert lon == -74.0

def test_validate_coordinates_invalid_lat():
    with pytest.raises(ValueError, match="Latitude"):
        validate_coordinates(95, 0)

def test_validate_coordinates_invalid_lon():
    with pytest.raises(ValueError, match="Longitude"):
        validate_coordinates(0, 200)


# ── Julian Day ──────────────────────────────────────────────────
def test_jd_known():
    """J2000.0 = 2000-01-01 12:00 UTC → JD 2451545.5"""
    dt = datetime(2000, 1, 1, 12, 0, 0)
    jd = datetime_to_jd(dt)
    assert abs(jd - 2451545.5) < 0.01

def test_jd_different_days():
    a = datetime_to_jd(datetime(2025, 1, 1, 0, 0, 0))
    b = datetime_to_jd(datetime(2025, 1, 2, 0, 0, 0))
    assert abs(b - a - 1.0) < 0.01


# ── Ayanamsa ──────────────────────────────────────────────────────
def test_ayanamsa_positive():
    jd = datetime_to_jd(datetime(2025, 6, 15))
    aya = get_ayanamsa(jd)
    assert 24 < aya < 26

def test_tropical_to_sidereal():
    sidereal = tropical_to_sidereal(30.0, 24.3)
    assert abs(sidereal - 5.7) < 0.01

def test_tropical_to_sidereal_wrap():
    sidereal = tropical_to_sidereal(10.0, 24.3)
    assert 345 < sidereal < 360


# ── Sign Conversion ──────────────────────────────────────────────
def test_degrees_to_sign_aries():
    assert degrees_to_sign(5) == 0

def test_degrees_to_sign_taurus():
    assert degrees_to_sign(35) == 1

def test_degrees_to_sign_pisces():
    assert degrees_to_sign(350) == 11

def test_sign_names():
    assert SIGN_NAMES[0] == "Aries"
    assert SIGN_NAMES[11] == "Pisces"


# ── VedicChart ────────────────────────────────────────────────────
def test_chart_einstein():
    dt = datetime(1879, 3, 14, 8, 0)
    chart = VedicChart(dt, 48.4014, 9.9897)
    result = chart.full_chart()
    assert "ascendant_sign" in result
    assert len(result["planets"]) == 7
    assert len(result["houses"]) == 12

def test_chart_gandhi():
    dt = datetime(1869, 10, 2, 1, 0)
    chart = VedicChart(dt, 21.1702, 72.8181)
    result = chart.full_chart()
    assert len(result["planets"]) == 7
    assert "aspects" in result

def test_chart_aspects_present():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    result = chart.full_chart()
    assert isinstance(result["aspects"], list)
    for asp in result["aspects"]:
        assert "planet1" in asp
        assert "planet2" in asp
        assert "aspect" in asp

def test_chart_house_planets():
    dt = datetime(2025, 6, 15, 9, 30)
    chart = VedicChart(dt, 40.7, -74.0)
    houses = chart.get_house_planets()
    assert len(houses) == 12
    all_planets = []
    for planets_in_house in houses.values():
        all_planets.extend(planets_in_house)
    assert len(all_planets) == 7


# ── Rules Engine ────────────────────────────────────────────────
def test_rules_engine_match():
    rules = [{"planet": "sun", "sign": "Leo"}]
    engine = AstroRulesEngine(rules)
    chart = {"planets": {"sun": "Leo"}, "houses": {}, "aspects": []}
    triggered = engine.evaluate(chart)
    assert len(triggered) == 1

def test_rules_engine_no_match():
    rules = [{"planet": "sun", "sign": "Virgo"}]
    engine = AstroRulesEngine(rules)
    chart = {"planets": {"sun": "Leo"}, "houses": {}, "aspects": []}
    triggered = engine.evaluate(chart)
    assert len(triggered) == 0

def test_rules_engine_house_match():
    rules = [{"planet": "mars", "house": 7}]
    engine = AstroRulesEngine(rules)
    chart = {"planets": {}, "houses": {7: ["mars"]}, "aspects": []}
    triggered = engine.evaluate(chart)
    assert len(triggered) == 1

def test_rules_engine_aspect_match():
    rules = [
        {
            "planet": "moon",
            "aspect": "conjunction",
            "aspect_planet": "mars",
            "require_aspect": True,
        }
    ]
    engine = AstroRulesEngine(rules)
    chart = {
        "planets": {}, "houses": {},
        "aspects": [{"planet1": "moon", "planet2": "mars",
                      "aspect": "conjunction", "angle_deg": 2.5}],
    }
    triggered = engine.evaluate(chart)
    assert len(triggered) == 1

def test_rules_engine_aspect_no_match():
    rules = [
        {
            "planet": "moon",
            "aspect": "conjunction",
            "aspect_planet": "mars",
            "require_aspect": True,
        }
    ]
    engine = AstroRulesEngine(rules)
    chart = {"planets": {}, "houses": {}, "aspects": []}
    triggered = engine.evaluate(chart)
    assert len(triggered) == 0


# ── Load Rules ──────────────────────────────────────────────────
def test_load_rules_file(tmp_path):
    rules = [{"planet": "sun", "sign": "Leo"}]
    path = tmp_path / "test_rules.json"
    path.write_text(json.dumps(rules))
    loaded = load_rules(str(path))
    assert len(loaded) == 1
    assert loaded[0]["planet"] == "sun"


# ── Compute Aspect ──────────────────────────────────────────────
def test_compute_aspect_conjunction():
    assert compute_aspect(2.0) == "conjunction"

def test_compute_aspect_opposition():
    assert compute_aspect(179.0) == "opposition"

def test_compute_aspect_trine():
    assert compute_aspect(120.0) == "trine"

def test_compute_aspect_square():
    assert compute_aspect(90.0) == "square"

def test_compute_aspect_none():
    assert compute_aspect(45.0) is None
