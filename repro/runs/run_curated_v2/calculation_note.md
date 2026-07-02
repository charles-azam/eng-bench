# Calculation Note — Passive Reactor Cavity Cooling System (NSTF RCCS)

**Prepared for:** RCCS natural-circulation performance prediction
**Facility:** Argonne Natural-convection Shutdown-heat-removal Test Facility (NSTF), a ½-axial-scale
air-cooled RCCS model of the GA-MHTGR.
**Author:** engineering analysis, 2026-07-02
**Basis:** first principles + the geometry, materials, and controlled conditions in `inputs/`.

> **Provenance statement.** Every number in this note was derived from physics and the supplied
> input pack (`inputs/01–04`). **No facility test reports, published NSTF results, or pre-made model
> of this facility were consulted.** The only facility numbers used as *inputs* are the geometry,
> materials, emissivities, ambient envelope, the prescribed heater/decay-power curve, and the
> explicitly-allowed *design-duty scaling targets* of Table 5 (which are design intents, not
> measurements). Where I compare against those targets it is a cross-check of my own prediction,
> not a source for it. Empirical correlations are cited inline.

---

## 1. Method

The RCCS is a closed buoyancy loop:

```
outdoor air → 24" downcomer → inlet plenum → 12 riser ducts (heated) → outlet plenum
            → dual 24" chimney (≈19.6 m rise) → discharge
```

Heat path across the cavity:

```
radiant heaters → 1" steel "heated wall" (mock vessel, ε≈0.78)
   → 0.71 m AIR CAVITY, crossed by (a) thermal radiation + (b) enclosed natural convection
   → riser front wall → conduction through 4.8 mm steel → forced/mixed convection to riser air
```

Two coupled balances are solved numerically (`rccs_model.py`):

1. **Loop momentum balance** — buoyancy head = sum of friction + form losses → **mass flow ṁ**.
   Buoyancy is computed from the actual density profile around the loop (cold downcomer + cold inlet
   run, linearly-heated riser, hot chimney with a small insulated-stack cooldown) using ideal-gas
   ρ(T). Losses use Darcy friction (Blasius `f=0.316 Re⁻⁰·²⁵` turbulent, `64/Re` laminar) on each
   segment, with the chimney's tabulated *equivalent length* (826″, which already folds in its
   elbows/bellows/tees/valve) plus form-loss coefficients for entrances, exits, plenum
   expansion/contraction, and a lumped minor-loss bucket for the five butterfly "loafer" valves and
   instrument probes.
2. **Energy + heat-transfer network** — `Q = ṁ cₚ ΔT` sets the air rise; internal riser convection
   (Dittus–Boelter, `Nu=0.023 Re⁰·⁸ Pr⁰·⁴`, Incropera) sets the riser-wall temperature; a
   two-surface radiation network with re-radiating (insulated) side walls (Incropera Eq. 13.30)
   plus tall-cavity natural convection (`Nu=0.046 Ra^{1/3}`, MacGregor–Emery / Incropera) sets the
   heated-wall (vessel) temperature and the radiation/convection split.

Air properties are ideal-gas density and power-law fits for μ, k anchored to the supplied 0 °C/100 °C
reference data (`inputs/02`, Table 47). The transient (accident) case adds a lumped steel thermal
mass and integrates the vessel temperature over the prescribed decay-power curve
(`transient_and_sensitivity.py`).

**Key modelling assumptions** (most-uncertain flagged in §8):
- Air drawn at outdoor ambient temperature; negligible pre-heat in the uninsulated downcomer.
- Three non-heated cavity walls are adiabatic → radiatively **re-radiating** surfaces.
- Riser front and heated plate both oxidised steel, ε≈0.79–0.80; plate–riser view factor F₁₂≈0.5
  (remainder to re-radiating walls).
- Chimney insulated → hot column cooled ≈12 K over the rise.
- Lumped minor-loss coefficient K≈4 (referenced to chimney velocity head) for un-itemised fittings.
- Accident: programmed electric power (poly×90, peak ≈87.7 kWe) delivers **η≈0.64 → ≈56 kWt** to
  the section after heater/back-insulation losses (per the inputs' "82 kWe → ≈56 kWt" note).

---

## 2. Geometry used (derived from `inputs/01`)

| Quantity | Value |
|---|---|
| Riser internal flow area (1 duct 9.624″×1.624″) | 100.8 cm² |
| Riser total internal flow area (×12) | 0.1210 m² |
| Riser hydraulic diameter | 70.6 mm |
| Riser heated length | 6.82 m |
| Riser total inner wetted (heated) area | 46.8 m² |
| Downcomer / each chimney area (24″) | 0.292 m² |
| Dual-chimney flow area | 0.584 m² (matches Table 10) |
| Heated-plate area | 10.18 m² |
| Cavity gap / height / width | 0.707 / 6.71 / 1.32 m |
| Loop inlet→outlet elevation Δz | 20.47 m (Table 56) |

---

## 3. Results — steady operating cases

| Quantity | **Peak duty (winter, 0 °C)** | **Normal duty (winter, 0 °C)** | **Peak duty (summer, 25 °C)** |
|---|---|---|---|
| Net section power Q | 56.0 kWt | 26.2 kWt | 56.0 kWt |
| **(1) Mass flow ṁ** | **0.58 kg/s** | **0.46 kg/s** | **0.52 kg/s** |
| **(2) Riser air ΔT** | **96 °C** (T_out ≈ 96 °C) | **57 °C** (T_out ≈ 57 °C) | **106 °C** (T_out ≈ 131 °C) |
| **(3a) Riser-wall T** | **≈110 °C** | ≈64 °C | ≈143 °C |
| **(3b) Heated-wall / vessel T** | **≈386 °C** | ≈266 °C | ≈396 °C |
| **(4) Radiation fraction** | **87 %** (49 kW rad / 7 kW conv) | 80 % (21 / 5.2 kW) | 89 % (50 / 6.1 kW) |
| Riser Re / velocity | 17 200 / 4.3 m/s | 14 400 / 3.2 m/s | 14 600 / 4.3 m/s |
| Buoyancy head | 49 Pa | 30 Pa | 45 Pa |

**Cross-check vs allowed design-duty targets (Table 5).** Design intent (peak): ṁ=0.456 kg/s,
ΔT=121 °C; (normal): ṁ=0.396 kg/s, ΔT=67 °C. My momentum balance predicts somewhat **more flow and
less ΔT** than the design intent. This is expected and consistent: the Table-5 ΔT is a *scaling
requirement* (ΔT_R=1, forcing full-scale ΔT), from which the target flow is simply back-computed as
Q/(cₚΔT) — it is not an independent loop solution. My value is the flow the buoyancy/loss balance
actually delivers. Both satisfy `Q=ṁcₚΔT≈56 kW`. The ~25 % gap is within the natural-circulation
prediction band and is governed by the loop loss coefficient (§8).

### Interpretation
- **Radiation dominates** heat transport across the cavity (≈80–90 %). Air is nearly transparent and
  cavity natural convection is weak over a 0.71 m gap, so the T⁴ radiative link carries most of the
  load — the defining feature of an air RCCS. The radiation fraction *rises* with power/temperature
  (T⁴) and with warmer ambient.
- The **riser wall runs only ~10–50 °C above the bulk air** — the internal convective resistance is
  modest; the large temperature step is across the cavity, so the **vessel wall sits several hundred
  °C above the risers**, set almost entirely by the radiative balance.

---

## 4. Accident (decay-heat) transient

Programmed **electric** power (poly×90) peaks at **87.7 kWe at t≈71.5 h**; after heater/back losses
(η≈0.64) the **section thermal load peaks at ≈56 kWt** — matching the 1.5 MWt-scaled DCC peak.
Steel thermal mass ≈2.0 MJ/K gives a vessel-wall time constant of ~1–2 h, far shorter than the
~85 h decay evolution, so the wall responds **quasi-statically**.

| | Winter (~10 °C avg) | Summer (~25 °C avg) |
|---|---|---|
| **(5) Peak heated-wall (vessel) T** | **≈390 °C** | **≈396 °C** |
| Time of peak | ≈73 h (lags power peak ~1.5 h) | ≈73 h |
| Peak riser-wall T | ≈115 °C | ≈130 °C |

**Does it level off or run away? → It levels off. No runaway.** Two independent reasons:
1. The decay-power source itself peaks (~72 h) then falls; the vessel temperature tracks it and
   declines afterward (see `fig_transient.png`: 390 °C at peak → 335 °C by 100 h).
2. Even at *constant* peak power the system has a **stable equilibrium**: heat removal is dominated by
   radiation, `Q_rem ∝ T_vessel⁴`, which rises steeply and monotonically with wall temperature. Any
   temperature excursion is met by a faster-than-linear increase in removal — the system is
   intrinsically self-limiting. Runaway would require removal to saturate or fall with temperature,
   which radiation never does.

**Safe-limit check.** With ΔT_R=1 the NSTF wall temperature ≈ the full-scale RPV surface temperature.
The peak ≈390–396 °C stays **below** common RPV service limits (~427 °C / 800 °F for prolonged
service; the plate/heaters themselves are rated far higher, 677 °C). **Margin ≈30–140 °C**, so the
vessel stays below a safe limit in both seasons. (This margin is the quantity most sensitive to the
emissivity/view-factor assumption — §8.)

---

## 5. Sensitivity to outdoor conditions

### Air temperature (Q = 56 kWt, steady) — `fig_ambient.png`
| Outdoor T | −18 °C | 0 °C | 20 °C | 32 °C |
|---|---|---|---|---|
| Mass flow ṁ | 0.62 | 0.58 | 0.53 | 0.51 kg/s |
| Riser ΔT | 90 °C | 96 °C | 104 °C | 108 °C |
| Vessel T | 379 °C | 386 °C | 394 °C | 399 °C |

Colder outdoor air ⇒ **denser inlet ⇒ larger buoyancy ⇒ more flow** (ṁ rises ~20 % from +32 to
−18 °C) and lower ΔT. The vessel temperature is only weakly sensitive (**≈+0.4 °C per °C of ambient**,
~20 °C total across the envelope) because the radiative link fixes the vessel-to-riser step and the
riser floats on the (ambient-referenced) air. **Warm-ambient (summer) is the limiting design case**
for peak vessel temperature.

### Wind — `fig_wind.png`
Wind over the stack exit imposes a dynamic pressure ≈ Cp·½ρV² (Cp≈0.5) that either **assists** the
draft (suction at the outlet) or **opposes** it (pressurising the inlet), depending on
direction/geometry:

| Wind speed | 0 | 4 | 8 | 10 m/s |
|---|---|---|---|---|
| ṁ if assisting | 0.58 | 0.60 | 0.67 | 0.73 kg/s |
| ṁ if opposing | 0.58 | 0.55 | 0.48 | 0.43 kg/s |

Light wind (<4 m/s) is a minor perturbation (few %). Strong wind swings flow by **±25 % at 10 m/s**
and, when opposing, can throttle the draft toward stagnation — the mechanism behind the flow
unsteadiness/reversal that wind is known to induce in tall natural-draft stacks. Because the vessel
temperature is radiation-limited, even a 25 % flow change moves the vessel wall only ~15–20 °C, but
wind is the largest source of *short-term variability* in flow and outlet temperature.

---

## 6. Confidence summary

| # | Quantity | Best estimate (peak duty) | Confidence | Dominant uncertainty |
|---|---|---|---|---|
| 1 | Mass flow ṁ | 0.58 kg/s | **Moderate**, ±25 % | loop loss coefficient (form losses) |
| 2 | Riser ΔT | 96 °C | **Moderate**, ±20 % | follows from ṁ (Q fixed) |
| 3a | Riser-wall T | 110 °C | Moderate–high, ±15 °C | internal Nu correlation |
| 3b | Vessel wall T | 386 °C | **Moderate**, ±40 °C | emissivity + view factor |
| 4 | Radiation fraction | 87 % | **High** (qualitatively robust), ±5 pts | cavity-convection Nu |
| 5 | Accident peak / runaway | 390–396 °C; **no runaway** | High for *no-runaway*; moderate for absolute peak (±40 °C) | same as 3b; η_section |
| 6 | Ambient/wind trends | as tabulated | High for *direction & slope* | wind pressure coefficient Cp |

---

## 7. Most-uncertain assumptions (ranked)

1. **Cavity radiation parameters (emissivity + view factor).** The vessel temperature scales as
   `Q ∝ ε_eff σ(T_v⁴−T_r⁴)`; a shift from ε_eff≈0.7 to 0.85, or F₁₂ from 0.5 to 0.7, moves the vessel
   wall by ±30–50 °C — the single biggest lever on the safe-margin number. Confidence is moderate
   because the plate emissivity (0.78–0.79) is a given input, but the riser emissivity and the
   enclosure view factors are engineering estimates.
2. **Loop loss coefficient.** Sets ṁ (hence ΔT). The un-itemised minor losses (five loafer valves,
   plenum expansions, flow conditioner, probes) are lumped as K≈4; halving/doubling it changes ṁ by
   ~±15 %. This is why my ṁ sits above the scaling-target ṁ.
3. **Section efficiency η for the accident case.** I used η≈0.64 so the section peaks at 56 kWt; if the
   true heater/back loss differs, the peak load — and thus peak vessel T — shifts roughly °C-for-°C
   with the implied ΔT.
4. **Cavity natural-convection Nu.** Affects the (small) convective fraction and the 10–15 % of load
   not carried by radiation; low leverage on the headline temperatures.

---

## 8. Files

| File | Contents |
|---|---|
| `rccs_model.py` | Air properties, geometry, loop momentum balance, heat-transfer network, steady cases |
| `transient_and_sensitivity.py` | Decay-curve evaluation, lumped-capacitance accident transient, ambient & wind sweeps |
| `make_figures.py` | Generates the figures + `results_summary.json` |
| `results_summary.json` | Machine-readable headline results |
| `fig_transient.png` | Accident power/removal and vessel-temperature history (level-off) |
| `fig_ambient.png` | Flow / ΔT / vessel-T vs outdoor temperature |
| `fig_wind.png` | Flow vs wind speed (assisting vs opposing) |

**Correlations cited:** Blasius friction factor; Dittus–Boelter internal turbulent convection;
MacGregor–Emery tall-cavity natural convection; two-surface + re-radiating-wall radiation network
(all standard textbook forms, e.g. Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer*).
