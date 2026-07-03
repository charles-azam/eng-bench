# TRISO Benchmark Diligence Map (Opus scout, 2026-07-02)
Source files: triso/sources/TECDOC-1674_full.txt (31,190 lines, 711 pp) and TECDOC-2090_full.txt
(12,091 lines). All line refs → 1674 unless [2090].

## Benchmark structure
- Ch.9 Normal-operation benchmark (SiC stress & failure fraction), lines 19677–22999.
  Analytical cases 1–8 (no measured data; closed-form answers exist): defs 20888–20940;
  Table 9.3 (cases 1–3) 20951–20988; Table 9.4 (4a–4d creep/swelling) 20994–21040; Table 9.5
  (cases 5–8 full TRISO) 21046–21079. Irradiation postcalcs 9–13: prose 22249–22273; Table 9.12
  (HRB-22, HFR-K3/B/2, HFR-P4/3, NPR-1 A5) 22285–22320; Table 9.13 (HFR-EU1) 22326–22348.
- Ch.10 Accident benchmark (Kr/Cs/Sr/Ag release), lines 23002–25571. Sensitivity cases 1a–5b
  Table 10.5: 23721–23766. Postcalc heating tests 6–9 Table 10.11: 24285–24346. Prediction
  cases 10–11 Table 10.12: 24281–24298. Fuel/particle characteristics Table 10.1: 23606–23635,
  Table 10.2: 23641–23668.

## Measured data (THE ANSWERS — hold out)
- **Table 8.2 (lines 18614–18659)**: ~25 KüFA heating tests, text-extractable: failure counts
  (of 16,400/sphere) + Kr-85/Cs-137/Sr-90/Ag-110m release. Key rows:
  HFR-K3/1 7.7% FIMA 1600°C/500h → 0 fail, Kr 1.8e-6, Cs 1.1e-4, Ag 2.7e-2.
  HFR-K3/3 10.2% FIMA 1800°C/100h → ~12 fail, Kr 6.5e-4, Cs 5.9e-2, Sr 1.5e-3, Ag 6.7e-1.
  AVR 91/31 1700°C → 2+18 fail, Kr 1.2e-3. AVR 70/33 1800°C/175h → 28 fail, Kr 1.7e-3.
  AVR 74/10 1800°C/90h → 30 fail, Kr 1.8e-3. AVR 90/20 1620°C → 2+3, Kr 2.4e-4.
  (Reproduced in [2090] Table 19, lines 3014–3078, adds Cs-134.)
- **[2090] Table 21 (lines 3617–3643)**: HFR-P4/SL-P1 compacts (1,600 particles), 1600–1800°C:
  HFR-P4/3/7 13.9% FIMA 1600°C → Kr 9.9e-4; HFR-P4/3/12 1800°C/279h → Kr 1.0e-3, Cs 5.2e-1;
  HFR-P4/1/12 11.1% FIMA 1600°C → 0 fail, Kr 5.4e-7.
- **Failure-onset times in prose**: HFR-P4/3-7: 3 failures at 49/115/200 h @1600°C (24500–24502).
  HFR-K3/3: 10 failures at 50,55,65,70,75,80,85,89,92,97 h @1800°C (24984–24986); one-particle
  Kr level 6e-5. HFR-K6/3: 5 failures at 119/174/214/258/288 h of final 1800°C phase
  (25131–25134). HFR-P4/1-12: 0 fail (24366). HFR-K3/1: 0 fail (24848–24851).
- Normal-op measured: only NPR-1 A5 quoted: 0.6% (95% CI 0–3%) at 79% FIMA (14347–14348);
  others ≈0 and figure-only. Table 5.5 (9977–10016): AVR GLE-3 elements Kr < 1e-6 at
  1250–1500°C (≤7.6e-6 fail fraction @95% CL).
- Note discrepancy: K3/3 "~12" (Table 8.2) vs "10" (prose onset list) — record both in refs.

## Code-comparison results (also hold out)
Tables 9.9–9.11: 21285–21296, 21360–21371, 21419–21432 (analytical: SiC 125.1–125.9 MPa case 1;
104.2–106.7 case 3). Figs 9.5–9.22: 21455–22974 (cases 9–13 spread HUGE: 1e-14…1e-2).
Accident: Table 10.6: 23807–23818; 10.7: 23885–23896; 10.8: 23929–23947 (>1 order spread);
10.9: 24079–24098; 10.10: 24170–24179; curves Figs 10.8–10.29: 24374–25466. Codes: ATLAS,
PANAMA/FRESCO-II, COPA, GETTER, PARFUME/PISA, SORS, STRESS3. Known: Sr overpredicted >100× by
ALL codes (24494) — exclude Sr from scoring. Inter-code Cs band typically ×2–×10.

## Material properties (INPUTS — enables fully-offline runs)
Table 9.8 (21243–21263): PyC swelling polynomials A0–A5 + creep coeff 2.71e-4 /(MPa·1e25 n/m²);
Eqs 9.22–9.23 (21199–21230). Table 9.6 (21100–21120): PyC E=3.96e4 MPa ν=.33 ν_creep=.5; SiC
E=3.70e5 ν=.13. Table 9.7 (21128–21160): internal pressures for cases 1–8. Table 9.14
(22363–22379): SiC strength 873 MPa (572 NPR), Weibull m=8.02 (6.0 NPR); PyC 200 MPa m=5.
Table 7.1 (13572–13583): kernel diffusion D0'/Q — Cs 0.90/209, Sr 3.5e4/488, Ag 0.107/165,
Xe-Kr 2.1e-5/126 (kJ/mol). Eq 10.9 (24002–24016): Cs-in-SiC D. R/B Booth model Eqs 7.5–7.6
(13595–13609); heating release Eqs 10.7–10.8 (23780–23802). Buffer: stiffness≈0 by convention
(21195–21197). Gap: matrix/graphite sorption coefficients reference TECDOC-978.

## Verdict
Targets: (A) HFR-K3/1 vs K3/3 sister spheres — the 1600/1800 °C cliff (0 vs ~10-12 failures,
Kr 1.8e-6 vs 6.5e-4) + onset times; (B) HFR-K6/3 staged heating (failures only in final 1800°C
phase); (C) HFR-P4 compact burnup pair (3 vs 0 failures at same T). End-state numbers
text-scoreable; transient curves are figures-only. Risks: severe in-document answer leakage
(postcalc prose EMBEDS failure counts as BCs — strip surgically); the original codes did NOT
predict failures (circularity); avoid EU1bis (spec≠reality) and normal-op cases 9–13 except
NPR-1; exclude Sr.
