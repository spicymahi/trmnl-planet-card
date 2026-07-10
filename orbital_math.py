"""
Simplified orbital mechanics for the Planet Card.

Orbital periods and radii are real; positions use real J2000 mean
longitudes (from JPL's low-precision planetary elements) as each planet's
true starting angle, then advance that angle uniformly over time assuming
a circular orbit. This is still an approximation (real orbits are
slightly elliptical, and we ignore orbital inclination), but starting each
planet from its real relative position -- instead of assuming every
planet lines up at angle 0 on the epoch date -- is what actually makes
Earth-to-planet distances come out realistic rather than arbitrary.
"""

import math
from datetime import date, datetime, timezone

# Orbital period in Earth days, mean orbital radius in AU, and mean
# longitude (degrees) at epoch J2000 (Jan 1, 2000), per planet. Mean
# longitude values are from JPL's "Keplerian Elements for Approximate
# Positions of the Major Planets" (https://ssd.jpl.nasa.gov/planets/approx_pos.html).
PLANETS = {
    "mercury": {"period_days": 88.0,    "radius_au": 0.39, "name": "MERCURY", "symbol": "\u263F", "L0": 252.25},
    "venus":   {"period_days": 224.7,   "radius_au": 0.72, "name": "VENUS",   "symbol": "\u2640", "L0": 181.98},
    "earth":   {"period_days": 365.25,  "radius_au": 1.00, "name": "EARTH",   "symbol": "\u2295", "L0": 100.47},
    "mars":    {"period_days": 687.0,   "radius_au": 1.52, "name": "MARS",    "symbol": "\u2642", "L0": 355.43},
    "jupiter": {"period_days": 4331.0,  "radius_au": 5.20, "name": "JUPITER", "symbol": "\u2643", "L0": 34.35},
    "saturn":  {"period_days": 10747.0, "radius_au": 9.58, "name": "SATURN",  "symbol": "\u2644", "L0": 50.08},
    "uranus":  {"period_days": 30589.0, "radius_au": 19.2, "name": "URANUS",  "symbol": "\u2645", "L0": 314.20},
    "neptune": {"period_days": 59800.0, "radius_au": 30.1, "name": "NEPTUNE", "symbol": "\u2646", "L0": 304.22},
}

EPOCH = date(2000, 1, 1)
AU_KM = 149_597_870.7
LIGHT_SPEED_KM_S = 299_792.458
MARS_SOL_HOURS = 24 + 39 / 60 + 35 / 3600  # Mars day length ("sol") in hours

# Real synodic ("solar day") length in hours for each planet -- the time
# from one local noon to the next, which is what a surface clock would
# actually track. Mercury and Venus have solar days vastly longer than
# their sidereal rotation because their slow/retrograde spin interacts
# with their own orbital motion; Venus's solar day is even longer than
# its entire year.
SOLAR_DAY_HOURS = {
    "mercury": 4222.6,
    "venus": 2802.0,
    "earth": 24.0,
    "mars": MARS_SOL_HOURS,
    "jupiter": 9.9,
    "saturn": 10.7,
    "uranus": 17.2,
    "neptune": 16.1,
}


def days_since_epoch(d: date) -> float:
    return (d - EPOCH).days


def orbital_angle_deg(planet_key: str, d: date) -> float:
    """Current angle (degrees) of a planet around the Sun, circular-orbit
    approx, starting from its real J2000 mean longitude rather than 0 --
    this is what makes relative planet positions (and therefore distances)
    come out realistic instead of arbitrary."""
    period = PLANETS[planet_key]["period_days"]
    l0 = PLANETS[planet_key]["L0"]
    days = days_since_epoch(d)
    return (l0 + days / period * 360.0) % 360.0


def heliocentric_distance_au(planet_a: str, planet_b: str, d: date) -> float:
    """Distance between two planets using law of cosines on circular orbits."""
    ra = PLANETS[planet_a]["radius_au"]
    rb = PLANETS[planet_b]["radius_au"]
    theta_a = math.radians(orbital_angle_deg(planet_a, d))
    theta_b = math.radians(orbital_angle_deg(planet_b, d))
    delta = theta_a - theta_b
    dist_sq = ra**2 + rb**2 - 2 * ra * rb * math.cos(delta)
    return math.sqrt(max(dist_sq, 0.0))


def distance_from_earth_km(planet_key: str, d: date) -> float:
    au = heliocentric_distance_au(planet_key, "earth", d)
    return au * AU_KM


def distance_trend(planet_key: str, d: date) -> str:
    """Compare today's distance to yesterday's to get a direction."""
    from datetime import timedelta
    today_dist = distance_from_earth_km(planet_key, d)
    yesterday_dist = distance_from_earth_km(planet_key, d - timedelta(days=1))
    if today_dist < yesterday_dist:
        return "closer"
    elif today_dist > yesterday_dist:
        return "farther"
    return "steady"


def light_delay(planet_key: str, d: date) -> tuple[int, int]:
    """Returns (minutes, seconds) light delay from Earth to planet, one-way."""
    km = distance_from_earth_km(planet_key, d)
    total_seconds = km / LIGHT_SPEED_KM_S
    minutes = int(total_seconds // 60)
    seconds = int(round(total_seconds % 60))
    if seconds == 60:
        seconds = 0
        minutes += 1
    return minutes, seconds


def planet_year_progress(planet_key: str, d: date) -> tuple[int, int, int]:
    """Returns (current_day, period_days_rounded, percent_complete)."""
    period = PLANETS[planet_key]["period_days"]
    days = days_since_epoch(d)
    current_day = int(days % period)
    if current_day == 0:
        current_day = int(period)
    percent = round((current_day / period) * 100)
    return current_day, round(period), percent


def season(planet_key: str, d: date) -> str:
    """Bucket orbital angle into a hemisphere-flavored season label.

    Purely illustrative — maps orbital quadrant to a season name using the
    convention that angle 0 = northern spring equinox.
    """
    angle = orbital_angle_deg(planet_key, d)
    if angle < 90:
        return "Northern Spring"
    elif angle < 180:
        return "Northern Summer"
    elif angle < 270:
        return "Northern Fall"
    else:
        return "Northern Winter"


def local_solar_time(planet_key: str, d: datetime) -> str:
    """Simplified local solar clock, using each planet's real solar-day
    length so the clock actually advances at a believable rate for that
    planet (e.g. Venus's clock crawls, Jupiter's spins fast) -- this is
    NOT a true position-dependent LMST calculation, just a stylized clock
    face driven by the real day length.
    """
    sol_hours = SOLAR_DAY_HOURS.get(planet_key, 24.0)
    # Use elapsed time since epoch (in hours) modulo the sol length,
    # scaled back into a 24-hour clock face for display purposes.
    epoch_dt = datetime(2000, 1, 1, tzinfo=timezone.utc)
    elapsed_hours = (d - epoch_dt).total_seconds() / 3600.0
    sol_fraction = (elapsed_hours % sol_hours) / sol_hours
    clock_hours = sol_fraction * 24.0
    hh = int(clock_hours)
    mm = int(round((clock_hours - hh) * 60))
    if mm == 60:
        mm = 0
        hh = (hh + 1) % 24
    return f"{hh:02d}:{mm:02d}"


def orbit_progress_percent(planet_key: str, d: date) -> int:
    """Same underlying value as planet_year_progress percent; exposed
    separately since it's rendered in two places on the card (progress bar
    and bottom orbital status bar) and callers may want just the number."""
    _, _, pct = planet_year_progress(planet_key, d)
    return pct


def todays_planet(d: date, rotation_order: list[str] | None = None) -> str:
    """Pick which planet to feature today.

    Uses a shuffled rotation: every 8 days, the full list of planets is
    reshuffled (deterministically, seeded from the cycle number) and then
    shown one per day in that shuffled order. This guarantees every planet
    appears once before any repeat, while still feeling "random" day to
    day, rather than a fixed Mercury-Venus-Earth-... sequence.

    Deliberately stateless: given the same date, this always produces the
    same planet, with no need to persist "which planets have I shown"
    anywhere between workflow runs.
    """
    import random

    planets = rotation_order or list(PLANETS.keys())
    n = len(planets)
    days = days_since_epoch(d)
    cycle_number = days // n       # which 8-day cycle we're in
    day_in_cycle = days % n        # position within that cycle's shuffle

    rng = random.Random(cycle_number)  # same cycle_number -> same shuffle, always
    shuffled = planets.copy()
    rng.shuffle(shuffled)

    return shuffled[day_in_cycle]
