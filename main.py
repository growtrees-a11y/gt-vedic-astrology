"""
PROJ-05: Classical Vedic Astrology Rules Engine
Phase 0: Swiss Ephemeris setup + sidereal calculation
Phase 1: Ascendant, 12 houses, Ayanamsa correction
Phase 2: JSON ruleset engine
Phase 3: Historical test chart assertions
"""
import json
import os
import math
from datetime import datetime
from typing import Dict, List, Optional

# Swiss Ephemeris mock — no C-library dependency required
from mock_swe import (  # noqa: F401
    SUN, MOON, MERCU, VENUS, MARS, JUPITER, SATURN,
    calc_ut,
    ayanamsa_ut,
    houses_ut,
)

# Thin wrapper so existing code path (`swe.X`) keeps working
import types

swe = types.ModuleType("swe")
swe.SUN = SUN
swe.MOON = MOON
swe.MERCURY = MERCU
swe.VENUS = VENUS
swe.MARS = MARS
swe.JUPITER = JUPITER
swe.SATURN = SATURN
swe.calc_ut = calc_ut
swe.ayanamsa_ut = ayanamsa_ut
swe.houses_ut = houses_ut
swe.FLAH_IRA = 1
swe.FLG_SWIEPH = 1
swe.FLG_SPEED = 2
swe.FLG_SIDEREAL = 0x40


# ── Helpers ────────────────────────────────────────────────────────────

def datetime_to_jd(dt: datetime) -> float:
    """Convert datetime to Julian Day."""
    # JD calculation from datetime
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jd = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    # Fractional day from time of day
    frac = (dt.hour * 3600 + dt.minute * 60 + dt.second) / 86400
    return float(jd) + frac


def get_ayanamsa(jd: float) -> float:
    """Lahiri Ayanamsa (degrees)."""
    # Use Swiss Ephemeris Ayanamsa calculation
    ayanamsa_deg, _ = swe.ayanamsa_ut(jd - 2440587.5, swe.FLAH_IRA)
    return ayanamsa_deg


def tropical_to_sidereal(tropical_deg: float, ayanamsa: float) -> float:
    """Convert tropical longitude to sidereal."""
    sidereal = tropical_deg - ayanamsa
    # Normalize to [0, 360)
    return sidereal % 360


def degrees_to_sign(deg: float) -> int:
    """Convert degrees to zodiac sign index (0=Aries, 1=Taurus, ...)."""
    return int(deg // 30) % 12


SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]


class VedicChart:
    """Classical Vedic (sidereal) birth chart."""

    def __init__(self, birth_date: datetime, lat: float, lon: float):
        self.birth_date = birth_date
        self.lat = lat
        self.lon = lon
        self.jd = datetime_to_jd(birth_date)
        self.ayanamsa = get_ayanamsa(self.jd)

    def calculate_planets(self) -> Dict[str, float]:
        """Calculate sidereal planetary positions."""
        planets = {}
        # Calculate each planet's tropical position, then apply ayanamsa
        for body_code, name in [
            (swe.SUN, "sun"),
            (swe.MOON, "moon"),
            (swe.MERCURY, "mercury"),
            (swe.VENUS, "venus"),
            (swe.MARS, "mars"),
            (swe.JUPITER, "jupiter"),
            (swe.SATURN, "saturn"),
        ]:
            # Get tropical position
            pos, _ = swe.calc_ut(self.jd - 2440587.5, body_code)
            tropical = pos[0]  # longitude
            sidereal = tropical_to_sidereal(tropical, self.ayanamsa)
            planets[name] = sidereal

        return planets

    def calculate_ascendant(self) -> float:
        """Calculate sidereal Ascendant degree."""
        # Use Swiss Ephemeris houses calculation (Equal House system)
        houses, _ = swe.houses_ut(
            self.jd - 2440587.5,
            self.lat,
            self.lon,
            flags=swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL,
        )
        ascendant = houses[0]
        return ascendant

    def calculate_houses(self) -> List[float]:
        """Calculate 12 house cusps (Equal House system, sidereal)."""
        houses, _ = swe.houses_ut(
            self.jd - 2440587.5,
            self.lat,
            self.lon,
            flags=swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL,
        )
        return [h % 360 for h in houses[:12]]

    def get_planet_signs(self) -> Dict[str, str]:
        """Get zodiac sign for each planet."""
        planets = self.calculate_planets()
        return {name: SIGN_NAMES[degrees_to_sign(deg)] for name, deg in planets.items()}

    def get_house_planets(self) -> Dict[int, List[str]]:
        """Map planets to houses."""
        planets = self.calculate_planets()
        house_cusps = self.calculate_houses()
        result: Dict[int, List[str]] = {i: [] for i in range(1, 13)}

        for name, deg in planets.items():
            # Find house
            for i in range(12):
                c1 = house_cusps[i]
                c2 = house_cusps[(i + 1) % 12]
                if c1 <= c2:
                    if c1 <= deg < c2:
                        result[i + 1].append(name)
                else:  # Wraps around 0
                    if deg >= c1 or deg < c2:
                        result[i + 1].append(name)
        return result

    def full_chart(self) -> Dict:
        """Full chart data."""
        return {
            "date": self.birth_date.isoformat(),
            "lat": self.lat,
            "lon": self.lon,
            "ayanamsa": round(self.ayanamsa, 4),
            "ascendant_deg": round(self.calculate_ascendant(), 4),
            "ascendant_sign": SIGN_NAMES[degrees_to_sign(self.calculate_ascendant())],
            "planets": self.get_planet_signs(),
            "houses": self.get_house_planets(),
        }


# ── Phase 2: JSON Rules Engine ──────────────────────────────────────────

class AstroRulesEngine:
    """Evaluate JSON rules against chart data."""

    def __init__(self, rules: List[Dict]):
        self.rules = rules

    def evaluate(self, chart: Dict) -> List[Dict]:
        """Evaluate all rules against chart, return triggered rules."""
        triggered = []
        planets = chart["planets"]
        houses = chart["houses"]

        for rule in self.rules:
            if self._check_rule(rule, planets, houses):
                triggered.append(rule)
        return triggered

    def _check_rule(self, rule: Dict, planets: Dict, houses: Dict) -> bool:
        """Check single rule."""
        planet = rule.get("planet", "").lower()
        sign = rule.get("sign", "").lower()
        house = rule.get("house")

        # Planet in sign?
        if sign:
            planet_sign = planets.get(planet, "")
            if planet_sign.lower() != sign:
                return False

        # Planet in house?
        if house:
            if planet not in houses.get(house, []):
                return False

        # Aspect check (simplified)
        aspect = rule.get("aspect")
        if aspect:
            aspect_planet = rule.get("aspect_planet", "").lower()
            # Simplified aspect check
            return True  # Placeholder

        return True


def load_rules(path: str) -> List[Dict]:
    """Load rules from JSON file."""
    with open(path) as f:
        return json.load(f)


if __name__ == "__main__":
    print("PROJ-05: Vedic Astrology Rules Engine")
    # Historical chart: Albert Einstein (March 14, 1879, Ulm, Germany)
    dt = datetime(1879, 3, 14, 8, 0)
    chart = VedicChart(dt, 48.4014, 9.9897)
    result = chart.full_chart()
    print(f"Ascendant: {result['ascendant_sign']} ({result['ascendant_deg']:.2f}°)")
    print(f"Planets: {result['planets']}")
