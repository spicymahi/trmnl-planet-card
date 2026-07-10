# TRMNL Planet Card (v2 — HTML/CSS template)

A daily-updating "planet mission card" for a TRMNL OG (800×400, 1-bit
e-ink) display. The card layout comes from a real HTML/CSS template
(exported from Claude Design), with the dynamic fields wired up as
`{{ placeholders }}`. A small Python script computes today's values using
simplified orbital math, injects them into the template, screenshots the
result with a headless browser, downsizes it to the real device
resolution, and dithers it to true 1-bit — matching TRMNL's own
recommended image pipeline (Floyd-Steinberg dithering).

A GitHub Action re-runs this once a day and commits the new image, so
TRMNL just displays whatever's at a fixed URL.

## How it fits together

```
card_template.html   <- the Claude Design export, with {{ field }} bindings
        |
        v
orbital_math.py       <- computes today's distance, light delay, season, etc.
        |
        v
render_html.py         <- substitutes {{ fields }} with real values,
                           expands the two progress-bar loops,
                           swaps the image-slot for a plain <img> tag
        |
        v
render_card.py           <- orchestrates the above, screenshots the HTML
                             with Playwright, downsizes to 800x400,
                             dithers to 1-bit
        |
        v
output/card.png            <- the finished image TRMNL displays
```

## One-time setup

1. **Add your planet artwork.** Drop your hero image (the planet
   portrait) into `assets/` — e.g. `assets/venus.png`. This is the file
   that goes into the empty box on the left side of the card. See "Art
   direction notes" below for what actually holds up on 1-bit e-ink.

2. **Push this repo to GitHub**, enable Actions if prompted.

3. **Trigger the first render manually**: Actions tab → "Render daily
   planet card" → "Run workflow". This installs Playwright's headless
   Chromium, renders the card, and commits `output/card.png`.

4. **Grab the raw image URL**:

   ```
   https://raw.githubusercontent.com/<your-username>/<your-repo>/main/output/card.png
   ```

5. **Point TRMNL at that URL** as a static image source in your private
   plugin settings.

## Running it locally

```bash
pip install -r requirements.txt
playwright install --with-deps chromium
python render_card.py --planet venus --hero assets/venus.png --out output/card.png
```

## Why HTML/CSS instead of drawing on a flattened image

Earlier versions of this project tried overlaying text directly onto a
flattened PNG template using Pillow, with hand-measured pixel coordinates
for every field. That works, but it's fragile — every coordinate has to
be re-measured if the layout changes, and font-matching has to be done by
hand.

Since the template is actually a real HTML/CSS layout (built in Claude
Design), rendering the HTML directly with live data is far more robust:
the browser's layout engine handles all spacing and alignment
automatically, real webfonts render correctly, and there's no risk of
text overlapping.

## Dynamic fields

| Field | Source |
|---|---|
| Planet name / subtitle | Static per planet (see `PLANET_SUBTITLES` in `render_card.py`) |
| Date (top right) | Today's real-world date |
| Distance from Earth (+ trend) | Computed (simplified orbital math) |
| Light delay | Derived from distance |
| Planet year (day/total + %) | Computed from orbital period |
| Local solar time | Simplified planet-day-length approximation |
| Season | Derived from orbital angle (stylized, not astronomically literal — see note below) |
| Orbit progress (bottom bar) | Same % as planet year, rendered as a segmented bar |

Everything else (the "Today Elsewhere" fact card, the bottom
solar-system strip, footer, planet symbol) is static markup in
`card_template.html`.

**Note on "Season":** this is deliberately the same simplified
orbital-angle-based logic for every planet, purely for flavor/aesthetic
consistency — it doesn't attempt to model each planet's actual axial
tilt (e.g. Venus has almost no real seasons in nature, but the card shows
one anyway for a uniform look across planets).

## Adding more planets

1. Add orbital constants for the planet in `orbital_math.py` (most are
   already there — see `PLANETS` dict).
2. Add a subtitle in `PLANET_SUBTITLES` in `render_card.py`.
3. Add a hero image to `assets/<planet>.png`.
4. Run with `--planet <planet> --hero assets/<planet>.png`.

The card layout itself doesn't need to change — same template, same
field bindings, just different values and a different hero image.

## Art direction notes (important for the hero image)

TRMNL OG is **true 1-bit** — every pixel is pure black or white, no gray.
Through testing, we found:

- **Photographic/halftone dot-matrix portraits look great in grayscale
  preview but turn to visual noise once dithered to real 1-bit** at
  800×400, because the fine dot density needed to fake tonal gradients
  doesn't survive the resolution drop.
- **Line-art / contour-style portraits (like topographic maps) hold up
  much better** — they're built from clean strokes rather than faked
  gradients, so they stay legible after dithering.

Recommendation: design hero art with bold, deliberate linework rather
than fine photographic detail. Design at 2x the target box size for
crisper results, and preview it through the actual dither pipeline
(`render_card.py`) before finalizing — a grayscale preview alone can be
misleading about how it'll really look on-device.

## Accuracy notes

All astronomical values are **simplified approximations** (circular,
coplanar orbits), not ephemeris-grade calculations — designed to look
plausible and change smoothly day to day, not to be scientifically
precise. See the docstring at the top of `orbital_math.py`.

## Fonts

The template uses **Archivo Black** and **Space Mono**, both loaded live
from Google Fonts at render time. This requires internet access during
rendering (available in GitHub Actions; if running locally without
internet, the browser will fall back to system fonts).
