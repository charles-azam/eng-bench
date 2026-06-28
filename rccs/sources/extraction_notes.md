# Source Provenance & Extraction Notes

Where the curated numbers came from, and what still lives only in figures. This is the audit
trail behind `inputs/` and `refs/`.

## Source documents (in `sources/pdfs/` and extracted to `sources/text/`)

| File | Document | Role |
|---|---|---|
| `NSTF_air_final_results_1350591.pdf` (339 pp) | **ANL-ART-47**, *Final Project Report on RCCS Testing with the Air-Based NSTF* (Argonne, Aug 2016) | **Keystone.** Geometry, sensors, BCs, and all measured results. NQA-1 quality. |
| `NSTF_air_ambient_effects_1389835.pdf` (13 pp) | **ICONE25-67418**, Hu et al., *Modeling the Ambient Condition Effects of an Air-Cooled Natural Circulation System* (2017) | The weather-effect correlation + RELAP5/CFD ambient handling. |

(Two other reports — the ½-scale design report OSTI/1184668 and the computational-modeling final
report OSTI/1429403 — returned HTML landing pages on direct fetch and were not needed: ANL-ART-47
is self-contained. `publications.anl.gov` sits behind a Cloudflare challenge. They can be added
later via a browser if the figure-level detail below is wanted.)

## Section → content map (ANL-ART-47)

| Report section | Used for | Lands in |
|---|---|---|
| §1.4 Scaling (Tables 3–5) | ½-scale ratios, 227→12 risers, sector slice, design duty | inputs/01 |
| §3.2 Flow path, §3.2.3 Riser Ducts | downcomer/plena/chimney/riser dimensions | inputs/01 |
| §3.3 Heated cavity/wall/plate | cavity dims, plate material & emissivity, heater zones | inputs/01, 02 |
| §3.4 Insulation (Table 9) | insulation materials, k(T), thickness | inputs/02 |
| §4.2 Sensors (Tables 12–14) | instrument types, counts, **locations** (Riser 7, mid-plane) | inputs/03 |
| §4.3 Heater Power Control | 40-zone shaping, max power, control modes | inputs/04 |
| §5.3 Heat Losses | ~65% efficiency (HELD OUT) | refs/measured_data |
| §5.4 Physical Properties (Tables 21–22) | Re/Ra/Ri regime, h ≈ 3–6 W/m²·K | inputs/02 |
| §6.4 Prototypic Conditions (Tables 25–26) | decay-heat polynomial, cosine/azimuthal peaking | inputs/04 |
| §6.1–6.3 Computational models, ambient correlations | RELAP5/STAR-CCM+ accuracy, ṁ correlation | refs/national_lab_own_models, refs/weather_effect |
| §7.1 Baseline (Tables 31–32) | **the primary measured targets** | refs/measured_data, reference_values.json |
| §7.2 Cosine/Azimuthal (Tables 26, 33) | shape-variation results | refs/measured_data |
| §7.3 Accident (Tables 35, 37) | accident transient peaks, winter/summer | refs/measured_data |
| §7.5 Meteorological influences | weather magnitude, wind events | refs/weather_effect |

## Known reporting quirks (carried through honestly)

- Heated area listed as **8.82 m²** (Table 4 scaling) vs **10.18 m²** (as-built plate, §3.3) —
  ~12% inconsistency; use 10.18 m² for the plate.
- Ceramic-heater count **200** (§3.3.5, =10×20) vs **220** (§3.3.4).
- Riser-bank flow area in Table 10 printed with unit "m" — read as **m²** (0.078–0.155 m²).
- Some Table-37 mass-flow values carry unit "kg/s" but are numerically kg/min (cross-check vs the
  0.5 kg/s baseline). reference_values.json uses the consistent SI values.
- Max/Min column labels are swapped in a few Table-32 rows; the per-run values are correct.

## Geometry details that live only in figures (not numeric in text)

These were flagged as GAPS; the agent is told to choose & justify (see inputs/01 §9):
- Riser center-to-center pitch — Figure 19 (plan view). Nominal ≈ 52 in / 12 ≈ 4.3 in.
- Heated-plate exact height × width — Figure 21.
- Riser cross-section internal detail — Figure 11.
- Wall/plate thermocouple axial stations — Figures 30, 35–37.
- East-wall nine-layer stack thicknesses — Figure 25.
- Decay-heat curve C10 coefficient — referenced but not listed (C0–C9 reproduce it to 0.99996).

If figure-level precision is needed later, render the relevant PDF pages directly (the report is
in `sources/pdfs/`); the page offset is ≈ report-page + front-matter (Introduction "p.3" ≈ PDF
p. ~12).
