# Calculation Note — Passive Reactor Cavity Cooling System (RCCS)

**Subject:** First-principles prediction of the natural-circulation air cooling performance of a
½-axial-scale, air-cooled RCCS test facility (12-riser, 19.03° sector).
**Author:** Engineering analysis (Tribe)  ·  **Date:** 2026-07-01
**Scope:** Cases 1–3 of `inputs/04_boundary_conditions_and_test_cases.md`.

> **Provenance statement.** Every number in this note was derived from physics and the sanctioned
> inputs in `inputs/` only. No published test data, report, or pre-made model of this facility was
> consulted. All empirical correlations are general textbook/standard correlations, cited at point
> of use. The digitized decay-heat polynomial in `inputs/04` was found numerically unstable
> (wrong peak time, negative past ~110 h — its C10 term is missing), so the *sanctioned normalized
> shape* (26→56 kW, peak at 84.85 h) was used instead, as that file explicitly permits.

---

## 1. Method overview

The RCCS is a single-phase, open, natural-circulation air loop. The four coupled physics blocks
and how they close:

1. **Buoyancy-driven flow.** A segmented hydrostatic loop integral gives the stack driving head
   from the density difference between the tall external cold-air column and the hot internal
   (riser + chimney) column. This is balanced against friction + form losses to solve the loop
   **mass flow** `ṁ`.
2. **Energy balance.** `Q_air = ṁ·c_p·(T_out − T_in)` sets the **riser air temperature rise**.
3. **Gas-side convection.** Gnielinski/Petukhov turbulent-duct correlation gives the internal
   coefficient `h_i` and hence the **riser wall temperature**.
4. **Cavity transfer.** A gray-surface **radiation** network (plate ↔ risers, re-radiating
   adiabatic side walls) plus enclosed-cavity **natural convection** sets the **plate temperature**
   and the **radiation/convection split**.

Blocks 1–2 are coupled (flow depends on riser densities, which depend on ΔT) and solved by
fixed-point iteration; blocks 3–4 then follow. Implemented in `rccs_model.py` (steady),
`accident_transient.py` (Case 2), `weather_sweep.py` (Case 3), `airprops.py` (air properties).

**Key geometry used** (from `inputs/01`): 12 risers, internal 9.624×1.624 in →
`A_riser=0.0101 m²`, `D_h=0.0706 m`; heated length 6.91 m; heated-plate area **10.18 m²**
(as-built); plate–riser gap 0.707 m; chimney dual 24-in, `A=0.58 m²`, discharge 19.6 m.
**Properties** (`inputs/02`): plate ε=0.785 (measured); riser ε **assumed 0.80** (oxidized
structural steel — *not reported*; standard value, see §7); air properties from ideal-gas +
Sutherland (viscosity/conductivity) + standard `c_p` fit, evaluated at the mean gas temperature.

**Heat input assumption (most consequential — see §7).** Case 1 states 82 kW_e electric, "which
corresponds to the scaled 1.5 MWt peak duty" = **56.07 kW** to be removed. We take the heat
reaching the air as **Q_air = 56.07 kW** (the scaled duty; the ~26 kW electric–duty gap is
parasitic loss through the heater backing/structure). An independent conduction estimate of
parasitic loss gives only ~10–14 kW, which would imply Q_air ≈ 68–72 kW; we therefore also report
a **Q_air = 70 kW** sensitivity case. This ±25% span on delivered heat is the single largest
uncertainty and brackets all temperature predictions.

---

## 2. Case 1 — Baseline steady state (Q_air = 56.07 kW, T_in = 20 °C, outdoor +2 °C)

| Quantity | Predicted value | Where (per `inputs/03`) | Confidence |
|---|---|---|---|
| **Loop air mass flow** | **0.55 kg/s ≈ 33 kg/min** | inlet downcomer, whole loop | Medium (±25%) |
| **Riser air ΔT** | **≈ 100 °C** (20 → 122 °C) | outlet−inlet gas TC | Medium (±25%) |
| **Riser wall T** (hot face) | **≈ 135 °C** | Riser 7, z=3500 mm | Medium-high |
| **Heated-plate front T** | **≈ 360 °C** | plate front face | Medium |
| **Radiative fraction** | **≈ 90 %** (50.8 kW rad / 5.3 kW conv) | Riser 7 four-face flux | High (direction), Medium (exact %) |
| Riser velocity / Reynolds | 4.4 m/s / Re≈15 600 (turbulent) | — | High |
| Stack driving head | 62 Pa (risers 57, downcomer 3.7, chimney 1.8 Pa) | — | Medium |
| Internal coefficient `h_i` | 18 W/m²·K (Nu≈44) | — | High |
| Cavity convection `h` | 2.3 W/m²·K (Ra≈6×10⁸) | — | Medium |

**Reading of the result.** The loop self-organizes to ~0.55 kg/s: buoyancy head (62 Pa) is almost
entirely spent overcoming the **riser bank** (form losses at entry/exit/plena + friction dominate;
the chimney and downcomer are minor). Because the flow is modest, the air heats a lot (ΔT≈100 °C).
Heat crosses the cavity **overwhelmingly by radiation (~90 %)** — expected for a high-emissivity
(ε≈0.78) plate at ~360 °C facing cooler risers across a wide air gap; enclosed-cavity natural
convection carries only ~10 %. The plate runs ~360 °C to reject 56 kW radiatively.

**Sensitivity (Q_air = 70 kW instead of 56):** ṁ 0.57 kg/s, ΔT 122 °C, wall 158 °C, plate 400 °C,
radiative fraction 92 %. **Normal-operation duty (26.16 kW):** ṁ 0.47 kg/s, ΔT 56 °C, wall 82 °C,
plate 249 °C, radiative fraction 85 %.

---

## 3. Radiation / convection split (cavity side)

At the riser front face the co-located matte/reflective flux sensors decompose incident heat.
Our network (plate ε=0.785, riser ε=0.80, parallel-plate gray exchange
`R = 1/ε_p + 1/ε_r − 1 = 1.53` with re-radiating adiabatic side walls driving the view factor →1)
plus turbulent vertical-enclosure convection (`Nu = 0.046·Ra^{1/3}`, MacGregor & Emery / Catton)
gives:

- **Radiation ≈ 90 %**, convection ≈ 10 % at baseline; the fraction rises with power (85 % at
  26 kW → 90 % at 56 kW → 92 % at 70 kW) because radiation scales as T⁴ while cavity convection is
  nearly linear in ΔT.
- Physically the **front (line-of-sight) face** dominates the radiative gain; side/rear faces
  receive far less (re-radiation only). Our lumped model reports the *array-total* split; a per-face
  breakdown would need the tube-to-tube view factors (drawing-only pitch, §7).

**Confidence:** High that the system is radiation-dominated (~85–92 %); Medium on the exact number
(depends on assumed riser ε and the cavity-convection correlation).

---

## 4. Case 2 — Accident decay-heat transient

Imposed heat shape: normal 26.16 kW → **56.07 kW peak at t = 84.85 h** (½-scale) → slow decay.
Method: lumped-capacitance on the steel (plate + risers, **C = 1.83 MJ/K**), with the air loop
**quasi-steady** (loop time constant ~seconds–minutes ≪ 85 h). The heat *removed* is computed as a
function of plate temperature, `Q_rem(T_p)`, with the natural-circulation flow responding:

| T_plate | 300 °C | 350 °C | 400 °C | 450 °C |
|---|---|---|---|---|
| Q removed | 38 kW | 52 kW | 70 kW | 92 kW |

`dQ_rem/dT_p ≈ 0.3–0.4 kW/°C` and **rising** (the T⁴ radiation term). This is a strong negative
feedback.

**Result:**
- **Peak plate temperature ≈ 361 °C**, reached at t ≈ 85 h, coincident with the power peak.
- The plate tracks the quasi-steady equilibrium almost exactly (steel thermal lag ≈ 0.5–0.7 h ≪
  85 h), so there is negligible overshoot.
- Peak loop flow ≈ 0.55 kg/s, riser ΔT ≈ 100 °C, riser wall ≈ 135 °C at the peak instant.

**Does it level off or run away? → It LEVELS OFF. No runaway.** As `Q_in` rises, `T_p` rises, but
the removed heat climbs faster (radiation ∝ T⁴ *and* buoyant flow strengthens), so the plate
settles at whatever temperature makes `Q_rem = Q_in`. There is no positive-feedback path.

**Stays below a safe limit? → YES.** Peak plate ≈ 361 °C (≈ 400 °C in the conservative 70 kW
case) is well below the strength-loss onset of structural/mild steel (~540 °C, per ASCE/AISC
elevated-temperature curves) and far below any melting or creep-rupture regime. The mock vessel is
comfortably safe with large margin; the passive system is inherently stable.
*Confidence: High* — the qualitative conclusion (level-off, safe) is robust to every uncertain
input; only the exact peak temperature (±40 °C) depends on the Q_air assumption.

Trace saved to `transient_trace.csv`; see `fig_transient.png`.

---

## 5. Case 3 — Weather sensitivity (Q_air = 56.07 kW fixed)

Colder outdoor air makes the **external cold column denser** (it acts over the 15.6 m lever arm —
the largest term in the stack head), strengthening the draft. If the loop draws outdoor air the
inlet also gets denser, reinforcing this.

**Outdoor-temperature sweep (loop draws outdoor air, no wind):**

| Outdoor T | −18 °C | −2 °C | +2 °C | +10 °C | +24 °C |
|---|---|---|---|---|---|
| Mass flow (kg/s) | 0.58 | 0.55 | 0.54 | 0.52 | 0.49 |
| Riser ΔT (°C) | 96 | 102 | 104 | 107 | 113 |
| Riser wall (°C) | 93 | 114 | 120 | 131 | 149 |
| Plate (°C) | 348 | 355 | 356 | 360 | 366 |

**Trend:** over the full −18…+24 °C range, flow varies only **≈ ±8 %** and plate temperature
**≈ ±10 °C**. Outdoor temperature is a *weak* performance driver — the draft depends on the
density *difference*, and the hot legs dominate that difference regardless of ambient. (If the
inlet is instead building-conditioned at 20 °C, the trend is nearly identical: flow 0.60→0.49
kg/s across the range.)

**Wind sensitivity (outdoor +2 °C, wind sets a stack-exit stagnation head ~C_p·½ρV², C_p≈±0.4):**

| Wind | 0 | 3 m/s | 6 m/s | 9 m/s | 11 m/s |
|---|---|---|---|---|---|
| Dynamic head (Pa) | 0 | 6 | 23 | 52 | 78 |
| Flow, favorable (kg/s) | 0.55 | 0.56 | 0.58 | 0.62 | 0.66 |
| Flow, adverse (kg/s) | 0.55 | 0.54 | 0.51 | 0.47 | 0.43 |

**Trend:** wind is the *stronger* weather effect. At 11 m/s the exit dynamic head (~78 Pa) is
comparable to the baseline buoyant head (62 Pa), so depending on wind direction and stack-cap
aerodynamics the flow can swing **≈ ±20 %** (ΔT from ~84 to ~130 °C). A favorable (aspirating)
wind aids the chimney; an adverse crosswind/back-pressure throttles it. See `fig_weather.png`.

*Confidence:* High on the *directions*; Medium on wind magnitude (the pressure coefficient `C_p`
is geometry/direction dependent and is an assumption here). Outdoor-T effect: High.

---

## 6. Summary of reported quantities

| # | Quantity | Baseline (56 kW) | Range/notes | Confidence |
|---|---|---|---|---|
| 1 | Natural-circulation mass flow | **0.55 kg/s (33 kg/min)** | 0.49–0.66 across weather/Q | Medium |
| 2 | Riser air temperature rise | **≈ 100 °C** | 84–130 °C | Medium |
| 3 | Riser wall T (z=3500, hot face) | **≈ 135 °C** | 93–158 °C | Medium-high |
| 3 | Heated-plate (vessel) front T | **≈ 360 °C** | 348–400 °C | Medium |
| 4 | Radiative fraction of removal | **≈ 90 %** | 85–92 % | High/Medium |
| 5 | Accident peak plate T | **≈ 361 °C** | ≤ 400 °C (70 kW case) | High |
| 5 | Level-off vs runaway | **Levels off; stays safe** (≪540 °C) | robust | High |
| 6 | Weather sensitivity | flow ±8 % (T), ±20 % (wind) | see §5 | High dir. |

---

## 7. Assumptions and the most uncertain items

**Ranked by impact on the answers:**

1. **Heat actually delivered to the risers, Q_air (MOST UNCERTAIN).** Taken as the scaled duty
   56.07 kW; an independent parasitic-loss estimate suggests it could be ~70 kW. This ±25% shifts
   plate temperature by ~40 °C and flow by ~5 %. All temperatures scale with this; we report both
   bounds.
2. **Riser bank loss coefficients** (entrance 0.5, exit 1.0, plena turns ~1.0, split ~0.5;
   dominate the loop resistance). These set the flow (hence ΔT). A ±40 % change in ΣK moves flow
   ~±15 % and ΔT inversely. *Cite: Idelchik / Crane TP-410 form-loss ranges; Churchill friction
   factor.*
3. **Riser surface emissivity** = 0.80 assumed (not reported; oxidized ASTM A500 steel typically
   0.7–0.9). Affects the radiative conductance and plate temperature by ~±15 °C. *Cite: standard
   emissivity tables for oxidized steel.*
4. **Cavity-convection correlation** (`Nu=0.046 Ra^{1/3}` turbulent vertical enclosure) — sets the
   ~10 % convective share; a factor-of-2 error only moves the radiative fraction a few points.
5. **Stack elevation model & wind C_p** — the segmented loop integral is a 1-D idealization;
   wind `C_p=±0.4` is representative, not geometry-specific.

**Correlations cited:** Churchill (friction factor); Gnielinski/Petukhov (internal turbulent
convection); MacGregor & Emery / Catton (enclosed vertical-cavity convection); gray-surface
radiation network (Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer*); Sutherland's law
+ ideal-gas (air properties); ASCE/AISC elevated-temperature steel strength (safe-limit reference).

**Overall confidence.** *Directional and qualitative conclusions are high-confidence*: the loop
runs ~0.5 kg/s by buoyancy, heat crosses the cavity mostly by radiation (~90 %), and the accident
transient is self-limiting and safe. *Absolute temperatures* carry ~±40 °C and *flow* ~±25 %,
driven mainly by the delivered-heat and riser-loss assumptions above.
