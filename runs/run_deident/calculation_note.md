# Calculation Note — Passive Reactor Cavity Cooling System (RCCS)

**Facility:** ½-axial-scale, air-cooled RCCS test section (12 riser ducts, sector slice).
**Scope:** Predict, from first principles, the natural-circulation air mass flow, riser air
temperature rise, riser-duct and heated-plate wall temperatures, the radiation/convection split,
the accident-transient peak temperatures and stability, and the sensitivity to outdoor weather.

> **Provenance statement.** Every number in this note was derived from the physics and from the
> sanctioned inputs in `inputs/` only. **No published test report, measured dataset, or pre-made
> model of this facility was consulted** (nothing from `refs/`, `sources/`, or the web about this
> facility). Empirical correlations used are general engineering correlations, each cited below.

All working files are in `output/`: `props.py` (air properties), `geom.py` (geometry),
`rccs.py` (steady loop + heat-transfer solver), `transient.py` (accident case),
`weather.py` (weather sweep), `parasitic.py` (parasitic-loss estimate).

---

## 1. Model overview and governing physics

The RCCS is a single-phase natural-circulation air loop. Four physics blocks are solved
self-consistently:

**(A) Loop momentum balance (sets the mass flow).**
Buoyant driving head = sum of friction + form losses around the loop:

  Δp_drive = g·[(ρ_amb−ρ̄_riser)·H_riser + (ρ_amb−ρ_out)·H_stack]
  Δp_loss  = Σ (f·L/D + K)·½ρV²   over downcomer, plena, 12 risers, and dual chimney.

ρ̄_riser is evaluated at the mean gas temperature T_m=(T_in+T_out)/2; ρ_out at the outlet
temperature; ρ_amb at the outdoor air (the hydrostatic reference the chimney is immersed in).
H_riser=7.49 m (riser bottom→top), H_stack=12.1 m (riser top→19.6 m discharge). Friction factor
from **Haaland (1983)**; the riser hydraulic diameter D_h=0.0706 m and internal flow area
0.0101 m²/duct are derived from the 10×2×0.188-in section (matches the input's stated values).

**(B) Energy balance:** Q_air = ṁ·c_p·(T_out−T_in).

**(C) Cavity heat transfer (plate → riser front surface):** radiation + natural convection across
the 0.707-m air gap.
- *Radiation:* two-gray-surface exchange with the adiabatic (insulated) side/back walls acting as
  reradiating surfaces. Because the gap (0.71 m) ≪ plate height (6.7 m) the plate and the riser
  plane are treated as parallel surfaces of area A_plate, and — since the insulated walls are the
  only non-sink — essentially all the plate's net radiation reaches the risers:
  Q_rad = σ·A_plate·(T_p⁴−T_r⁴)/(1/ε_p + 1/ε_r − 1), with ε_p=0.78 (measured), ε_r=0.80 (assumed).
- *Convection:* vertical enclosure correlation **Catton (1978)**, Nu = 0.046·Ra^(1/3).

**(D) Riser internal convection (riser surface → flowing air):** turbulent duct flow,
**Dittus–Boelter (1930)** Nu = 0.023·Re^0.8·Pr^0.4 (heating). Re≈1.5–1.7×10⁴ (turbulent).
Steel wall conduction across the 4.8-mm wall is negligible (ΔT<0.2 K).

**Circumferential wall temperature.** Radiation lands mostly on the 2-in front face (line-of-sight
to the plate). The conductive steel tube (k≈50 W/m·K) spreads this heat around the perimeter; a
1-D circumferential conduction model (`rccs.circumferential_wall`, 240 nodes, periodic) resolves
the front/side/rear face temperatures at the reporting mid-plane. Assumed external heat split:
**front 80 %, each side 7.5 %, rear 5 %** (radiation is line-of-sight to the front).

**Air properties** (`props.py`): ideal-gas density (R=287.05); viscosity by **Sutherland's law**;
conductivity by a Sutherland-type law; c_p by a polynomial fit to standard dry-air data; Pr≈0.69–0.71;
β=1/T. Values reproduce standard tables (e.g. ρ=1.204, μ=1.81×10⁻⁵, k=0.0257 at 20 °C).

**Heat delivered to the air (key input choice).** Case 1 states 82 kWe electric input, described as
representing the scaled 1.5 MWt peak duty (= **56.07 kWt** ½-scale). A first-principles parasitic-loss
estimate (`parasitic.py`: conduction through the 6-in SuperIsol side/back walls + 2-in Duraboard
heater backing + uninsulated plenum/downcomer) gives ≈ **11 kW**, which would put heat-to-air near
72 kW; the facility's implied loss (82−56) is 26 kW. Because Case 2 states the accident thermal duty
explicitly as 26→56 kWt, I adopt **Q_air = 56 kW as the baseline** (the sanctioned scaled duty) and
report sensitivity up to 82 kW. *This is the single most uncertain assumption in the note* (see §8).

---

## 2. Case 1 — baseline steady state (Q_air = 56.07 kW, T_in = 20 °C, outdoor = +2 °C)

| Quantity | Location (per `inputs/03`) | Prediction | Confidence |
|---|---|---|---|
| **(1) System mass flow** | inlet downcomer, whole loop | **0.58 kg/s = 34.7 kg/min** | Medium |
| **(2) Riser air ΔT** | outlet−inlet TC per riser | **≈ 96 K** (20 → 116 °C) | Medium |
| **(3a) Riser wall T, hot/front face** | Riser 7, z=3500 mm, front | **≈ 185 °C** | Medium |
| (3a) Riser wall, side / rear / mean | Riser 7, z=3500 mm | 121 / 98 / 124 °C | Low–Med |
| **(3b) Heated-plate front T** | plate front face | **≈ 359 °C** | Medium–High |
| **(4) Radiative fraction of heat removal** | Riser 7 four-face flux sensors | **≈ 90 %** (Q_rad 50.6 kW / Q_conv 5.5 kW) | High |

Supporting values: driving head Δp ≈ 63 Pa; riser velocity 4.6 m/s, Re ≈ 1.66×10⁴ (turbulent);
internal h ≈ 20 W/m²·K; cavity natural-convection h ≈ 2.3 W/m²·K (Ra ≈ 6.6×10⁸).
Loss breakdown: riser friction ≈ 51 %, riser entrance+exit form losses ≈ 40 %, chimney+downcomer
≈ 9 % — i.e. the 12 risers dominate the loop resistance.

**Normal-operation duty (26.16 kWt), same ambient:** ṁ ≈ 0.50 kg/s (30 kg/min), ΔT ≈ 52 K,
plate ≈ 248 °C, riser front ≈ 106 °C, radiative fraction ≈ 84 %. (Radiative fraction rises with
power because radiation scales as T⁴ while cavity convection is roughly linear in ΔT.)

**Reading the numbers.** The flow is a weak (roughly Q^0.1) function of power: buoyancy and loss
both scale with the flow, so doubling the heat mostly raises ΔT and temperatures rather than flow.
Temperatures are set overwhelmingly by radiation — the plate sits ~230 K above the riser surface to
drive 50 kW of radiant flux across the cavity.

---

## 3. (4) Radiation vs convection split

Across the cavity the plate loses **≈ 90 %** of its heat by radiation and **≈ 10 %** by natural
convection at the 56-kW baseline (84 % / 16 % at the 26-kW normal load). This is the expected
regime for a high-temperature RCCS: with plate temperatures of 250–360 °C and a wide radiating gap,
the σT⁴ term dwarfs the low-velocity buoyant gas convection (cavity h ≈ 2 W/m²·K).

By riser face (from the circumferential model + line-of-sight radiation assumption): the **front
(hot) face carries ≈ 80 %** of the absorbed heat, the two wide side faces ≈ 15 % combined, and the
rear face ≈ 5 % — which is what the co-located matte/reflective flux sensors on Riser 7's four faces
are built to resolve. **Confidence: High for the ~90 % overall radiative fraction** (robust to the
convection correlation — even a 2× error in cavity-h moves it only a few points); **Medium for the
per-face breakdown** (depends on the assumed 80/15/5 line-of-sight split).

---

## 4. (5) Case 2 — accident decay-heat transient

**Method.** The scaled decay curve rises 26 → 56 kWt over ~85 h (peak at t = 84.85 h), then declines
(`transient.py`). The plate/near-surface steel thermal capacitance is C ≈ 1.27 MJ/K, giving a
thermal time constant τ = C/(dQ_removed/dT_p) ≈ 1.3 MJ/K ÷ 0.34 kW/K ≈ **60 min** — far shorter than
the tens-of-hours power ramp. The air loop responds in seconds. The transient is therefore
**quasi-static**: temperatures track the instantaneous steady state. I integrate the lumped plate
energy balance C·dT_p/dt = P_in(t) − Q_removed(T_p) using the steady solver's T_p(Q) map.

**Result.**

| Quantity | Prediction | Confidence |
|---|---|---|
| **Peak heated-plate temperature** | **≈ 359 °C at t ≈ 85 h** (coincides with peak power) | Medium–High |
| Peak riser front-wall temperature | ≈ 185 °C | Medium |
| Peak system mass flow | ≈ 0.58 kg/s | Medium |
| Behaviour | **Levels off, then declines with the decay curve — NO runaway** | High |
| Vessel below safe limit? | **Yes** — 359 °C ≪ ~500–550 °C steel limit; margin ≳ 150 K | High |

**Why it cannot run away (robust conclusion).** Heat removal is radiation-dominated (∝ T_p⁴), so
dQ_removed/dT_p is strongly positive at every power level (203 → 392 W/K over 26–70 kW, all > 0).
Any temperature excursion increases removal faster than it increases storage, so the plate has a
single **stable** fixed point at each power. The transient computed by integration peaks at 359 °C —
identical to the quasi-steady value at 56 kW — confirming the plate follows the power quasi-statically
and declines as decay heat falls. Even at the (upper-bound) 82-kW heat-to-air the plate is ~427 °C,
still below the steel limit. **The passive system is self-limiting.**

---

## 5. (6) Case 3 — weather sensitivity (Q_air = 56 kW)

Outdoor air sets both the buoyancy reference density and (facility draws outdoor air) the riser inlet
temperature, so T_in = T_outdoor in this sweep. Wind is modelled as a draft perturbation at the
discharge, Δp_wind = C_p·½ρV² with C_p ≈ +0.3 (favourable cap/stack effect).

**Outdoor temperature, −18 → +24 °C (no wind):**

| T_outdoor | ṁ (kg/s) | ΔT (K) | Plate T (°C) | Riser front (°C) | rad. frac |
|---|---|---|---|---|---|
| −18 | 0.602 | 92 | 347 | 145 | 88 % |
| 0 | 0.558 | 99 | 354 | 170 | 89 % |
| +2 | 0.554 | 100 | 355 | 173 | 90 % |
| +24 | 0.509 | 109 | 365 | 203 | 91 % |

- **Colder air → stronger natural circulation.** Density difference grows, so flow rises: ṁ increases
  **≈ +15 %** from +24 °C to −18 °C, ΔT drops, and the plate runs ~18 K cooler.
- The plate temperature is only weakly sensitive to weather (radiation-clamped): the whole −18…+24 °C
  span moves it by <20 K. Worst case for temperatures is **hot, still air**.

**Wind, 0 → 11 m/s (favourable, at +2 °C):**

| V_wind | Δp_wind (Pa) | ṁ (kg/s) | Plate T (°C) |
|---|---|---|---|
| 0 | 0 | 0.554 | 355 |
| 6 | 6.9 | 0.582 | 354 |
| 11 | 23 | 0.648 | 351 |

- Favourable wind augments the ~60-Pa buoyant draft and raises flow **≈ +17 %** at 11 m/s, cooling the
  plate a few K. **Sign caveat:** depending on direction/geometry wind can instead *oppose* the draft
  (C_p < 0) and reduce flow by a similar magnitude; the facility's dual N/S chimney ports make a
  fully adverse case unlikely but the magnitude (±15–20 % at high wind) is the honest bound.

**Confidence:** *Directional trends — High* (cold/windy strengthens circulation and lowers
temperatures; hot/still is the limiting case). *Magnitudes — Medium* (wind C_p and the inlet-air
assumption are approximate).

---

## 6. Confidence summary and the most uncertain assumption

| Result | Confidence | Governing uncertainty |
|---|---|---|
| Radiative fraction ≈ 90 % | **High** | robust to convection-model error |
| Accident is self-limiting (no runaway) | **High** | σT⁴ removal → guaranteed stable fixed point |
| Plate front temperature (~360 °C) | **Med–High** | radiation-dominated → insensitive to flow errors |
| Mass flow (~0.58 kg/s) & ΔT (~96 K) | **Medium** | loss coefficients ±30 % → ṁ ±15 %, ΔT ∓15 % |
| Riser front-face wall T (~185 °C) | **Medium** | face heat-split (80/15/5) + internal-h correlation |
| Weather magnitudes | **Medium** | wind C_p, inlet-air source |

**Most uncertain single assumption:** the **heat actually delivered to the air, Q_air.** I used the
sanctioned scaled duty (56 kW); the electric input (82 kWe) minus a first-principles parasitic estimate
(~11 kW) suggests it could be as high as ~72 kW. The effect is bounded and monotonic — at 70 kW the
plate is ~398 °C, riser front ~220 °C, ṁ ~0.60 kg/s, radiative fraction ~92 %, and the accident
conclusion (self-limiting, below the steel limit) is unchanged. Secondary uncertainties: the
**riser emissivity** (not reported; assumed 0.80 — a value of 0.7 raises the plate ~15 K) and the
**loop loss coefficients** (dominant term is riser friction, computed, not fitted).

## 7. Reproduce

```
cd output
python3 rccs.py         # baseline + loss breakdown + power sensitivity
python3 transient.py    # Case 2 accident transient (peak, stability)
python3 weather.py      # Case 3 outdoor-T and wind sweeps
python3 parasitic.py    # parasitic-loss estimate (heat-to-air interpretation)
```
