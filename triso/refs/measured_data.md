# HELD-OUT measured data — TRISO accident-heating prediction pack

**Do NOT expose any of this to the predicting agent.** These are the measured outcomes used to
score predictions against `pack/inputs/02_cases.md`. Every value carries a line-reference into the
source documents (1674 = TECDOC-1674_full.txt; 2090 = TECDOC-2090_full.txt).

Particle populations for normalization: spheres = 16,400 (HFR-K3) / 14,580 (HFR-K6);
compacts = 1631 (HFR-P4). One-particle Kr-85 fractional-release level ≈ 6×10⁻⁵ (sphere),
≈ 6×10⁻⁴ (compact).

---

## Case-by-case measured outcomes

### Case A1 — HFR-K3/1 sphere, 7.7 % FIMA, 1600 °C / 500 h
- **Failed particles (heating): 0** (manuf. 0, heating 0). Kr release stayed below the
  one-particle inventory, so no failure was inferred. (1674 Table 8.2 line 18623; prose
  1674 lines 24848–24851; 2090 Table 19 line 3026.)
- **Fractional release:** Kr-85 = **1.8×10⁻⁶**; Cs-137 = **1.1×10⁻⁴**; Sr-90 = 1.8×10⁻⁷;
  Ag-110m = 2.7×10⁻². (1674 Table 8.2 line 18623.) Cs-134 = 1.3×10⁻⁴ (2090 Table 19 line 3026).
- **Onset:** none (no failures). (1674 lines 24848–24851.)

### Case A2 — HFR-K3/3 sphere, 10.2 % FIMA, 1800 °C / 100 h
- **Failed particles (heating): ~12** per Table 8.2 (manuf. 0, heating ~12). (1674 Table 8.2
  line 18657; 2090 Table 19 line 3074.)
- **DISCREPANCY:** the postcalculation prose instead assumes **10** failures during the 1800 °C
  heating, at **50, 55, 65, 70, 75, 80, 85, 89, 92, 97 h** into the 1800 °C exposure. Kr release
  exceeded the one-particle level (6×10⁻⁵) after ~50 h at 1800 °C. (1674 lines 24984–24986.)
  → **Record both: "~12" (Table 8.2) vs "10" (prose onset list).**
- **Fractional release:** Kr-85 = **6.5×10⁻⁴**; Cs-137 = **5.9×10⁻²**; Sr-90 = 1.5×10⁻³;
  Ag-110m = 6.7×10⁻¹. (1674 Table 8.2 line 18657.) Cs-134 = 6.4×10⁻² (2090 Table 19 line 3074).

### Case B — HFR-K6/3 sphere, 10.9 % FIMA, staged 1600/1700/1800 °C + final 1800 °C/300 h
- **Failed particles (heating): 5**, ALL in the **final (4th) 1800 °C phase**, at
  **119, 174, 214, 258, 288 h** into that final 300 h phase. Kr stayed below 10⁻⁵ through the
  1600 °C and 1700 °C phases and only rose with the 1800 °C phases. (1674 lines 25131–25134.)
- **Fractional release (Cs-137):** Cs stayed near the 10⁻⁶ level during the 1600 °C and 1700 °C
  phases, then rose in the 1800 °C phase and **eventually reaches ~4 % (≈4×10⁻²)** Cs-137.
  (1674 lines 25135–25137.) Kr-85 whole-test end state is figure-only (Figs 10.24–10.26);
  not in a text table.

### Case C1 — HFR-P4/3-7 compact, 13.9 % FIMA, 1600 °C / 304 h
- **Failed particles (heating): 3**, at **49 h, 115 h, 200 h** into the 1600 °C hold.
  (1674 lines 24500–24502.)
- **Fractional release:** Kr-85 = **9.9×10⁻⁴**; Cs-137 = **3.9×10⁻³**; Sr-90 = 2.4×10⁻⁴;
  Cs-134 = 3.5×10⁻³. (2090 Table 21, row "HFR-P4/3/7", lines 3636–3638.)

### Case C2 — HFR-P4/1-12 compact, 11.1 % FIMA, 1600 °C / 304 h
- **Failed particles (heating): 0.** (1674 line 24366 context; the compact one-particle level is
  6×10⁻⁴ and release stayed below it.)
- **Fractional release:** Kr-85 = **5.4×10⁻⁷**; Cs-137 = **2.6×10⁻⁴**; Sr-90 = 6.0×10⁻⁶;
  Cs-134 = 3.0×10⁻⁴. (2090 Table 21, row "HFR-P4/1/12", lines 3626–3628.)

---

## Companion rows from [2090] Table 21 (HFR-P4 / SL-P1 compacts, for context; lines 3617–3643)

| Compact | Burnup %FIMA | Fast fluence (10²⁵) | Irrad T (°C) | Heat T (°C) | Dur (h) | Kr-85 | Sr-90 | Cs-134 | Cs-137 |
|---|---|---|---|---|---|---|---|---|---|
| SL-P1/6 | 10.7 | 6.7 | 790–800 | 1600 | 304 | 7.3×10⁻⁷ | 4.3×10⁻⁵ | 7.5×10⁻⁴ | 3.9×10⁻⁴ |
| HFR-P4/1/12 | 11.1 | 5.5 | 900–940 | 1600 | 304 | 5.4×10⁻⁷ | 6.0×10⁻⁶ | 3.0×10⁻⁴ | 2.6×10⁻⁴ |
| HFR-P4/1/8 | 13.8 | 7.2 | 900–940 | 1600 | 304 | 5.4×10⁻⁵ | 1.5×10⁻⁴ | 1.5×10⁻³ | 2.0×10⁻³ |
| HFR-P4/2/8 | 13.8 | 7.2 | 900–945 | 1600 | 304 | 8.1×10⁻⁵ | 1.1×10⁻⁴ | 1.5×10⁻³ | 1.4×10⁻³ |
| HFR-P4/3/7 | 13.9 | 7.5 | 1050–1075 | 1600 | 304 | 9.9×10⁻⁴ | 2.4×10⁻⁴ | 3.5×10⁻³ | 3.9×10⁻³ |
| SL-P1/10 | 10.3 | 6.0 | 790–800 | 1700 | 304 | 9.1×10⁻⁵ | 2.1×10⁻² | 9.3×10⁻² | 1.0×10⁻¹ |
| SL-P1/9 | 10.7 | 6.3 | 790–800 | 1700 | 304 | 3.7×10⁻⁵ | 5.8×10⁻² | 1.3×10⁻¹ | 9.8×10⁻² |
| HFR-P4/3/12 | 9.9/12.0 | 5.5 | 1050–1075 | 1800 | 279 | 1.0×10⁻³ | not meas. | 5.2×10⁻¹ | 5.2×10⁻¹ |

---

## Broader Table 8.2 context (1674 lines 18614–18659; reproduced in 2090 Table 19, lines 3014–3078)

Additional heated spheres, useful for calibrating the temperature/burnup trend and for possible
extra scoring rows:

| Element | Burnup %FIMA | Fluence (10²⁵, E>0.1) | Temp (°C) | Time (h) | Failed (heating) | Kr-85 | Cs-137 |
|---|---|---|---|---|---|---|---|
| AVR 71/22 | 3.5 | 0.9 | 1600 | 500 | 0 | 4.0×10⁻⁷ | 2.0×10⁻⁵ |
| AVR 82/9 | 8.9 | 2.5 | 1600 | 500 | 0 | 5.3×10⁻⁷ | 7.6×10⁻⁴ |
| AVR 90/20 | 9.8 | 2.9 | 1620 | ~10 | 3 (+2 manuf.) | 2.4×10⁻⁴ | 6.5×10⁻⁶ |
| AVR 91/31 | 9.0 | 2.6 | 1700 | ~10 | 18 (+2 manuf.) | 1.2×10⁻³ | 2.4×10⁻³ |
| AVR 70/33 | 1.6 | 0.4 | 1800 | 175 | 28 | 1.7×10⁻³ | 2.2×10⁻² |
| AVR 74/10 | 5.5 | 1.4 | 1800 | 90 | 30 | 1.8×10⁻³ | 7.9×10⁻² |
| AVR 76/18 | 7.1 | 1.9 | 1800 | 200 | ~3 | 1.2×10⁻⁴ | 4.5×10⁻² |
| AVR 88/41 | 7.6 | 2.0 | 1800 | 24 | 0 | 2.4×10⁻⁷ | 1.5×10⁻⁴ |

Trend: at 1600 °C essentially no heating-induced failures up to ~9 % FIMA/500 h; failures set in
and multiply at 1800 °C; Cs-137 release climbs by orders of magnitude between 1600 °C and 1800 °C.

---

## Possible extra case — NPR-1 A5 (normal-operation / high-burnup outlier)

- HEU TRISO, ~200 µm kernel, irradiated ~170 days to **79 % FIMA**, 3.8×10²⁵ n/m² at ~950 °C.
- **Measured SiC failure fraction: 0.6 % (95 % CI 0–3 %).** A STAPLE calculation predicted 2.4 %.
  (1674 lines 14345–14349; input params in Table 9.12, 1674 lines 22285–22320.)
- Included here as an optional stress case for the very-high-burnup regime; note the enrichment,
  kernel size and PyC/SiC strength inputs differ from the LEU cases (SiC 572 MPa, m 6.0;
  PyC 218 MPa, m 9.5 — Table 9.14 case 12).

---

## Participant-code result locations and known code-spread (DILIGENCE §3)

For qualitative comparison only — these are *code predictions*, not measurements, and the
original codes largely did **not** predict particle failures (failures were imposed as boundary
conditions in the postcalculations, so there is circularity in the failure-count comparison).

- **Analytical normal-op (SiC stress) results:** Tables 9.9–9.11 at 1674 lines 21285–21296,
  21360–21371, 21419–21432 (e.g. SiC 125.1–125.9 MPa case 1; 104.2–106.7 MPa case 3).
  Case 9–13 spread figures: 1674 Figs 9.5–9.22, lines 21455–22974 (predicted failure fractions
  span ~1×10⁻¹⁴ … 1×10⁻²).
- **Accident release code tables:** Table 10.6 (1674 23807–23818), 10.7 (23885–23896),
  10.8 (23929–23947), 10.9 (24079–24098), 10.10 (24170–24179); release curves Figs 10.8–10.29
  (1674 lines 24374–25466).
- **Codes:** ATLAS, PANAMA/FRESCO-II, COPA, GETTER, PARFUME/PISA, SORS, STRESS3.
- **Known code-spread context for scoring tolerance:**
  - **Cs-137 inter-code band is typically ×2 to ×10** — treat a factor-of-a-few miss on Cs as
    within the state of the art.
  - **ALL codes overpredict Sr-90 by > 100×** (1674 line 24494) — **Sr is excluded from scoring.**
  - Accident release predictions commonly spread more than one order of magnitude between codes.
