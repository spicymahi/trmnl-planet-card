"""
The main daily entry point: computes today's values for a given planet,
injects them into card_template.html, screenshots the result, downscales
to the real TRMNL OG resolution, and dithers to true 1-bit.

Usage:
    python render_card.py --planet venus --hero assets/venus.png --out output/card.png
"""

import argparse
from datetime import date, datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright
from PIL import Image

import orbital_math as om
from render_html import render_html, build_fields

TRMNL_WIDTH = 800
TRMNL_HEIGHT = 480

# Screenshot at 2x the target resolution for crisper downscaling/dithering,
# matching the template's own natural width (1760-ish at 2:1 ratio).
RENDER_WIDTH = 1600
RENDER_HEIGHT = 800

PLANET_SUBTITLES = {
    "mercury": "THE SWIFT PLANET",
    "venus": "THE EVENING STAR",
    "earth": "THE BLUE MARBLE",
    "mars": "THE RED PLANET",
    "jupiter": "THE GIANT PLANET",
    "saturn": "THE RINGED PLANET",
    "uranus": "THE TILTED PLANET",
    "neptune": "THE WINDY PLANET",
}


def compute_fields(planet_key: str, when: datetime) -> dict:
    today = when.date()

    distance_km = om.distance_from_earth_km(planet_key, today)
    distance_m_km = distance_km / 1_000_000
    trend = om.distance_trend(planet_key, today)
    trend_label = {
        "closer": "GETTING CLOSER \u2193",
        "farther": "GETTING FARTHER \u2191",
        "steady": "STEADY \u2192",
    }[trend]

    delay_min, delay_sec = om.light_delay(planet_key, today)
    day_n, period_n, pct = om.planet_year_progress(planet_key, today)
    season_label = om.season(planet_key, today).upper()
    local_time = om.local_solar_time(planet_key, when)
    date_str = today.strftime("%m / %d / %Y")

    planet_name = om.PLANETS[planet_key]["name"]
    subtitle = PLANET_SUBTITLES.get(planet_key, "")

    fields = build_fields(
        planet_name=planet_name,
        planet_subtitle=subtitle,
        date_str=date_str,
        distance_value=f"{distance_m_km:.1f} MILLION KM",
        distance_trend=trend_label,
        light_delay_value=f"{delay_min} MIN {delay_sec} SEC",
        day_n=day_n,
        period_n=period_n,
        day_percent=pct,
        local_time=local_time,
        local_time_label=f"{planet_name} SOLAR TIME",
        season=season_label,
        orbit_percent=pct,
    )
    return fields, pct


def screenshot_html(html_path: Path, png_path: Path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": RENDER_WIDTH, "height": RENDER_HEIGHT})
        page.goto(f"file://{html_path.resolve()}")
        page.wait_for_timeout(1500)  # let webfonts finish loading
        page.screenshot(path=str(png_path), full_page=True)
        browser.close()


def downscale_and_dither(src_path: Path, dst_path: Path):
    im = Image.open(src_path).convert("L")
    resized = im.resize((TRMNL_WIDTH, TRMNL_HEIGHT), Image.LANCZOS)
    dithered = resized.convert("1")  # PIL's default 'L'->'1' uses Floyd-Steinberg
    dithered.save(dst_path)


def render(planet_key: str, hero_image_path: str, out_path: str, when: datetime | None = None):
    when = when or datetime.now(timezone.utc)
    fields, pct = compute_fields(planet_key, when)

    html = render_html(fields, hero_image_path=hero_image_path, day_percent=pct, orbit_percent=pct)

    tmp_html = Path("output/_tmp_card.html")
    tmp_html.parent.mkdir(parents=True, exist_ok=True)
    tmp_html.write_text(html)

    tmp_png = Path("output/_tmp_card_raw.png")
    screenshot_html(tmp_html, tmp_png)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    downscale_and_dither(tmp_png, out)

    print(f"Saved {out}")
    print(f"  planet={planet_key} date={fields['dateStr']} "
          f"distance={fields['distanceValue']} delay={fields['lightDelayValue']} "
          f"day={fields['dayN']}/{fields['periodN']} ({pct}%) "
          f"time={fields['localTime']} season={fields['season']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--planet", default="venus")
    parser.add_argument("--hero", required=True, help="Path to the planet PNG/JPG for the hero image slot")
    parser.add_argument("--out", default="output/card.png")
    args = parser.parse_args()
    render(args.planet, args.hero, args.out)
