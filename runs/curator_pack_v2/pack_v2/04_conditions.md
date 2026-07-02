# 04 — Heater System & Test-Case Definitions (Controlled Inputs)

Controlled/boundary inputs from ANL-ART-47: heater power system (§4.3), baseline test definition
(§7.1), the accident decay-heat scenario (§6.4.1), power-shaping profiles (§6.4.2–§6.4.3), off-normal
test-case definitions (§7.3–§7.4), and the ambient envelope (§1.5). Only *prescribed/controlled*
quantities are given; no measured system responses (flows, gas/wall/plate temperatures, removed
power, ΔP, efficiency, fluxes) are included.

---

## 1. Heater power system & control (§3.3.5, §4.3)
- Source: **200 ceramic radiant heaters** (6″×12″×0.5″), 1,100 W each, **max 220 kWe**. Powered by
  480 & 240 VAC; 120 VAC per element.
- **40 control zones** = 20 "main" (8 heaters each) + 20 "guard" (2 heaters each). Nominal split:
  **80% of power from main zones, 20% from guard zones** (guards trim temperature uniformity).
- Spatial control grid: overall height split into **ten 67-cm axial segments**; at each axial
  elevation there are **4 azimuthal zones** (2 central + 2 guard) → 40 zones total.
- Operating modes: (i) constant heat flux (**max 21.6 kW/m²**), (ii) constant temperature
  (**max 677 °C**), or (iii) an arbitrary combination.
- Controllers: 40× **Eurotherm EPower** (600 VAC, 50 A), ±1% of full-scale power regulation;
  arranged in 5 banks × 4 substations; each zone hard-wired to a Mini8 controller with a safety
  trip set-point. Power-control mode moved from Phase-Angle to **Burst Firing** in later testing.

---

## 2. Baseline test case — the primary controlled reference (§3.5, §7.1)

The baseline simulates the GA-MHTGR depressurized-conduction-cooldown (DCC) **peak** decay-heat load
of 1.5 MWt full scale → **56 kWt** in the NSTF. Config (`baseline` operating state):

1. **Heated–riser spacing:** 70.66 cm (27.82″).
2. **Outlet-plenum floor height:** 40.64 cm.
3. **Heater profile & power:** variable-burst, **linear across the 40 zones**; setpoints **56 kWe**
   and **82 kWe** (a 1st ramp to 56 kWe, then a 2nd ramp so that, after heat losses, ≈ 56 kWt reaches
   the heated section).
4. **Chimney:** open vertical stacks; cross-connect (XC) and fan lofts closed.
5. **Flow mode:** natural circulation; **dual vertical chimney** configuration.

Run011 (the reference baseline run) prescribed two steady-state hold periods: **56 kWe** held ~6 h,
then **82 kWe** held ~16 h. (Table 10 lists the nominal baseline heater power as 78 kWe; the
executive summary and §7.1 describe the baseline near ~82 kWe.)

Baseline "as-set" configuration values (from §3.5, Table 10): riser–heater spacing 0.71 m; riser flow
area 0.155 m²; outlet-plenum floor spacing 0.41 m; outlet-plenum depth 1.88 m; chimney discharge
height 19.6 m; chimney flow area 0.58 m²; flow operation natural.

---

## 3. GA-MHTGR accident decay-heat scenario (§6.4.1, §7.3.1)

Scenario: begin at **normal** steady operation (700 kWt full → **26.16 kWt** NSTF), then follow a
prescribed decay-heat time history up to the DCC-with-small-primary-leak **peak** (1.5 MWt full →
**56.07 kWt** NSTF). Linear profile, natural circulation, dual vertical chimney.

### Table 25 — Scaling ratios & resulting values (§6.4.1)
| Parameter | Scaling ratio | Full scale | ANL 1/2 scale |
|---|---|---|---|
| Power (normal) | Q̇R = √lR | 700 kWt | 26.16 kWt |
| Power (DCC accident) | Q̇R = √lR | 1,500 kWt | 56.07 kWt |
| Time | TR* = √lR | 120 hr | 84.85 hr |

### Prescribed electrical-power decay curve (§6.4.1)
The GA "RCCS Removal" decay curve was digitized, normalized to a peak of 1.5 MWt, and fit to a
polynomial. The programmed NSTF electric power is:

`P_watt,electric = [ C00 + C01·t + C02·t² + … + C09·t⁹ ] × Pscale`, with **t in minutes**,
and **Pscale = 90** (estimated to yield ≈ 56 kWt peak).

Fitted coefficients:
```
C00 =  466.531039994
C01 =  0.078631095079
C02 =  0.000170562320568
C03 = -1.28449427566e-007
C04 =  5.09424812301e-011
C05 = -1.27606140005e-014
C06 =  2.04789514471e-018
C07 = -2.08318254453e-022
C08 =  1.29530038954e-026
C09 = -4.48601180685e-031
```
Correlation coefficient 0.999958043125; standard error about the line 1.46350115015.
(Report text describes a 10th-order fit; coefficients through C09 are those tabulated.)

Run014/Run018 executed this scenario: initiate at normal steady load, then follow the scaled curve to
the peak. (Run014 and Run018 are the winter and summer executions — see ambient conditions below.)

---

## 4. Power-shaping profiles (§6.4.2–§6.4.3)

### 4.1 Cosine axial power profile (§6.4.2, Table 26)
Axial power skews were fit to the 40 zones with the integral power preserved. Peak positions
(normalized 0–1 axial): true cosine 0.5; MHTGR mid-plane 0.575; bottom-peaked 0.25.

**Table 26 — Peaking factors (Pn / Plinear) by zone:**
| NSTF Zone | Linear | Bottom Peak | Mid-Plane |
|---|---|---|---|
|1|1.0|1.225|0.498|
|2|1.0|1.325|0.831|
|3|1.0|1.425|1.010|
|4|1.0|1.375|1.140|
|5|1.0|1.275|1.248|
|6|1.0|1.150|1.313|
|7|1.0|0.900|1.294|
|8|1.0|0.650|1.157|
|9|1.0|0.450|0.904|
|10|1.0|0.225|0.605|

### 4.2 Azimuthal power skew (§6.4.3)
NSTF has only two azimuthal zones. To mimic the MHTGR cavity azimuthal skew, the prescribed control
input was a **125% vs 75% power split** between the two azimuthal heater zones. (Applied in Run026,
linear/azimuthal profile, dual vertical, natural circulation.)

---

## 5. Off-normal / prototypic test-case definitions (controlled inputs)

### 5.1 Adjacent chimney roles + short-circuit — Run017 (§7.3.3)
- Config: **adjacent** chimney roles — south chimney connected to the inlet downcomer via a 24″
  flexible duct as sole air intake; north chimney is the exhaust. Natural circulation.
- Heater: one steady-state period at **78 kWe** (~6 h), linear profile.
- Short-circuit sequence: cross-connect damper LF-CX opened to three break levels **33.3%, 50%,
  100%** of open flow area; each held 30 min, with 60 min between to re-establish steady state.

### 5.2 Blocked riser channels — Run015 (§7.4.1)
- Config: start at normal load (700 kWt full → **26.16 kWt** NSTF), linear, single vertical chimney,
  natural circulation.
- Blockage stages: **16.6%, 33.3%, 50%** blockage = physically closing **2, 4, 6** riser channels
  via inlet mechanical flaps. Specific closures: risers (2,3), then +(10,12), then +(5,8). Each stage
  held ≥ 6 h.

### 5.3 Heavy-gas (argon) ingress — Run027 (§7.4.2)
- Config: establish steady normal air operation (700 kWt full → 26.16 kWt NSTF), single vertical
  chimney, natural circulation; then transition inlet gas from air to argon (single-variable change).
- Argon acceptance target: **≥ 1,000 cu-ft** available gas volume at **< 1% O₂ (≥ 95% argon)**.
  (Exec. summary: ≈ 1,200 cu-ft of heavy gas was introduced — ~twice the internal flow-path volume.)
- Gas enclosure (above the downcomer inlet): **7 × 10 × 15 ft**, uni-strut frame wrapped in two
  layers of 6-mil (0.006″) LDPE film. A central 24″-dia air duct (normal draw) plus four 12″-dia
  bypass valves at the top corners (argon ingress mode); identical inlet flow area in both modes.
- (Argon/air physical properties for this scenario are in 02_materials.md, Tables 46–47.)

### 5.4 I-NERI scaling-philosophy test — Run023 (§7.3.4)
- Collaboration with KAERI and UW comparing scaling philosophies. On the NSTF the case was run in a
  **forced-flow** configuration (exhaust out the horizontal lofts, forced fan blowers; valves after
  the outlet plenum and before the lofts dampened to add resistance), linear profile.
- Two prescribed cases: **Case I** preserves Richardson number (RiR = 1.0); **Case II** preserves
  heat flux (q″R = 1.0). Target heated ΔT = 98 °C for both. (Per-case scaled target flow/power values
  appear in the report's Table 42; treat as design targets.)

---

## 6. Ambient / meteorological boundary conditions (§1.5, §7.3.2)
Ambient conditions are external boundary inputs (the report shows they strongly influence natural
circulation). The tested ambient envelope:
- **Outdoor temperature range across the program: −18.1 °C to +32.1 °C** (§1.5).
- Baseline (Run011) was run on a "fair, typical Midwestern winter day" (§7.1) — i.e., near-freezing
  ambient, low wind.
- Accident-scenario executions bracketed the seasonal range (§7.3.2): **Run014 (winter)** ambient
  averaging ~10 °C (span ≈ 2.9–22.5 °C); **Run018 (summer)** ambient averaging ~25 °C
  (span ≈ 19.1–32.1 °C).
- A modeler should treat outdoor air temperature, barometric pressure, humidity, and wind
  (speed/direction) as prescribed boundary conditions within the envelope above; instrument ranges
  for these are in 03_instrumentation.md.

Zero-flow / initial condition: the facility is brought to a sealed zero-flow state (all five chimney
valves closed, inlet plenum sealed) before power ramp; the working gas and structure start near
ambient/indoor temperature (§7.1).
