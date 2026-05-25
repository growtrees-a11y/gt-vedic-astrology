"""
PROJ-05 Tests — Vedic astrology chart calculations.
pytest test_main.py
"""
import pytest
from datetime import datetime
from main import VedicChart, AstroRulesEngine, degrees_to_sign, SIGN_NAMES


def test_chart_creation():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    assert chart.lat == 40.0
    assert chart.lon == -74.0


def test_planet_signs_exist():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    signs = chart.get_planet_signs()
    assert "sun" in signs
    assert "moon" in signs
    for s in signs.values():
        assert s in SIGN_NAMES


def test_ascendant_in_sign():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    asc = chart.calculate_ascendant()
    assert 0 <= asc < 360


def test_full_chart_structure():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    result = chart.full_chart()
    assert "ascendant_sign" in result
    assert "planets" in result
    assert "houses" in result
    assert isinstance(result["planets"], dict)
    assert isinstance(result["houses"], dict)


def test_degrees_to_sign():
    assert degrees_to_sign(0) == 0  # Aries
    assert degrees_to_sign(30) == 1  # Taurus
    assert degrees_to_sign(359) == 11  # Pisces
    assert degrees_to_sign(360) == 0  # wraps


def test_rules_engine_basic():
    rules = [
        {"planet": "sun", "sign": "aries", "house": 1},
        {"planet": "moon", "sign": "cancer"},
    ]
    engine = AstroRulesEngine(rules)
    chart = {"planets": {"sun": "Aries", "moon": "Cancer"}, "houses": {}}
    triggered = engine.evaluate(chart)
    assert len(triggered) == 1  # only moon in cancer matches (sun not in house 1)


def test_ayanamsa_positive():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    assert chart.ayanamsa > 0


def test_houses_count():
    dt = datetime(2000, 1, 1, 12, 0)
    chart = VedicChart(dt, 40.0, -74.0)
    houses = chart.calculate_houses()
    assert len(houses) == 12
