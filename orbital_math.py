"""
Simplified orbital mechanics for the Planet Card.

These are deliberately approximate (circular, coplanar orbits) — the goal is a
plausible, smoothly-changing display, not ephemeris-grade accuracy.
"""

import math
from datetime import date, datetime, timezone

# Orbital period in Earth days, and mean orbital radius in AU, per planet.
# Epoch reference: Jan 1, 2000 (J2000), each planet placed at angle 0 for
# simplicity — real world starting positions differ, but since this is a
# stylistic approximation, a shared epoch keeps the math simple and consistent.
PLANETS = {
    "mercury": {"period_days": 88.0,    "radius_au": 0.39, "name": "MERCURY", "symbol": "\u263F"},
    "venus":   {"period_days": 224.7,   "radius_au": 0.72, "name": "VENUS",   "symbol": "\u2640"},
    "earth":   {"period_days": 365.25,  "radius_au": 1.00, "name": "EARTH",   "symbol": "\u2295"},
    "mars":    {"period_days": 687.0,   "radius_au": 1.52, "name": "MARS",    "symbol": "\u2642"},
    "jupiter": {"period_days": 4331.0,  "radius_au": 5.20, "name": "JUPITER", "symbol": "\u2643"},
    "saturn":  {"period_days": 10747.0, "radius_au": 9.58, "name": "SATURN",  "symbol": "\u2644"},
    "uranus":  {"period_days": 30589.0, "radius_au": 19.2, "name": "URANUS",  "symbol": "\u2645"},
    "neptune": {"period_days": 59800.0, "radius_au": 30.1, "name": "NEPTUNE", "symbol": "\u2646"},
}

EPOCH = date(2000, 1, 1)
AU_KM = 149_597_870.7
LIGHT_SPEED_KM_S = 299_792.458
MARS_SOL_HOURS = 24 + 39 / 60 + 35 / 3600  # Mars day length ("sol") in hours


def days_since_epoch(d: date) -> float:
    return (d - EPOCH).days


def orbital_angle_deg(planet_key: str, d: date) -> float:
    """Current angle (degrees) of a planet around the Sun, circular-orbit approx."""
    period = PLANETS[planet_key]["period_days"]
    days = days_since_epoch(d)
    return (days / period * 360.0) % 360.0


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
    """Simplified local solar clock — NOT true LMST, just a plausible-looking
    clock that advances at the planet's own day-length rate.

    For Mars we use the real sol length; for other planets not yet modeled
    for day-length, we fall back to Earth's 24h for simplicity.
    """
    sol_hours = MARS_SOL_HOURS if planet_key == "mars" else 24.0
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
    """Pick which planet to feature today, cycling through a fixed order."""
    order = rotation_order or list(PLANETS.keys())
    idx = days_since_epoch(d) % len(order)
    return order[idx]
