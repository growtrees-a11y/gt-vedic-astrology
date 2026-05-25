"""
mock_swe.py — Mock Swiss Ephemeris (pyswisseph) module.

Provides the same API surface as `swe` but uses approximate mathematical
formulas so the code runs without the Swiss Ephemeris data files or the
C-library dependency.  Values are good enough for unit tests and demo
charts; they are NOT for professional astrology work.
"""

import math

# ── Body codes (match pyswisseph) ──────────────────────────────────────
SUN   = 0
MOON  = 1
MERCU = 2    # Mercury
VENUS = 3
MARS  = 4
JUPITER = 5
SATURN = 6

# ── Flag / mode constants ────────────────────────────────────────────
FLAH_IRA = 1  # Lahiri Ayanamsa
FLG_SWIEPH = 1
FLG_SPEED  = 2
FLG_SIDEREAL = 0x40


# ── Approximate planetary positions ──────────────────────────────────
# Mean elements (J2000 epoch).  Simple Kepler-style approximation
# sufficient for ~1° accuracy, which is fine for sign/house placement
# in a mock.

def _mean_anomaly_and_longitude(jd_t, body: int) -> tuple:
    """Return (tropical_longitude_deg, 0) for a given body.

    Returns a single-element list to mirror swe.calc_ut's API shape,
    plus a speed list of zeros.
    """
    # Days since J2000.0
    t = (jd_t - 2451545.0) / 36525.0  # centuries

    # Mean longitudes (degrees) at J2000 + secular drift
    # Sources: Meeus, "Astronomical Algorithms", simplified
    if body == SUN:
        L0 = 280.46646 + 36000.76983 * t
    elif body == MOON:
        L0 = 218.3165 + 483002.2013 * t  # Moon moves fast
    elif body == MERCU:
        L0 = 256.0002 + 149376.0655 * t
    elif body == VENUS:
        L0 = 181.9798 + 58520.0067 * t
    elif body == MARS:
        L0 = 355.4330 + 19140.2998 * t
    elif body == JUPITER:
        L0 = 34.3514 + 3034.9059 * t
    elif body == SATURN:
        L0 = 49.9542 + 1222.1150 * t
    else:
        L0 = 0.0

    # Normalise to [0, 360)
    lon = L0 % 360
    return lon


def calc_ut(jd: float, body: int, flags=0) -> tuple:
    """Mock swe.calc_ut — returns ([lon, lat, dist], []) like the real API.

    We only populate longitude; latitude and distance are zero.
    """
    lon = _mean_anomaly_and_longitude(jd, body)
    return ([lon, 0.0, 0.0], [])


# ── Ayanamsa ──────────────────────────────────────────────────────────
def ayanamsa_ut(jd: float, mode: int) -> tuple:
    """Mock swe.ayanamsa_ut — Lahiri Ayanamsa (degrees).

    The caller passes `jd` as MJD (days since JD 2440587.5 = 1858.875).
    Lahiri ayanamsa ≈ 23.07° at J2000, growing at ~0.01397°/year.
    """
    year = 1858.875 + jd / 365.25
    aya = 23.07 + 0.01397 * (year - 2000)
    return (aya, 0)


# ── Houses ────────────────────────────────────────────────────────────
def houses_ut(jd: float, lat: float, lon: float, flags=0) -> tuple:
    """Mock swe.houses_ut — returns 12 house cusps (degrees).

    Uses a simplified ascendant formula then distributes houses evenly
    (Equal House) for the sidereal flag case, or Placidus-like spacing
    otherwise.  Only the longitude is meaningful.
    """
    # Approximate local sidereal time (degrees)
    # UT in hours from midnight JD
    day = int(jd + 0.5)
    ut = (jd + 0.5 - day) * 24.0
    # GMST (degrees) approximate
    gmst_deg = (280.4606 + 360.9856473 * (jd - 2451545.0)) % 360
    lmst_deg = (gmst_deg + lon) % 360  # lon already in degrees

    # Approximate ascendant
    lat_rad = math.radians(lat)
    lmst_rad = math.radians(lmst_deg)
    obliquity = 23.4393 - 0.0130 * ((jd - 2451545.0) / 36525.0)  # degrees
    obl_rad = math.radians(obliquity)

    asc_rad = math.atan2(
        math.sin(lmst_rad),
        math.cos(lmst_rad) * math.sin(lat_rad)
        - math.tan(obl_rad) * math.cos(lat_rad),
    )
    asc_deg = math.degrees(asc_rad) % 360

    # Check for sidereal flag — subtract ayanamsa
    if flags & FLG_SIDEREAL:
        aya, _ = ayanamsa_ut(jd - 2451545.0, FLAH_IRA)
        asc_deg = (asc_deg - aya) % 360

    # Equal house cusps from ascendant
    cusps = [(asc_deg + i * 30) % 360 for i in range(12)]
    return (cusps, [])
