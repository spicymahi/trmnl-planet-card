"""
The main daily entry point: computes today's values for a given planet,
injects them into card_template.html, screenshots the result at the
card's true native resolution (800x480, no scaling), and converts it to
pure 1-bit black/white.

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


# The template is now designed natively at 800x480 (the real TRMNL OG
# resolution) -- no scaling of any kind happens between the browser's
# render and the final image. This matters: any zoom/resize step, however
# carefully tuned, still involves resampling math that can blur or drop
# fine text and hairline dividers. Rendering 1:1 at the true target
# resolution sidesteps that class of problem entirely, the same way a
# native e-ink app would.


def screenshot_html(html_path: Path, png_path: Path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": TRMNL_WIDTH, "height": TRMNL_HEIGHT})
        page.goto(f"file://{html_path.resolve()}")
        page.wait_for_timeout(1200)  # let webfonts finish loading
        page.screenshot(path=str(png_path))  # not full_page: card is exactly viewport-sized
        browser.close()


def to_pure_bw(src_path: Path, dst_path: Path):
    """Convert to pure 1-bit black/white with a hard threshold.

    No resize happens here at all -- the screenshot is already exactly
    TRMNL_WIDTH x TRMNL_HEIGHT. A hard threshold (not Floyd-Steinberg
    dithering) keeps every line and letter an unambiguous solid black or
    white pixel, matching the crisp look of a native e-ink app.
    """
    im = Image.open(src_path).convert("L")
    assert im.size == (TRMNL_WIDTH, TRMNL_HEIGHT), (
        f"Expected exactly {TRMNL_WIDTH}x{TRMNL_HEIGHT}, got {{im.size}}. "
        f"Check that card_template.html's outer div is still sized "
        f"{TRMNL_WIDTH}x{TRMNL_HEIGHT} with no extra margin/padding overflow."
    )

    threshold = 128
    bw = im.point(lambda p: 255 if p > threshold else 0, mode="L").convert("1")
    bw.save(dst_path)


def render(planet_key: str, hero_image_path: str, out_path: str, when: datetime | None = None):
    when = when or datetime.now(timezone.utc)
    fields, pct = compute_fields(planet_key, when)

    # Resolve to an absolute path so the <img src="..."> reference works
    # regardless of where the temporary HTML file ends up on disk (it's
    # saved under output/, not the repo root, so a relative path would
    # otherwise point at the wrong location).
    hero_abs_path = str(Path(hero_image_path).resolve())

    html = render_html(fields, hero_image_path=hero_abs_path, day_percent=pct, orbit_percent=pct)

    tmp_html = Path("output/_tmp_card.html")
    tmp_html.parent.mkdir(parents=True, exist_ok=True)
    tmp_html.write_text(html)

    tmp_png = Path("output/_tmp_card_raw.png")
    screenshot_html(tmp_html, tmp_png)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    to_pure_bw(tmp_png, out)

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
