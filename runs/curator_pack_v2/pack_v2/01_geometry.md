# 01 — Facility Geometry & Scaling

Input pack for the air-based **Natural convection Shutdown heat removal Test Facility (NSTF)**
at Argonne (report ANL-ART-47). All values below are *design / as-built descriptions* taken
from the facility-description sections; each item notes its source section/table. No measured
test outcomes are included.

Unit note: the report mixes US customary and SI. Where the report gives both, both are
reproduced. Conversions I add for convenience are flagged "(≈ …, derived)".

---

## 1. Scaling basis & top-level configuration (§1.3, §1.4)

The NSTF is a **1/2 axial-scale** model (length ratio `lR = 0.5`) of the General Atomics
Modular High-Temperature Gas-cooled Reactor (GA-MHTGR) Reactor Cavity Cooling System (RCCS).

Full-scale reference reactor — **GA-MHTGR** (§1.3, Table 2):
- Power per module: **140 MWt / 87.5 MWe**; proposed plant: 4 modules, 2 steam turbines, ~560 MWe net.
- Fuel: UCO + ThO₂, graphite moderator; fuel temperature 1,060 °C max, 677 °C avg.
- Coolant: helium, 259 °C inlet / 687 °C outlet.
- Full RCCS: array of **227 riser tubes, 2.5 cm wide × 25 cm deep**, lining the concrete containment;
  concentric chimney ducts, inlet/outlet manifolds → plenums.

NSTF as-built high-level (§1.4.2):
- **12 riser ducts** at 1/2 axial scale — represents a **19.03° sector slice** of the 227-tube full design.
- Total facility height **≈ 26 m**.

### Table 3 — Scaling similarity ratios (§1.4), values for lR = 0.5
| Parameter | Scaling ratio | Value (lR = 0.5) |
|---|---|---|
| Material thickness δR | 1 | 1 |
| Area AR | 1 | 1 |
| Air velocity UR | √lR | 0.707 |
| Time ratio TR* | √lR | 0.707 |
| Heated temperature rise ΔTR | 1 | 1 |
| Reference temperature TR | 1 | 1 |
| Heat flux q″R | lR^(−0.5) | 1.414 |
| Integral power Q̇R | √lR | 0.707 |
| Heat transfer coefficient hR | lR^0.4 | 0.758 |
| Reynolds number ReR | √lR | 0.707 |
| Richardson number RiR | 1 | 1 |
| Stanton number StR | lR^0.9 | 0.536 |
| Biot number BiR | lR^0.4 | 0.758 |

Design criterion: cold inlet → hot riser reference location, atmosphere at same condition for all
scales, so ΔTR = 1.0 (temperature rise across heated section preserved).

Jet-penetration scaling (§1.4.1): Xm/Dj ∝ Fj^0.5; for the 1/2-scale facility XmR = 0.707, so the
hot outlet-plenum elevation (riser exit → plenum ceiling) was built to 0.707 of full scale.

### Table 4 — Geometric scaling comparison (§1.4.2)
| Parameter | GA RCCS (full) | ANL 1/2 scale (NSTF) | Scaling ratio |
|---|---|---|---|
| Height scaling | 1:1 | 2:1 | lR |
| Total RCCS height | 55.2 m | 26 m | lR |
| Heated riser (length) | 13.86 m | 6.82 m | √lR |
| Outlet plenum ceiling | 1.83 m | 1.47 m | lR |
| Heated area | 311.2 m² | 8.82 m² | (sector) , lR |
| Riser duct count | 227 | 12 | (sector) |

### Table 5 — Heat-removal design-basis / scaled duty targets (§1.4.2) — *inputs, not measurements*
| Parameter | Scenario | GA RCCS (full) | ANL 1/2 scale (NSTF) |
|---|---|---|---|
| Decay power | Peak, accident | 1.5 MWt | 56.07 kWt |
| Decay power | Normal | 700 kWt | 26.16 kWt |
| Heat flux | Peak, accident | 4.82 kW/m² | 6.82 kW/m² |
| Heat flux | Normal | 2.25 kW/m² | 3.18 kW/m² |
| Heated ΔT | Peak, accident | 121 °C | 121 °C |
| Heated ΔT | Normal | 67 °C | 67 °C |
| System flow rate | Peak, accident | 12.2 kg/s | 0.456 kg/s |
| System flow rate | Normal | 10.6 kg/s | 0.396 kg/s |

(These are scaled design-duty targets, explicitly allowed as inputs.)

---

## 2. Base support & cavity framework (§3.1)
- Structural base: W12×65 I-beam sections, ≈ 30,000 lb, six base supports to concrete floor, each
  secured by four 1.25″ bolts. Base assembly total height 6 ft.
- U-channel framework (supports heated-cavity assemblies): built in two sections, ASTM A36 channels
  — four MC12×45 and two MC6×18 — joined onto 1″ steel plates.

---

## 3. Flow-path ducting (§3.2)

### 3.1 Inlet downcomer (§3.2.1)
- Uninsulated **24″ diameter** duct.
- Geometry: vertical straight length → 90° elbow → horizontal straight; combined **equivalent
  centerline length 184.5″**.
- Sierra flow conditioner at top edge, extends 24″ deep (establishes fully developed inlet profile).

### 3.2 Inlet plenum (§3.2.2)
- Material: **1/8″ thick aluminum alloy 3003**.
- Total available volume **78 ft³ (2.21 m³)**; a divider plate reduces flow-available volume to
  **41.7 ft³ (1.18 m³)** (unused back cavity insulated).
- Interior box (Fig. 10 caption): **44″ tall × 51.75″ wide (parallel to riser slots) × 59.75″ deep**;
  only **31.75″** of depth available to working gas (false back wall).
- Three potential inlet ports; centerline of each 16″ from bottom; N and S ports 33″ wide (blanked
  off), primary W port 52″ wide (in use). Downcomer mates to center of west wall.
- Riser ducts extend **7″ below the plenum ceiling**; ceiling has 12 slots sealed with Kevlar wrap
  (allows thermal expansion; risers grow ≈ 1 cm upward at operating temperature).

### 3.3 Riser ducts (§3.2.3)
- **12** ducts, welded structural rectangular steel tubing, **ASTM A500 Grade B**.
- Cross-section duplicates full-scale GA design: **10″ × 2″ × 0.188″ wall** (≈ 254 × 50.8 × 4.78 mm).
  → Internal flow cross-section ≈ **9.624″ × 1.624″** per duct (derived from outer − 2×wall).
- Length **295″** each; **272″** resides within the heated cavity (7″ extends into inlet plenum,
  16″ into outlet plenum).
- Weight ≈ 385 lb/riser; 12 total ≈ 4,620 lb. Each riser has a 3/8″ support plate welded 16″ below
  its top lip.
- Top support plate: **1″ thick ASTM A36 steel**, ≈ 1,820 lb, bears full riser load.

### 3.4 Outlet plenum (§3.2.4)
- Interior: **74″ tall × 87″ east/west × 64″ north/south**. Plenum internal height also stated as
  **188 cm** (§4.2.8).
- As-built false west wall reduces width 87″ → 74″. Interior volume **203.8 ft³ (5.77 m³)**, reduced
  from total available **240 ft³ (6.79 m³)**.
- Chimney ports: **24″ diameter**, on N and S walls, at plenum E-W centerline, elevated **56.5″ from
  plenum floor** (= 40.5″ above the top surface of the riser tube ends).
- Riser-tube centerline offset **16.5″ westward** from chimney-port centers.
- With 3″ insulated floor added: riser exit face 13″ above insulated floor; chimney-port centerline
  53.5″ above insulated floor.
- Panels (5 sub-assemblies): steel angle **L3×2×1/4″** frame + **6″ insulation** + **1/8″ Al** inside
  and outside; ≈ 800 lb each.

### 3.5 Chimney stacks (§3.2.5)
- Dual ductwork assemblies; **24″ diameter, 14-gauge galvanized steel**, wrapped in **3″ mineral wool**
  + **0.016″ aluminum jacket**.
- Five butterfly valves ("loafers") with Honeywell **MS7520A2205** electronic actuators: 2–10 VDC
  control, positions 0–90° in 3° increments, 90 s for full traverse. (Flow area vs. actuator position
  in Fig. 17.)
- Two forced fan-loft blowers (see §3.6).
- Equivalent flow-path length from outlet-plenum exit: **826.13″ (vertical config)**, **470.37″
  (horizontal config)**.

#### Table 8 — Ducting segment types & equivalent lengths (§3.2.5)
Vertical path (total 826.13″):
| Seg | Radius | Eqv. run (in) | Type |
|---|---|---|---|
|1|36″|56.55|90° elbow|
|2|36″|28.27|45° elbow|
|3|n/a|22.00|Straight|
|4|36″|28.27|45° elbow|
|5|n/a|13.75|Bellows|
|6|36″|56.55|90° elbow|
|7|n/a|13.75|Bellows|
|8|n/a|42.00|4-way|
|9|n/a|40.00|Tee (straight thru)|
|10|n/a|12.00|Valve|
|11|n/a|13.75|Bellows|
|12|36″|44.61|90° elbow|
|13|n/a|36.13|Straight|
|14|n/a|13.75|Bellows|
|15|n/a|36.13|Straight|
|16|36″|44.61|90° elbow|
|17|n/a|324.00|Straight|

Horizontal path (total 470.37″):
| Seg | Radius | Eqv. run (in) | Type |
|---|---|---|---|
|1|36″|56.55|90° elbow|
|2|36″|28.27|45° elbow|
|3|n/a|22.00|Straight|
|4|36″|28.27|45° elbow|
|5|n/a|13.75|Bellows|
|6|36″|56.55|90° elbow|
|7|n/a|13.75|Bellows|
|8|n/a|42.00|4-way|
|9|20″|31.42|Tee (side port)|
|10|n/a|12.00|Valve|
|11|n/a|43.00|Straight|
|12|n/a|13.75|Bellows|
|13|n/a|31.06|Fan blower|
|14|n/a|30.00|Straight|
|15|n/a|48.00|Tapered straight|

### 3.6 Forced blower fans (§3.2.6)
- Two fan-loft blowers, model **24 AFB-H** (Air Products Equipment Co.), 3-phase 460 VAC, VFD to
  **1,725 RPM**, rated to 500 °F. (Used for isothermal/forced-flow benchmarking; flow-vs-frequency
  relation in Fig. 18.)

---

## 4. Heated cavity (§3.3)
- Overall height **22 ft (6.7 m)**; width **52″ (132 cm)**.
- Adjustable cavity depth **17.7″ to 59″ (45 to 150 cm)** in **1″ (2.5 cm)** increments.
- Baseline front-face spacing (riser tubes ↔ heated plate): **27.82″ (706.55 mm ≈ 70.66 cm)**.
- Heat-transfer area off the primary heated plate: **109.6 ft² (10.18 m²)**.
- Three sides (other than heated east wall) are adiabatic/insulated.

### 4.1 Unheated paneling (§3.3.1)
- North & south walls: **24 panel assemblies**, each **67″ × 21″**, 6″ insulation (inward) + 16-gauge
  aluminum alloy #3000 (outward).
- West wall: **4 panels**, L3×2×1/4″ frame, 6″ insulation, 1/8″ aluminum both faces, ≈ 267 lb each.

### 4.2 Heated (east) wall (§3.3.2)
- Nine-layer composite installed as three sub-assemblies: two vertical primary plates, four rows of
  heater sub-panels, four rows of outside insulation panels. Air gap between layers 1 and 2; thin
  insulation buffer between layers 2 and 3.

### 4.3 Primary heated plate (§3.3.3)
- **1″ steel plate** in front of the radiant heaters (simulates RPV surface).
- Material **SAE 1020 low-carbon steel**; lower plate ≈ 2,230 lb.
- Hung with 2″ spacers + insulation (free thermal expansion; enlarged mounting holes).
- (Material composition & emissivity — see 02_materials.md.)

### 4.4 Heater sub-panels (§3.3.4)
- **10 sub-panels**; mounting positions radiant coils away from test section for heat-flux uniformity.
- Each sub-assembly is a **2 ft × 5 ft** plate holding **20 ceramic plate heaters (6″ × 12″)**: the
  16 central elements form one (main) zone, the 4 edge elements the second (guard) zone.
- Stainless-steel sheets sandblasted + heat-treated to 1900 °F (emissivity raised 0.25 → 0.90).

### 4.5 Ceramic heaters (§3.3.5) — *see also 04_conditions.md for control/power*
- **200 ceramic heaters**, each **6″ × 12″ × 0.5″**, up to **1,100 W each** → max **220 kWe** total.
- Grouped into **40 control zones**: 20 "main" (8 plates each) + 20 "guard" (2 plates each).
  120 VAC across any individual element. 80% of total power from main zones, 20% from guard zones.

### 4.6 Heated-wall insulation panels (§3.3.6)
- Four vertical rows; sheet-metal frame housing two 3″ stacks (**6″ total**) insulation, 1/8″ Al
  exterior, ≈ 270 lb each.

---

## 5. Operating flexibility — adjustable features (§3.5, Table 10)
| Component | Range | Baseline value |
|---|---|---|
| Heater power | 0 – 220 kWe | 78 kWe |
| Heater profile | Arbitrary across 40 zones | Linear |
| Flow operation | Natural, forced | Natural |
| Forced flow | 0 – 1 kg/s | n/a |
| Riser–heater spacing | 0.45 – 1.5 m | 0.71 m |
| Riser flow area | 0.078 – 0.155 m² | 0.155 m² |
| Outlet plenum floor spacing | 0 – 0.41 m | 0.41 m |
| Outlet plenum depth | 1.88 – 2.2 m | 1.88 m |
| Chimney discharge height | 7.7 – 19.6 m | 19.6 m |
| Chimney flow area | 0 – 0.58 m² | 0.58 m² |

Four primary chimney configurations exist (Fig. 26): **baseline (dual vertical)**, **reduced
discharge**, **single chimney vertical**, and **adjacent inlet/outlet**.

The four primary as-built reconfigurable variables (§3.6): heated-wall-to-riser horizontal spacing,
riser extension into the outlet plenum, and the false walls on the inlet and outlet plenums.

---

## 6. Full-scale loop geometry & comparison (§8.3.2)

Elevation / flow-length differences between NSTF and the full-scale GA RCCS (design geometry).

### Table 56 — Elevations of inlet & exhaust ports (m)
| Configuration | Inlet — rel. grade | Inlet — rel. core | Outlet — rel. grade | Outlet — rel. core | Δ (m) |
|---|---|---|---|---|---|
| NSTF (baseline) | −1.64 | −0.83 | 18.84 | 19.64 | 20.47 |
| GA RCCS (full) | 36.88 | 20.80 | 44.40 | 28.31 | 7.52 |
| NSTF (adjacent config.) | 18.84 | 19.64 | 18.84 | 19.64 | 0.00 |

Supporting prose (§8.3.2): NSTF inlet is 2.72 ft below the thermal center of the heated cavity;
outlet is 64.45 ft above the thermal center (Δ ≈ 67.2 ft = 20.47 m, matching Table 56). Full GA RCCS
total elevation delta cited from literature as ≈ 24.67 ft (7.52 m in Table 56).

### Table 57 — Geometric ratios of loop segments (§8.3.2)
(`ℓi` = all inlet ductwork, `ℓ` = heated length, `ℓexit` = exit chimney length)
| Configuration | ℓi/ℓ (lengths) | ℓi/(ℓ+ℓexit) (flow area) | ℓi/(ℓ+ℓexit) (wetted perimeter) |
|---|---|---|---|
| NSTF (baseline) | 0.62 | 0.10 | 0.07 |
| GA RCCS (full) | 6.06 | 2.01 | 1.20 |
| NSTF (adjacent config.) | 4.64 | 1.39 | 0.70 |

### Cross-facility geometry (§7.3.4, Table 41 — design descriptions of NSTF)
NSTF entries (consistent with Table 4): total riser height 7.2 m, heated riser length 6.82 m,
12 ducts, heated area 8.820 m², heated surface type = heaters + plate, design basis GA-MHTGR.
