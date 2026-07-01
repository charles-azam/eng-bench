# Calculation Note — Passive RCCS Natural-Circulation Performance

**Facility:** ½-axial-scale, air-cooled Reactor Cavity Cooling System (RCCS) test facility, 12
instrumented riser ducts (19.03° sector of a 227-duct full design), based on the General Atomics
MHTGR RCCS concept.

**Method:** first-principles lumped/1-D thermal-hydraulic network model (radiation + natural
convection across the cavity, forced/buoyancy convection inside the risers, a buoyancy-vs-friction
natural-circulation momentum balance), built entirely from `inputs/01-04` and generic, cited,
open-literature correlations. **No published test data, reports, or pre-made models of this
facility were consulted** — every number below is derived from the given geometry/materials/
boundary conditions and standard heat-transfer/fluid-mechanics physics.

All working code is in `output/model/` (Python 3, numpy/scipy/matplotlib). Run `python3
model/run_case1.py`, `run_case2.py`, `run_case3.py` from `output/` to regenerate every number in
this note. Raw results are in `output/results/*.json`; figures in `output/figures/`.

---

## 1. Executive summary

| Quantity | Case 1 (baseline, 82 kWe) | Confidence |
|---|---|---|
| Loop air mass flow rate | **0.550 kg/s ≈ 33.0 kg/min** | Medium |
| Riser air temperature rise (ΔT) | **119 °C** (20→139 °C) | Medium |
| Riser wall, hot (front) face, Riser 7 mid-plane (z=3500 mm) | **≈ 330 °C** | Medium-low |
| Heated-plate (mock RPV) front-face temperature, mid-plane | **≈ 583 °C** | Medium |
| Radiative fraction of cavity heat transfer | **≈ 97 %** | Medium |
| Case 2 accident peak (t≈85 h, 56.07 kWt): peak plate T | **≈ 497 °C**, flow ≈0.51 kg/s | Medium |
| Does the vessel run away? | **No — temperature levels off.** Robust (structural) result. | High |
| Weather sensitivity (outdoor −18→+24 °C) | mass flow **0.61 → 0.49 kg/s** (≈ −21 %) | Medium |
| Wind sensitivity (0→11 m/s) | mass flow **+19 % to −15 %**, sign uncertain | Low |

Every number above carries an explicit assumption trail; §7 tabulates confidence and the leading
uncertainty for each.

---

## 2. Facility model and key geometric choices

Recap of the physical path (from `inputs/01`): heated plate (mock RPV, east wall) → radiates/
convects across a sealed, insulated cavity (baseline gap 0.7066 m) → outside of 12 vertical riser
ducts → conducts through the thin (4.775 mm) riser wall → forced/buoyant convection to air flowing
*inside* the risers → outlet plenum → 2 chimney stacks → discharge to outdoor air. The riser bank
itself and the internal air stream form the actual natural-circulation loop; the plate↔riser
cavity is a *separate*, sealed radiation/convection exchange (matches how the facility's own
instrumentation splits "gas-space" from "riser-wall" from "heated-plate" measurements, and why the
four-face heat-flux sensors sit on the *riser* surface, not the plate — inputs/03).

Key geometric numbers (all from `inputs/01`, cross-checked against my own derivation in
`output/model/geometry.py`):

- Riser hydraulic diameter D_h = 0.0707 m (computed from 10×2 in OD, 0.188 in wall → matches the
  source's stated 0.0707 m).
- Riser internal flow area, 12 ducts: 0.1212 m² (computed 0.1210 m², matches).
- Chimney area (2×24 in): 0.584 m² (computed 0.5837 m², matches the stated baseline 0.58 m²).

These matches give **high confidence in the geometric encoding** itself.

**Assumptions made to resolve ambiguities/inconsistencies flagged in the source:**

1. **Plate area.** Source lists two inconsistent values (10.18 m² "as-built" vs 8.82 m² "scaling
   table"). My own view-factor geometry (cavity width 1.32 m × height 6.7 m = 8.85 m²) matches the
   *scaling-table* value almost exactly, so **8.82 m² is used throughout** (both for radiation
   view factors and flux normalization) for internal consistency. Using 10.18 m² instead would
   lower the local flux and all downstream temperatures by roughly the 13 % area ratio.
2. **Riser-row width.** Taken as the full 1.32 m cavity width (the only reading of "sit in a row
   across the 52-in width" consistent with 12 ducts using their 10-in *wide* faces to face
   neighbours — a literal wide-face-to-wide-face pitch of 4.3 in would be geometrically impossible
   at 10-in duct width).
3. **Riser emissivity** (not reported): assumed **0.80** (oxidized structural steel, cf. Incropera
   & DeWitt Table A.11 "steel, oxidized," range 0.79–0.82).
4. **Elevation datum for buoyancy.** The chimney's "826 in vertical equivalent length" is
   explicitly a *friction* equivalent length (can include fitting allowances) and is inconsistent
   with the stated "discharge height 19.6 m" if read as physical elevation. I used the **stated
   19.6 m baseline discharge height** as the net buoyancy elevation (riser-bottom datum, z=0, to
   chimney exit) and the 826+470 in path length only for friction. This is flagged as one of the
   larger geometric uncertainties (§7).
5. **Axial power shape**, Case 1: uniform, per the input file.

---

## 3. Physics and correlations used (all generic, cited; none facility-specific)

### 3.1 Air properties
Ideal-gas density; Sutherland's-law viscosity (White, *Viscous Fluid Flow*; NASA RP-1311);
c_p linear fit anchored to Incropera & DeWitt Table A.4 (300 K/1000 K); Pr(T) interpolated from
the same table; k = μc_p/Pr (self-consistent); β = 1/T (ideal gas). Code: `air_properties.py`,
verified against Table A.4 at 300–800 K to within ~2 %.

### 3.2 Radiation, plate ↔ riser front faces (`radiation.py`)
Two-surface-plus-adiabatic-reradiating-surface enclosure (Incropera & DeWitt, *Fundamentals of
Heat and Mass Transfer*, 6th ed., Eq. 13.32), representing the insulated N/S/W cavity walls as a
single reradiating surface. Direct view factor F12 from the closed-form aligned-parallel-rectangle
formula (ibid. Table 13.2), scaled by the area fraction the 12 riser front faces occupy of the
full opposite plane (an approximation, since the exposed strips are evenly distributed over the
plate's height and width). Computed F12 = 0.264 (full-plane F = 0.554 × area fraction 0.476).
Riser side/rear faces are **not** given a separate radiation path to the plate (conservative
simplification — the front face is by far the dominant absorber given its direct line of sight).

### 3.3 Cavity natural convection (`convection.py`)
Sealed tall vertical rectangular enclosure (aspect ratio H/gap ≈ 9.5): Catton (1978) correlation
as tabulated in Incropera & DeWitt Table 9.3, Nu = 0.22·[Pr/(0.2+Pr)·Ra_L]^0.28·(H/L)^-0.25 for
2<H/L≤10; ElSherbiny et al. (1982) used automatically if H/L>10 (not triggered at baseline
geometry but is at the narrowest allowed cavity spacing).

### 3.4 Riser internal (duct) convection
Laminar, uniform heat flux: Nu=4.36 (circular-tube approximation of the true ~6:1-aspect
rectangular duct; Incropera Table 8.1 gives 40–70 % higher Nu for that aspect ratio at this
boundary condition, so this choice is **conservative**, i.e. it over-predicts the wall-to-air ΔT).
Turbulent: Gnielinski (1976) correlation, *Int. Chem. Eng.* 16, 359-368, valid 3000<Re<5×10⁶.
Linear blend across 2300<Re<4000.

### 3.5 Riser-wall circumferential conduction ("ring" model)
The riser front face receives essentially all the cavity radiation/convection, but the riser's
four faces are convectively cooled by the same internal air stream. A quick resistance estimate
(conduction path ≈ 0.14 m through a 4.775 mm, k=50 W/m·K wall vs. local internal-convection
resistance) shows these two resistances are comparable — i.e. the wall is **not** isothermal
around its perimeter, but also does not fully insulate the front face from the sides/rear. I
therefore solve a 3-node (front / combined-sides / rear) steady conduction–convection ring per
axial slice (`loop_solver.ring_solve`), rather than assuming either extreme. This is a
scoping-level idealization of a genuinely 2-D (or 3-D, if you count natural convection cells
inside the duct) problem; it is the **single most uncertain physics submodel** in this note (see
§7) but is the origin of the front/side/rear wall-temperature split reported in §4.

### 3.6 Loop momentum balance (`loop_solver.buoyancy_pressure` / `friction_pressure`)
Buoyancy: Δp = g·∫(ρ_amb − ρ_loop(z))dz, integrated over the riser (using the marched axial air-
temperature profile), outlet plenum, and chimney (density from a chimney-outlet temperature
computed via an exponential-duct-heat-loss formula through the Enerwrap-80 insulation), against a
reference column of ambient air over the same total height (valid because the uninsulated
downcomer/inlet plenum run near ambient temperature). Friction: Darcy–Weisbach with the Haaland
(1983) explicit approximation to Colebrook-White (turbulent) / f=64/Re (laminar), plus generic
engineering minor-loss coefficients (entrance 0.5, flow conditioner ~1.0, plenum transitions 1.5
each, duct bends 0.3, damper 0.5, discharge exit 1.0 — Idelchik/Crane-TP410-type order-of-magnitude
values, **not** derived from any facility-specific fitting data). **This minor-loss set is the
largest single uncertainty in the mass-flow-rate prediction** (§7).

### 3.7 Wind
No stack-cap geometry is given, so wind is modeled as a stack-suction pressure term at the chimney
discharge, Δp_wind = −C_p·½ρV², with a literature-typical default C_p = −0.4 (net-*aiding*, i.e.
crosswind-induced suction over an open vertical stack augments draft — generic building/stack
aerodynamics, e.g. ASHRAE Fundamentals Ch. 24 range), and an explicit sensitivity band C_p∈[−0.8,
+0.3] reported in §6 because the sign is genuinely uncertain without stack-cap details. A parallel
check showed wind's effect on chimney *heat loss* (via external convection, Jürges 1924, h=5.7+3.8V)
is negligible because the insulation resistance dominates (R_conduction ≈ 60× R_external-convection
even at 11 m/s) — wind matters here through momentum, not heat loss.

### 3.8 Parasitic (structural) heat losses
Not measured/given (source states this explicitly). Estimated from first principles using the
given insulation k(T) values: (a) conduction through the 2-in Duraboard behind the ceramic heaters
(assuming its hot face ≈ plate temperature — a likely **under-estimate**, since the heaters
themselves are probably hotter than the plate they drive) and (b) conduction through the 6-in
SuperIsol on the N/S/W cavity walls (assuming a cavity-air-side temperature ~60 % of the way from
ambient to plate temperature). Baseline result: **≈18.9 % of electric power** is lost this way
before reaching the radiation/convection network — a large fraction, and one of the leading
uncertainties in the whole calculation (§7): every downstream number (flow, ΔT, wall/plate temps)
scales with the *net* power actually crossing the cavity, not the raw electric input.

---

## 4. Case 1 — Baseline steady state (82 kWe, outdoor +2 °C, building air 20 °C, low wind)

Full output: `output/results/case1_baseline.json`; figure: `output/figures/case1_axial_profile.png`.

| Quantity | Value | Confidence |
|---|---|---|
| Net heat crossing the cavity (after 18.9% parasitic loss) | 66.5 kWt (of 82 kWe) | Medium |
| **Mass flow rate** | **0.550 kg/s = 33.0 kg/min** | Medium |
| Riser air inlet / outlet temperature | 20.0 °C / 138.9 °C | Medium |
| **Riser air ΔT** | **118.9 °C** | Medium |
| Chimney discharge air temperature | 124.4 °C (≈14 °C duct-loss drop) | Medium |
| **Heated-plate front temperature**, mid-plane (z=3500mm) | **582.7 °C** (axial range 564–604 °C) | Medium |
| **Riser hot (front) face temperature**, Riser-7 mid-plane | **329.9 °C** (axial range 275–383 °C) | Medium-low |
| Riser side-face / rear-face temperature, same location | 145.3 °C / 133.4 °C | Low (ring-model dependent) |
| **Radiative fraction of cavity heat transfer** | **97.1 %** (64.6 kW rad / 1.9 kW conv) | Medium |
| Riser internal Reynolds number (turbulent throughout) | 13,800 – 17,700 | Medium-high |
| Buoyancy head / friction head (balanced) | 69.8 Pa / 69.8 Pa | Medium |
| — friction breakdown | riser 45.3 Pa, outlet plenum 18.1 Pa, downcomer 2.5 Pa, inlet plenum 2.2 Pa, chimney 1.8 Pa | Low (loss coefficients assumed) |

**Physical picture:** at these temperatures (plate ~560-600°C, riser front ~270-375°C) radiation
dominates the cavity heat transfer by more than an order of magnitude over natural convection —
expected, since radiative exchange scales as T⁴ and the cavity gap (0.71 m) is wide enough that
natural convection across it is weak (Nu≈25–35, h≈2–3 W/m²K vs. effective radiative h≈30–100
W/m²K over this temperature range). The riser front face runs substantially hotter than its sides
and rear (my ring-conduction submodel, §3.5) because the thin duct wall does not fully spread the
concentrated front-face radiative input around the whole internal perimeter before the air stream
carries it away — this ~190 °C front-to-rear spread is a genuine physical feature of a one-sided-
heated thin-walled duct, not a numerical artifact, but its *magnitude* is one of the more uncertain
outputs in this note (§7) since it depends on a simplified 3-node idealization of what is really a
continuous 2-D conduction problem around the tube.

Flow is turbulent throughout the risers (Re~14,000-18,000), which gives confidence in the Gnielinski
correlation's applicability and in the general robustness of the mass-flow prediction (turbulent
friction and turbulent internal-convection correlations are both well-validated in this Re range).

---

## 5. Case 2 — Accident decay-heat transient

Full output: `output/results/case2_transient.json`; figure: `output/figures/case2_transient.png`.

**Power-curve note:** the supplied 10th-order polynomial (C0-C9) does **not** reproduce the
control points the input file itself states (26.16 kWt at t=0; 56.07 kWt peak at t=84.85 h) —
evaluated directly it gives 42.0 kWt at t=0, peaks near t=72 h at 87.7 kWt, and diverges to large
negative power beyond t≈110 h. This is consistent with the input file's own caveat that the C10
term is missing from the source. I therefore used the input file's **explicitly offered
fallback** — "impose the normalized shape: 26→56 kWt rise over ~85h, peak at 84.85h, then decay" —
building a smooth curve through those three stated control points (raised-cosine rise, exponential
decay after the peak with an **assumed** τ=200h post-peak time constant, since the source gives no
post-peak decay-rate data). This is flagged as a **modeling choice with real uncertainty in the
detailed transient path**, though the peak value/time themselves are taken directly from the input.

**Quasi-steady approximation:** justified because the plate/riser thermal time constants
(~48 s for the 25.4 mm plate, faster for the 4.8 mm riser wall) and the loop transport time
(~10-30 s at these flow velocities) are 3-4 orders of magnitude shorter than the ~85-hour power
ramp — the loop re-equilibrates essentially instantly relative to how fast the decay-heat curve
changes, so each instant is well approximated by the steady-state solution for Q(t) at that
instant. (High confidence in this approximation; it is a standard simplification for slow
thermal transients.)

| Quantity | Value | Confidence |
|---|---|---|
| **Peak time** (as given) | t ≈ 85 h | High (given) |
| **Peak power** (as given) | 56.0 kWt | High (given) |
| **Peak plate temperature** | **≈ 497 °C** | Medium |
| Peak riser front-face temperature | ≈ 270 °C | Medium-low |
| Mass flow rate at peak | ≈ 0.511 kg/s | Medium |

**Does the vessel stay below a safe limit — level off or run away?**

**It levels off — with high confidence, from the physics itself, independent of any specific
numeric safety limit.** Two independent lines of evidence from the model:

1. The transient itself: the imposed power curve rises to a peak and then declines (by
   construction/given), so plate temperature tracks it — rising to ≈497 °C at t≈85h then falling
   as decay heat recedes (see figure). There is no divergence at any point along the curve.
2. **More fundamentally, a steady solution exists and varies smoothly for *any* power level
   tested** — I swept the applied power from 20 kWt up to 250 kWt (4.5× the actual accident peak)
   and a converged, physically bounded steady-state solution was found at every point (plate
   temperature rising smoothly and monotonically from 293°C at 20kWt to 1207°C at 250kWt, with no
   turning point, bifurcation, or loss of solution). This reflects a structural (not numerical)
   feature of the physics: as wall temperature rises, **both** the radiative heat-removal
   capability (∝T⁴) **and** the buoyancy driving force (∝ΔT) increase monotonically with power, so
   the system's heat-removal capacity keeps pace with the imposed heat automatically — unlike, say,
   pool boiling (critical heat flux) or forced circulation (pump trip), passive gas natural
   circulation with radiation-dominated heat transfer has no known ceiling/turnaround mechanism at
   these temperatures. This is why the real design deliberately uses this passive radiation-driven
   approach for decay-heat removal.
3. As a consistency check: the Case-1 *baseline* test point (82 kWe) is deliberately run at a
   **higher** power than the actual accident *peak* (56.07 kWt) — my model shows Case 1's plate
   temperature (≈564-604°C) is correspondingly *hotter* than the true accident-transient peak
   (≈497°C), i.e. the baseline test point already bounds the accident case with margin, consistent
   with how the facility's test matrix is described.

**Numeric safety margin (lower confidence — not a given input):** no vessel/plate temperature
safety limit is provided in the inputs (this is a mock/test-article heated plate, not an
irradiated pressure vessel). Using a generic order-of-magnitude reference for carbon/low-alloy
steel long-term service (~370-450 °C, where creep/strength de-rating typically becomes significant
per general ASME Section III / API 530-type guidance — **not** facility-specific data), the
computed peak plate temperature (≈497 °C) is **above** that generic reference band by 45-125 °C
at the actual accident peak. **This
specific numeric comparison is low confidence** — it depends on (a) the ~19% parasitic-loss
assumption, (b) the front-face ring-conduction submodel, and (c) an assumed generic limit that may
not be the facility's actual pass/fail criterion. The **high-confidence conclusion is the
no-runaway/self-limiting behavior**, not the specific margin against an assumed number.

---

## 6. Case 3 — Weather sensitivity (outdoor −18…+24 °C, wind 0…~11 m/s)

Full output: `output/results/case3_weather.json`; figure: `output/figures/case3_weather.png`.

**Assumption:** the test cavity is indoors (Case 1 distinguishes "outdoor air" ≈2°C from
"building/inlet air" ≈20°C); I hold the building/inlet air fixed at 20 °C across this sweep (a
climate-controlled building will not track outdoor swings 1:1) and vary only the outdoor
temperature, which sets the buoyancy reference-column density and the chimney-discharge boundary
condition. Baseline heat load (82 kWe) held fixed throughout, per the case definition.

| Outdoor T | Mass flow | Riser ΔT | Plate T (mid) | vs. baseline (+2°C) |
|---|---|---|---|---|
| −18 °C | 0.614 kg/s | 106.2 °C | 576.2 °C | **+12%** flow |
| −2 °C | 0.562 kg/s | 116.3 °C | 581.4 °C | +2% |
| +2 °C (baseline) | 0.550 kg/s | 119.0 °C | 582.7 °C | — |
| +18 °C | 0.504 kg/s | 130.2 °C | 588.4 °C | −8% |
| +24 °C | 0.488 kg/s | 134.6 °C | 590.6 °C | **−11%** flow |

**Trend (Confidence: Medium):** colder outdoor air → denser reference column → stronger buoyancy →
higher mass flow → *lower* riser ΔT (more air carries the same heat) and slightly *lower* plate
temperature. Across the full −18…+24 °C range, mass flow varies by about **±12%** and plate
temperature by only **±1.5%** (≈8-9 °C) — the plate/wall temperatures are only weakly sensitive to
outdoor temperature because the dominant cavity heat-transfer mechanism (radiation) depends on the
plate/riser temperatures themselves, not directly on the flow rate, so a flow-rate change mostly
just re-partitions ΔT rather than changing the wall temperatures much.

**Wind (Confidence: Low — sign genuinely uncertain):** with the default assumption that crosswind
over an open stack mouth net-*aids* draft (C_p=−0.4, generic stack aerodynamics), mass flow
increases from 0.550 kg/s (calm) to 0.654 kg/s at 11 m/s (**+19%**). But because no stack-cap
geometry is given, the same physics could plausibly *suppress* draft instead (downwash); the
sensitivity band (C_p from −0.8 to +0.3) spans **+29% to −15%** in mass flow at 11 m/s relative to
calm conditions. **This is the single largest uncertainty band in this entire calculation note**
— resolving it would require either the actual stack-cap drawing or wind-tunnel/CFD data neither
of which is in the sanctioned inputs. Wind's effect on chimney heat *loss* (as opposed to
momentum) was checked and found negligible (§3.7) because the chimney insulation resistance
dominates.

---

## 7. Assumption & confidence summary

| # | Assumption | Why needed | Direction of bias if wrong | Confidence |
|---|---|---|---|---|
| 1 | Plate area = 8.82 m² (not 10.18 m²) | Source's own ~12% inconsistency | Using 10.18 m² would *lower* flux & temps ~13% | Medium |
| 2 | Riser row spans full 1.32 m cavity width | Pitch/width text is under-specified/inconsistent | Changes view factor F12, hence rad/conv split & plate T | Medium |
| 3 | Riser emissivity = 0.80 | Not reported in source | ±0.1 in ε shifts radiative q by ~±10-15% | Medium |
| 4 | Chimney elevation datum (19.6 m net buoyancy height) | "826 in" is a friction-only equivalent length | Larger true elevation gain → more buoyancy → more flow | Medium-low |
| 5 | **Parasitic loss ≈18.9% of electric power** | Not measured; only insulation k(T) given | Likely an under-estimate (heater-backside temp probably hotter than plate) → true net power to cavity may be *lower* → all temps could be somewhat lower than reported | **Low-medium — leading uncertainty** |
| 6 | **Loop minor-loss coefficients** (entrance/exit/plenum/damper K-values) | No fitting-loss data given | A 2× error in total ΣK changes mass flow by ~±30% (√ scaling) | **Low — leading uncertainty for m_dot** |
| 7 | **Riser-wall circumferential ring model** (3-node front/side/rear) | Real problem is 2-D; no data to calibrate against | Sets the front-face "hot spot" magnitude; true spread could be smaller (better spreading) or larger | **Low-medium — leading uncertainty for riser wall T** |
| 8 | Laminar internal Nu=4.36 (circular-tube approx.) | True Nu for 6:1 rectangular duct not tabulated at hand; only matters at low Re (not reached here — flow is turbulent, Re~14-18k) | Negligible impact in the cases run (all turbulent) | High (moot for these cases) |
| 9 | Wind stack-pressure coefficient C_p=−0.4 default | No stack-cap geometry given | Sign itself uncertain — see §6 | **Low — leading uncertainty for wind sensitivity** |
| 10 | Quasi-steady transient approximation | Thermal time constants ≪ decay-curve timescale | Would only break down for a much faster transient than this one | High |
| 11 | Decay-heat curve shape (fallback normalized curve, τ_decay=200h assumed) | Given polynomial doesn't reproduce stated control points | Peak value/time are as-given (high confidence); the detailed rise/fall shape between/after them is a construction | Medium (peak), Low (detailed shape) |
| 12 | Generic ~370-450°C "safety" reference temperature | No facility-specific limit given | Purely illustrative — see §5 | Low |

**Single most uncertain assumption overall:** the **loop pressure-loss (minor-loss) coefficients**
(#6) — because natural-circulation mass flow balances buoyancy against friction and friction scales
as ṁ², the mass-flow-rate prediction is roughly proportional to (Δp_buoy)^0.5/(ΣK)^0.5: a plausible
±50% uncertainty in the assumed ΣK translates to roughly ±20-25% uncertainty in predicted mass
flow, which propagates (inversely) into the riser ΔT and (more weakly, since radiation dominates)
into the wall/plate temperatures.

---

## 8. Files in this deliverable

```
output/
  calculation_note.md          <- this file
  model/
    air_properties.py          air thermophysical properties (Sutherland, ideal gas)
    geometry.py                 facility geometry, derived from inputs/01
    radiation.py                 plate<->riser view factor & 3-surface radiation network
    convection.py                cavity natural-convection & riser internal-convection correlations
    loop_solver.py               coupled ring/cavity/momentum natural-circulation solver
    decay_heat_curve.py          Case-2 power-vs-time curve (+ polynomial-mismatch documentation)
    run_case1.py / run_case2.py / run_case3.py   case drivers (reproduce every number above)
  results/
    case1_baseline.json, case1_profile.npz
    case2_transient.json
    case3_weather.json
  figures/
    case1_axial_profile.png
    case2_transient.png
    case3_weather.png
```

To reproduce: `cd output/model && python3 run_case1.py && python3 run_case2.py && python3 run_case3.py`.
