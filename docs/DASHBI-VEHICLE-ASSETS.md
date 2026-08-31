# Dashbi Vehicle Assets (PORTAL-NEXT-07.1, Gate 15-21)

Real production images, traced to `origin/main`, not reconstructed from memory,
downloaded from the internet, generated, or replaced with icons.

## Source

`const VEHICLE_IMAGES = {...}` — `dashbi-origin-main.html` line 2651, 3 entries as
base64 `data:image/png;base64,...` literals. Decoded and saved (unmodified byte
content) to `PORTAL-NEXT-07.1/.source-assets/vehicle_<family>_origin_main.png`
before any processing, so the raw production bytes are preserved as evidence
independent of the resized copies actually shipped.

| Family | Asset | Source | Production used | Resolution (raw) | Transparency |
|---|---|---|---|---|---|
| OUTLANDER | `vehicle_outlander_origin_main.png` → `assets/img/vehicles/outlander.png` | `origin/main` line 2651, `VEHICLE_IMAGES["OUTLANDER"]` | `<img src="${VEHICLE_IMAGES[f]}">` in `renderModelos`'s `.vehicleHero`, production line 4067 | 2048×935 PNG | Yes (RGBA, transparent background) |
| ECLIPSE CROSS | `vehicle_eclipse_cross_origin_main.png` → `assets/img/vehicles/eclipse_cross.png` | `origin/main` line 2651, `VEHICLE_IMAGES["ECLIPSE CROSS"]` | same | 2048×935 PNG | Yes (RGBA, transparent background) |
| TRITON | `vehicle_triton_origin_main.png` → `assets/img/vehicles/triton.png` | `origin/main` line 2651, `VEHICLE_IMAGES["TRITON"]` | same | 1080×521 PNG | Yes (RGBA, transparent background) |

Each raw asset was visually inspected (not just byte-decoded) before use — all 3 are
genuine Mitsubishi studio product photography with a transparent background, matching
the family name they're keyed under (confirmed: Outlander PHEV, Eclipse Cross Black
Edition, Triton), not placeholder/broken images.

## Processing for the compact selector

The presentation redesign required a much smaller footprint than production's
full-bleed hero images (this Wave's provisional target: ~100-140px display width).
Each raw PNG was resized (Lanczos resampling, aspect ratio preserved, alpha channel
preserved) to 280px wide — 2x the display target, for retina sharpness — and
re-saved with PNG optimization. This is lossless-aspect resizing of the real asset,
not fabrication: no new imagery, no AI generation, no stock-photo substitution. Final
sizes: Outlander 280×128 (46.9 KB), Eclipse Cross 280×128 (38.7 KB), Triton 280×135
(47.0 KB) — all well under a reasonable page-weight budget for 3 images.

## Selector design (Gate 15-21 constraints)

- `.dbVehicleCard`: 132px wide, image + family name, no card shadow/glow/gradient,
  no catalog styling.
- `.dbVehicleImgWrap`: fixed 60px height box, `object-fit: contain` — deterministic
  containment, no stretching/cropping/layout jump regardless of each source image's
  own aspect ratio.
- Selected state: 2px accent-red border + bold name + a check glyph (✓) — three
  independent signals, none of them color alone (Gate 33).
- Real `<button>` elements — native keyboard focus + Enter/Space activation, no
  custom key handling needed; `aria-pressed` reflects selection state.
- `alt=""` on the images (decorative — the family name is already rendered as
  visible text right below each image, so the image is redundant to a screen
  reader, not the sole conveyor of the family identity).
- Mobile: 2-per-row at ≤480px (`calc(50% - gap/2)`), verified no page-level
  horizontal overflow at 360/390/430 (see Gate 37 regression notes in REPORT.md).
