"""
Turns card_template.html (exported from Claude Design, with {{ }} bindings)
into a plain, self-contained static HTML file with today's real values
baked in -- no React runtime, no custom elements, just plain HTML/CSS that
any headless browser can screenshot directly.

This does three kinds of substitution:
  1. Simple {{ fieldName }} -> literal text (via TEXT_FIELDS)
  2. The two sc-for progress-bar loops -> expanded literal <span> elements
  3. The <x-import ... id="planet-art" ...> image slot -> a plain <img> tag
     pointing at whatever planet PNG/JPG you provide

Usage:
    python render_html.py --planet venus --hero assets/venus.png --out output/card.html
"""

import argparse
import re
from pathlib import Path

TEMPLATE_PATH = Path(__file__).parent / "card_template.html"


def make_squares_html(percent: int, count: int, size_px: int) -> str:
    """Expands what the sc-for loop would have rendered: `count` spans,
    the first round(count * percent/100) filled black, rest transparent."""
    filled = round(count * percent / 100)
    spans = []
    for i in range(count):
        bg = "#111111" if i < filled else "transparent"
        spans.append(
            f'<span style="width: {size_px}px; height: {size_px}px; '
            f'border: 1.5px solid #111111; background: {bg};"></span>'
        )
    return "\n              ".join(spans)


def render_html(fields: dict, hero_image_path: str, day_percent: int, orbit_percent: int) -> str:
    html = TEMPLATE_PATH.read_text()

    # --- 0a. Drop the opaque internal asset-loader <script src="UUID">.
    #          This referenced a script bundled inside Claude Design's own
    #          asset manifest; it has no meaning outside that environment. ---
    html = re.sub(r'<script src="[0-9a-f-]{36}"></script>\n?', "", html)

    # --- 0b. Replace the <helmet>...</helmet> block (Claude Design's
    #          head-injection convention, containing @font-face rules that
    #          point at opaque asset UUIDs) with a plain Google Fonts link.
    #          Archivo Black + Space Mono are both free/open on Google Fonts,
    #          which is what this template actually uses. ---
    google_fonts_link = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link href="https://fonts.googleapis.com/css2?'
        'family=Archivo+Black&family=Space+Mono:wght@400;700&display=swap" '
        'rel="stylesheet">\n'
        '<style>\n'
        '  body { margin: 0; background: #e9e9e6; }\n'
        '  a { color: #111111; }\n'
        '  a:hover { color: #444444; }\n'
        '</style>\n'
    )
    html = re.sub(r"<helmet>.*?</helmet>", google_fonts_link, html, flags=re.DOTALL)

    # --- 1. Strip the outer <x-dc> wrapper tags (keep their contents) ---
    html = html.replace("<x-dc>\n", "", 1)
    html = html.replace("\n</x-dc>", "", 1)

    # --- 2. Drop the trailing <script type="text/x-dc"> logic block entirely.
    #         We've already computed everything in Python. ---
    html = re.sub(
        r'<script type="text/x-dc".*?</script>\s*$',
        "",
        html,
        flags=re.DOTALL,
    )

    # --- 3. Replace the image-slot custom element with a plain <img> ---
    html = re.sub(
        r'<x-import[^>]*id="planet-art"[^>]*></x-import>',
        f'<img src="{hero_image_path}" alt="planet" '
        f'style="width:100%;height:100%;object-fit:contain;border-radius:8px;">',
        html,
    )

    # --- 4. Expand the two sc-for progress-bar loops into literal spans ---
    html = re.sub(
        r'<sc-for list="\{\{ daySquares \}\}"[^>]*>.*?</sc-for>',
        make_squares_html(day_percent, count=20, size_px=13),
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r'<sc-for list="\{\{ orbitSquares \}\}"[^>]*>.*?</sc-for>',
        make_squares_html(orbit_percent, count=26, size_px=14),
        html,
        flags=re.DOTALL,
    )

    # --- 5. Substitute every remaining {{ field }} with its literal value ---
    def replace_field(match):
        key = match.group(1).strip()
        if key not in fields:
            raise KeyError(
                f"Template references {{{{ {key} }}}} but no value was supplied. "
                f"Add it to the `fields` dict in render_html()'s caller."
            )
        return str(fields[key])

    html = re.sub(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}", replace_field, html)

    return html


def build_fields(
    planet_name: str,
    planet_subtitle: str,
    date_str: str,
    distance_value: str,
    distance_trend: str,
    light_delay_value: str,
    day_n: int,
    period_n: int,
    day_percent: int,
    local_time: str,
    local_time_label: str,
    season: str,
    orbit_percent: int,
) -> dict:
    return {
        "planetName": planet_name,
        "planetSubtitle": planet_subtitle,
        "dateStr": date_str,
        "distanceValue": distance_value,
        "distanceTrend": distance_trend,
        "lightDelayValue": light_delay_value,
        "dayN": day_n,
        "periodN": period_n,
        "dayPercent": day_percent,
        "localTime": local_time,
        "localTimeLabel": local_time_label,
        "season": season,
        "orbitPercent": orbit_percent,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hero", required=True, help="Path or URL to the planet PNG/JPG")
    parser.add_argument("--out", default="output/card.html")
    args = parser.parse_args()

    # Demo values matching the template's own defaults, just to confirm
    # the pipeline runs end to end. Real values come from orbital_math.py
    # via the daily render script.
    fields = build_fields(
        planet_name="VENUS",
        planet_subtitle="THE EVENING STAR",
        date_str="04 / 09 / 2026",
        distance_value="41.2 MILLION KM",
        distance_trend="GETTING CLOSER \u2193",
        light_delay_value="2 MIN 17 SEC",
        day_n=102,
        period_n=225,
        day_percent=45,
        local_time="10:23",
        local_time_label="VENUS SOLAR TIME",
        season="NORTHERN WINTER",
        orbit_percent=45,
    )

    html = render_html(fields, hero_image_path=args.hero, day_percent=45, orbit_percent=45)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    print(f"Saved {out_path}")
