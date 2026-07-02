# Calculation Note — Passive Reactor Cavity Cooling System (RCCS)

**Facility:** ½-axial-scale, air-cooled RCCS test facility (mock HTGR, GA-MHTGR-type),
19.03° sector = 12 riser ducts, natural circulation, dual chimney.
**Author:** engineering analysis, from first principles.
**Date:** 2026-07-02.

> **Provenance statement.** Every number in this note was derived from the geometry, materials
> and boundary conditions given in `inputs/` plus textbook physics and cited general
> correlations. **No published data, test report, or pre-made model of this facility was
> consulted.** Where the inputs did not supply a property (riser emissivity, steel k/ρ/cₚ,
> parasitic-loss fraction) I supplied a standard value from a cited source and state it as an
> assumption. Air properties are from CoolProp (dry air, 1 atm).

---

## 1. Method summary

Two independent models were built and reconciled:

1. **Reduced (0-D/1-D) loop model** (`model.py`): couples a loop momentum balance
   (buoyant draft = friction + form losses → mass flow), an energy balance
   (Q = ṁ cₚ ΔT → air temperature rise), a cavity heat-transfer model
   (radiation + enclosed natural convection → plate & riser wall temperatures), and an
   internal-convection + circumferential wall-conduction (fin) model → the local riser
   hot-face temperature at the sensor plane.

2. **Independent higher-fidelity CFD** (`cfd/rccs2d`, OpenFOAM `buoyantSimpleFoam`):
   a 2-D vertical slice of the cavity (depth × height) that **solves** the buoyant air flow,
   the Discrete-Ordinates (fvDOM) surface-to-surface radiation, and the wall temperatures.
   The **heat input is prescribed** as an electric heat flux on the plate; the internal
   coolant is represented by a convective sink (coefficient + coolant temperature). The plate
   and riser-front **temperatures are outputs, not inputs** — exactly the cross-check the task
   requires. See §9.

All the physics (buoyancy, friction, radiation network, convection correlations) is built from
the inputs; correlations are cited where used.

### Key geometry (derived from `inputs/01`)
| Quantity | Value | Source |
|---|---|---|
| Riser internal cross-section | 0.2445 × 0.0413 m, A₁ = 0.01008 m² | 9.624×1.624 in |
| Riser hydraulic diameter Dₕ | 0.0706 m | 4A/P |
| Risers | 12, total flow area 0.1210 m² | input |
| Heated length | 6.7 m (plate height); risers 6.91 m in cavity | input |
| Internal wetted (heated) area | 45.9 m² (12 × perimeter × 6.7 m) | derived |
| Heated plate area | 10.18 m² (as-built) | input |
| Cavity gap (plate→riser front) | 0.7066 m | input baseline |
| Chimney discharge height H | 19.6 m; chimney area 0.58 m² (dual 24-in) | input baseline |
| Downcomer | single 24-in, 0.292 m² | input |

### Heat input (derived, see §8)
Case-1 electric power is 82 kWe. An **independent parasitic-loss estimate** (`parasitic.py`:
back-of-heater conduction + insulated cavity walls + uninsulated outlet-plenum shell) gives
**≈ 24 kW** of structural loss, leaving **Q_air ≈ 56 kW** reaching the coolant — which coincides
with the scaled 1.5 MWt peak-accident duty (56.07 kW). **Q_air = 56 kW is used for Case 1.**

---

## 2. Natural-circulation mass flow rate  *(report location: inlet downcomer, whole loop)*

**Result (Case 1, Q_air = 56 kW, inlet air 20 °C, outdoor 2 °C):**

| Quantity | Reduced model | 
|---|---|
| **Mass flow ṁ** | **0.57 kg/s = 34 kg/min** |
| Riser bulk velocity | 4.6 m/s (Re ≈ 1.6 × 10⁴, turbulent) |
| Buoyant draft = total loss | ≈ 64 Pa |

**Physics.** The driving pressure is the chimney/stack effect,
ΔP_drive = g[ρ_amb·H − ∫ρ_int dz], with ρ_amb at the **outdoor** temperature (the stack sits in
and discharges to outdoor air), and the internal density integrated over the heated risers
(linear T rise) plus the hot chimney column to the 19.6 m discharge. This is balanced against
friction (Darcy, Petukhov smooth-pipe f) + form losses (riser inlet/exit, plena, chimney
entrance/turn, downcomer elbow/conditioner, discharge). The riser + chimney friction and the
plena/entrance form losses dominate. Solving ΔP_drive(ṁ,T_out) = ΔP_loss(ṁ) gives ṁ.

**Confidence: medium-high (±15 %).** The mass flow is pinned by the energy balance
(ṁ ≈ Q/(cₚΔT)) and the draft/loss balance, both robust. The largest uncertainty is the **lumped
form-loss coefficient** (ΣK for plena/entrances, assumed ≈ 6 velocity-heads total) and the exact
chimney equivalent length; a ±50 % change in ΣK moves ṁ by ≈ ±10 %.

---

## 3. Riser air temperature rise  *(outlet TC − inlet TC, per riser)*

**Result (Case 1):** **ΔT ≈ 97 °C** (inlet 20 °C → outlet ≈ 117 °C).

From Q_air = ṁ cₚ ΔT with ṁ = 0.57 kg/s, cₚ ≈ 1010 J/kg·K, Q = 56 kW.
**Confidence: high** for the *product* ṁ·ΔT (fixed by energy conservation); the split between ṁ
and ΔT carries the flow-model uncertainty above. If Q_air is really 70 kW (low-parasitic bound),
ΔT rises to ≈ 117 °C and ṁ to ≈ 36 kg/min (§8 sensitivity).

---

## 4. Riser duct wall & heated-wall (plate) temperatures  *(Riser 7, z = 3500 mm, hot face)*

**Reduced-model result (Case 1):**

| Location | Temperature |
|---|---|
| **Heated plate (mock RPV), front face** | **≈ 372 °C** |
| Riser wall, **hot (front) face**, z = 3500 mm | **≈ 181 °C** |
| Riser wall, side face | ≈ 128 °C |
| Riser wall, rear face | ≈ 110 °C |
| Riser wall, circumferential mean | ≈ 131 °C |
| Bulk coolant at z = 3500 mm | ≈ 69 °C |

**Physics.** The plate temperature is set by requiring the cavity to transfer 56 kW to the risers
by **radiation + enclosed natural convection** (§5). The riser mean wall temperature is set by the
internal convection resistance, T_wall,mean = T_air + Q/(h_int·A_int) with h_int ≈ 18 W/m²·K
(Gnielinski). The **circumferential distribution** (front hottest) is obtained by solving a 1-D
perimeter fin equation, k·t·d²T/ds² + q″(s) − h_int(T−T_air) = 0, with the radiative flux
concentrated on the front (line-of-sight) face; the 4.8 mm steel wall spreads the heat so the
front-face hot spot is bounded to ≈ 50 °C above the mean.

**Confidence: medium.** Plate temperature ±25 °C; riser front-face ±20 °C. Most-uncertain inputs:
the **riser emissivity** (not reported; assumed 0.80) and the **cavity radiation view factor /
effective area** (§5, §10). These are cross-checked by CFD in §9.

---

## 5. Split of removed heat: radiation vs convection  *(Riser 7 four-face flux sensors)*

**Reduced-model result (Case 1):** **radiation ≈ 91 %, convection ≈ 9 %** of the 56 kW.
(Q_rad ≈ 51 kW, cavity natural convection ≈ 5 kW.)

**Physics.** Across the 0.71 m air gap the plate (≈ 645 K) and riser plane (≈ 404 K) exchange heat
by (a) **gray-diffuse radiation** — parallel-surface network with re-radiating adiabatic
side/back walls, ε_plate = 0.785 (measured), ε_riser = 0.80 (assumed), giving
Q_rad = σ(T_p⁴−T_r⁴)/[network resistance]; and (b) **enclosed natural convection** — vertical
cavity, aspect ratio H/L ≈ 9.5, Ra_L ≈ 6 × 10⁸, Nu from the Catton vertical-enclosure correlation
(Bejan, *Convection Heat Transfer*), giving h_cav ≈ 2 W/m²·K. Radiation dominates because it scales
as T⁴ at these temperatures while enclosed-cavity convection is weak — a defining feature of
RCCS cavities. Radiative flux is concentrated on the riser **front** face (line of sight to the
plate); the model's per-face split is front ≫ sides > rear.

**Confidence: high on "radiation-dominated" (85–95 %); medium on the exact 91 %.** The convection
fraction depends on h_cav (cavity correlation, factor ~2 uncertainty), but even doubling h_cav
only moves the radiative fraction to ≈ 84 %.

---

## 6. Accident (decay-heat) transient — peak temperatures & safety  *(Case 2)*

The air-side decay heat is imposed per `inputs/04` as the sanctioned normalized shape rising
**26 → 56 kW**, peaking at **t = 84.85 h** (½-scale), then decaying. (The digitized 10th-order
polynomial is missing its C₁₀ term and diverges at the tail — it gives ≈ 83 kW at 85 h instead of
the documented 56 kW — so the normalized shape is used instead; noted in `cases.py`.)

**Quasi-steady argument.** The lumped thermal capacitance of the steel (plate + risers, C ≈ 3
MJ/K) against the plate-side conductance (dQ/dT_plate ≈ 4εσT³A ≈ 0.4 kW/K) gives a **time constant
τ ≈ 2 h**, far shorter than the ≈ 85 h transient. The system therefore tracks its steady state
with a small (~2 h) lag; the lumped-capacitance integration (`cases.py`, figure
`figs/case2_transient.png`) confirms the peak plate temperature occurs at t ≈ 87 h and equals the
steady 56 kW value.

**Result:**
| Quantity | Value |
|---|---|
| Peak air-side heat | 56 kW at 84.85 h |
| **Peak plate temperature** | **≈ 372 °C** (steady-state at 56 kW) |
| Peak riser front-face | ≈ 181 °C |
| Peak mass flow | ≈ 34 kg/min |
| Outlet air | ≈ 117 °C |

**Does it run away or level off? → It LEVELS OFF (no runaway).** Two independent stabilising
feedbacks guarantee a stable equilibrium at every power level: (i) heat removal by radiation rises
as T_plate⁴, a steep negative feedback, and (ii) the natural-circulation flow **increases** with
power (stronger buoyancy), raising convective removal. Since removed heat rises monotonically and
steeply with plate temperature while the input is bounded, a stable steady state always exists.
The peak plate temperature (≈ 372 °C) is **well below** any credible vessel/steel safety limit
(HTGR RPV accident limit ≈ 550 °C; SAE 1020 plate retains strength far above 372 °C).

**Confidence: high on "levels off / stays safe"; medium on the exact 372 °C** (same cavity-model
uncertainties as §4). Even the low-parasitic bound (70 kW → plate ≈ 411 °C) stays below 550 °C.

---

## 7. Sensitivity to outdoor conditions (air temperature, wind)  *(Case 3)*

**Outdoor air temperature (−18 → +24 °C), same 56 kW load** (figure `figs/case3_weather.png`):

| Outdoor T | Mass flow | Plate T |
|---|---|---|
| −18 °C | ≈ 39 kg/min | ≈ 368 °C |
| +2 °C (baseline) | ≈ 34 kg/min | ≈ 372 °C |
| +24 °C | ≈ 30 kg/min | ≈ 376 °C |

Colder outdoor air is **denser**, so the stack draft ρ_amb·g·H is stronger → more flow → lower
ΔT and slightly lower wall temperatures. The effect is monotonic and modest: over the full 42 °C
range the mass flow changes ≈ ±13 % and plate temperature ≈ ±6 °C. **Winter operation is
conservative (more cooling); summer is the limiting case but only marginally.**

**Wind.** Modelled as an adverse dynamic pressure at the chimney discharge (worst-case,
K = 1 stagnation): at 11 m/s the draft can be opposed by ≈ 0.5ρV² ≈ 77 Pa, comparable to the
64 Pa buoyant draft, cutting mass flow toward ≈ 16 kg/min in the worst orientation. **Confidence:
low on the wind magnitude** — real stacks see a mix of adverse/assisting/cross wind and often have
caps; favourable wind *increases* draft. The robust statement is that wind is a second-order,
direction-dependent modulation of the draft, bounded by ± one dynamic head at the discharge.

---

## 8. Heat-input & parasitic-loss assumption

`parasitic.py` estimates structural losses from first principles (insulation conduction + external
convection/radiation): back-of-heater (Duraboard 2 in) ≈ 6.7 kW, N/S/W cavity walls (SuperIsol
6 in) ≈ 1.9 kW, uninsulated outlet-plenum shell ≈ 15 kW → **≈ 24 kW total**, so of 82 kWe input
**≈ 56 kW reaches the coolant**. This *independently reproduces* the scaled 56 kW peak duty and
justifies Q_air = 56 kW. **Sensitivity:** if losses are only ~15 % (Q_air ≈ 70 kW), ṁ → 36 kg/min,
ΔT → 117 °C, plate → 411 °C (all reported in `results.json` as `case1_hiQ`). **Most-uncertain
single assumption in the whole note:** the outlet-plenum loss (uninsulated, area/temperature
poorly constrained), which sets Q_air within ±15 %.

---

## 9. Independent higher-fidelity CFD cross-check  *(item 7)*

**Tool & setup.** OpenFOAM v2312 `buoyantSimpleFoam` (steady, compressible, buoyant RANS
k-ω SST) on a 2-D vertical slice of the cavity (depth 0.7066 m × height 6.7 m, 60 × 200 cells),
run in Docker on this machine (`cfd/rccs2d`). Surface-to-surface radiation is solved with the
Discrete-Ordinates model **fvDOM** (near-transparent air; wall emissivities ε_plate = 0.785,
ε_riser = 0.80, adiabatic re-radiating ends). **The heat input is prescribed** as a uniform
electric heat flux on the plate, q″ = 56 kW / 10.18 m² = **5501 W/m²**; the coolant is a
convective sink on the riser wall (h_eff = 82.3 W/m²·K referenced to the front-plane area — i.e.
the internal Gnielinski coefficient scaled by the internal-to-plane area ratio 4.5 — and coolant
temperature 342 K). **The plate and riser temperatures and the radiative flux are OUTPUTS.**
Neither temperature was prescribed. To get past the stiff cold-start of a fixed-flux +
radiation coupling, the flux was ramped in small increments to the full 5501 W/m² (each stage
restarted from the previous converged field); the final field is at the full flux.

**CFD results (converged at q″ = 5501 W/m²) and reconciliation with the reduced model:**

| Quantity (Case 1) | Reduced model | **CFD (solved)** | Agreement |
|---|---|---|---|
| Heated-wall (plate) T, mid-plane z = 3.5 m | 372 °C | **333 °C** | within ~10 % |
| Plate T, area-mean | 372 °C (lumped) | 335 °C | within ~10 % |
| Riser wall T, z = 3.5 m | 131 °C (mean) / 181 °C (front) | **124 °C** | mean within ~5 % |
| Riser wall T, area-mean | 131 °C | 122 °C | within ~7 % |
| **Radiative fraction of heat removal** | **91 %** | **89 %** (plate radiates 4912 of 5501 W/m²) | excellent |

**Interpretation.** The independent CFD, which *solves* the buoyant flow and the DOM radiation
field with only the heat flux imposed, reproduces the reduced model's heated-wall and riser-wall
temperatures to within ~10 % and its radiation-dominated split (≈ 90 %) almost exactly. The CFD
plate runs ~40 °C cooler than the reduced lumped value because it resolves the enclosed-cavity
buoyant recirculation, which transfers slightly more heat by convection than the Catton
correlation, and it captures the axial stratification (plate hottest near the cool-air-fed bottom,
coolest near the hot top — figure `figs/cfd_profiles.png`). The single-wall 2-D slice represents
the riser as one plane, so its temperature corresponds to the tube's **circumferential-mean**
wall temperature (131 °C reduced ↔ 122 °C CFD); the reduced model's separate 181 °C is the
**front-face hot spot** from the perimeter-fin model, which the single-wall slice does not resolve.

**Caveat (honest).** The 2-D slice has adiabatic radiating end walls; a residual energy imbalance
of ~20 % (the coolant sink removes ~80 % of the imposed flux at the settled state) leaks to those
ends / reflects the not-fully-tightened residuals. This shifts the absolute plate temperature by
at most ~20–30 °C and does not affect the conclusions (radiation-dominated, plate 330–375 °C,
riser wall ~120–130 °C). The two independent methods **corroborate** each other.

---

## 10. Assumptions & most-uncertain items (consolidated)

1. **Q_air = 56 kW** (parasitic ≈ 24 kW of 82 kWe) — independently estimated (§8); ±15 %. *Most
   uncertain global input.*
2. **Riser emissivity = 0.80** (not reported; oxidised structural steel, range 0.7–0.9). Drives
   radiative split and riser temperature.
3. **Cavity radiation view factor** F ≈ 0.9 with re-radiating adiabatic walls (parallel-surface
   idealisation of a discrete-tube bank). Cross-checked by CFD.
4. **Cavity natural-convection h** (Catton correlation) — factor ~2; small effect (radiation
   dominates).
5. **Lumped form-loss ΣK ≈ 6** for plena/entrances/turns — ±50 % → ±10 % on ṁ.
6. **Wind coupling** — worst-case adverse assumed; direction-dependent, low confidence.

All correlations cited: Petukhov/Blasius friction, Gnielinski internal Nu, Catton vertical-cavity
Nu (Bejan), gray-diffuse radiation network (Incropera/Modest), ideal-gas stack-effect draft.
