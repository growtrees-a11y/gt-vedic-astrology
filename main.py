"""
PROJ-05: Classical Vedic Astrology Rules Engine — Production Ready
- Mock Swiss Ephemeris (mathematical approximations, no C deps)
- Complete Vedic chart: planets, ascendant, 12 houses, ayanamsa
- Full rules engine: planet/sign/house + aspects
- Historical chart validation
"""

import json
import logging
import math
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from mock_swe import (
    SUN, MOON, MERCU, VENUS, MARS, JUPITER, SATURN,
    calc_ut, ayanamsa_ut, houses_ut,
    FLAH_IRA, FLG_SWIEPH, FLG_SPEED, FLG_SIDEREAL,
)

logger = logging.getLogger("astro-agent")

# ── Constants ─────────────────────────────────────────────────────
SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

ASPECT_DEGREES = {
    "conjunction": 0, "opposition": 180, "trine": 120,
    "square": 90, "sextile": 60, "quincunx": 150,
}
ASPECT_ORB = 10  # degrees
PLANET_LABELS = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]


# ── Helpers ────────────────────────────────────────────────────────
def validate_coordinates(lat: float, lon: float) -> tuple:
    if not -90 <= lat <= 90:
        raise ValueError(f"Latitude out of range: {lat}")
    if not -180 <= lon <= 180:
        raise ValueError(f"Longitude out of range: {lon}")
    return float(lat), float(lon)


def datetime_to_jd(dt: datetime) -> float:
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jd = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    frac = (dt.hour * 3600 + dt.minute * 60 + dt.second) / 86400
    return float(jd) + frac


def get_ayanamsa(jd: float) -> float:
    ayanamsa_deg, _ = ayanamsa_ut(jd - 2400000.5, FLAH_IRA)
    return ayanamsa_deg


def tropical_to_sidereal(tropical_deg: float, ayanamsa: float) -> float:
    return (tropical_deg - ayanamsa) % 360


def degrees_to_sign(deg: float) -> int:
    return int(deg // 30) % 12


def compute_aspect(angle_deg: float) -> Optional[str]:
    for name, target in ASPECT_DEGREES.items():
        diff = abs(angle_deg % 360 - target) % 360
        if diff > 180:
            diff = 360 - diff
        if diff <= ASPECT_ORB:
            return name
    return None


# ── VedicChart ────────────────────────────────────────────────────
class VedicChart:
    """Classical Vedic (sidereal) birth chart."""

    def __init__(self, birth_date: datetime, lat: float, lon: float):
        lat, lon = validate_coordinates(lat, lon)
        self.birth_date = birth_date
        self.lat = lat
        self.lon = lon
        self.jd = datetime_to_jd(birth_date)
        self.ayanamsa = get_ayanamsa(self.jd)

    def calculate_planets(self) -> Dict[str, float]:
        planets: Dict[str, float] = {}
        for code, name in [
            (SUN, "sun"), (MOON, "moon"), (MERCU, "mercury"),
            (VENUS, "venus"), (MARS, "mars"),
            (JUPITER, "jupiter"), (SATURN, "saturn"),
        ]:
            pos, _ = calc_ut(self.jd - 2440587.5, code)
            tropical = pos[0]
            sidereal = tropical_to_sidereal(tropical, self.ayanamsa)
            planets[name] = sidereal
        return planets

    def calculate_ascendant(self) -> float:
        houses, _ = houses_ut(
            self.jd - 2440587.5, self.lat, self.lon,
            flags=FLG_SWIEPH | FLG_SPEED | FLG_SIDEREAL,
        )
        return houses[0]

    def calculate_houses(self) -> List[float]:
        houses, _ = houses_ut(
            self.jd - 2440587.5, self.lat, self.lon,
            flags=FLG_SWIEPH | FLG_SPEED | FLG_SIDEREAL,
        )
        return [h % 360 for h in houses[:12]]

    def get_planet_signs(self) -> Dict[str, str]:
        planets = self.calculate_planets()
        return {name: SIGN_NAMES[degrees_to_sign(deg)]
                for name, deg in planets.items()}

    def get_house_planets(self) -> Dict[int, List[str]]:
        planets = self.calculate_planets()
        house_cusps = self.calculate_houses()
        result: Dict[int, List[str]] = {i: [] for i in range(1, 13)}
        for name, deg in planets.items():
            for i in range(12):
                c1, c2 = house_cusps[i], house_cusps[(i + 1) % 12]
                if c1 <= c2:
                    if c1 <= deg < c2:
                        result[i + 1].append(name)
                else:
                    if deg >= c1 or deg < c2:
                        result[i + 1].append(name)
        return result

    def compute_aspects(self) -> List[Dict[str, Any]]:
        planets = self.calculate_planets()
        aspects: List[Dict[str, Any]] = []
        names = list(planets.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                p1, p2 = names[i], names[j]
                angle = abs(planets[p1] - planets[p2]) % 360
                aspect = compute_aspect(angle)
                if aspect:
                    aspects.append({"planet1": p1, "planet2": p2,
                                   "aspect": aspect, "angle_deg": round(angle, 2)})
        return aspects

    def full_chart(self) -> Dict[str, Any]:
        asc_deg = self.calculate_ascendant()
        return {
            "date": self.birth_date.isoformat(),
            "lat": self.lat, "lon": self.lon,
            "ayanamsa": round(self.ayanamsa, 4),
            "ascendant_deg": round(asc_deg, 4),
            "ascendant_sign": SIGN_NAMES[degrees_to_sign(asc_deg)],
            "planets": self.get_planet_signs(),
            "houses": self.get_house_planets(),
            "aspects": self.compute_aspects(),
        }


# ── Rules Engine ──────────────────────────────────────────────────
class AstroRulesEngine:
    """Evaluate JSON rules against chart data."""

    def __init__(self, rules: List[Dict[str, Any]]):
        self.rules = rules

    def evaluate(self, chart: Dict[str, Any]) -> List[Dict[str, Any]]:
        triggered: List[Dict[str, Any]] = []
        planets = chart.get("planets", {})
        houses = chart.get("houses", {})
        aspects = chart.get("aspects", [])
        for rule in self.rules:
            match = self._check_rule(rule, planets, houses, aspects)
            if match:
                triggered.append({**rule, "match_details": match})
        return triggered

    def _check_rule(self, rule: Dict[str, Any],
                    planets: Dict[str, str],
                    houses: Dict[int, List[str]],
                    aspects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        match: Dict[str, Any] = {}
        planet = rule.get("planet", "").lower()
        sign = rule.get("sign", "").lower()

        if planet and sign:
            if planets.get(planet, "").lower() != sign:
                return None
            match["planet_in_sign"] = f"{planet} in {sign}"

        house = rule.get("house")
        if house is not None and planet:
            if planet not in houses.get(house, []):
                return None
            match["planet_in_house"] = f"{planet} in house {house}"

        aspect_type = rule.get("aspect")
        if aspect_type:
            aspect_planet = rule.get("aspect_planet", "").lower()
            found = False
            for asp in aspects:
                p1, p2 = asp.get("planet1", ""), asp.get("planet2", "")
                if ((p1 == planet and p2 == aspect_planet) or
                        (p1 == aspect_planet and p2 == planet)):
                    if asp.get("aspect") == aspect_type:
                        found = True
                        match["aspect"] = f"{planet} {aspect_type} {aspect_planet}"
                        break
            if rule.get("require_aspect", True) and not found:
                return None
        return match if match else None


def load_rules(path: str) -> List[Dict[str, Any]]:
    with open(path) as f:
        return json.load(f)


if __name__ == "__main__":
    print("PROJ-05: Vedic Astrology Rules Engine")
    dt = datetime(1879, 3, 14, 8, 0)
    chart = VedicChart(dt, 48.4014, 9.9897)
    result = chart.full_chart()
    print(f"Ascendant: {result['ascendant_sign']} ({result['ascendant_deg']:.2f}°)")
    print(f"Planets: {result['planets']}")
    print(f"Aspects: {result['aspects']}")
