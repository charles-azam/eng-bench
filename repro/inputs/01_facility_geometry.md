# Facility Geometry

> Curated from the facility's design/description sections. Dimensions only. (Source held in
> `../sources/`; do not consult it.)

## 1. What the facility is

A **½-axial-scale**, **air-cooled** test facility reproducing a High-Temperature Gas Reactor's
**Reactor Cavity Cooling System (RCCS)** (based on the General Atomics MHTGR design). A wall of
electric heaters stands in for the hot reactor pressure vessel (RPV). Heat crosses an air-filled
cavity to a bank of vertical steel **riser ducts**. Air inside the risers warms, becomes buoyant,
and rises with no pump (natural circulation), exits through an upper plenum into two chimney
stacks, and is replaced by cool inlet air drawn down a downcomer.

**Facility scope:** the full RCCS design has **227 riser ducts** around the vessel; this facility
reproduces a **19.03° sector** of it = **12 riser ducts**.

## 2. Overall configuration & scaling

| Parameter | Full design | This ½-scale facility | Ratio |
|---|---|---|---|
| Total RCCS height | 55.2 m | 26 m | l_R = 0.5 |
| Heated riser length | 13.86 m | 6.82 m | √l_R |
| Riser duct count | 227 | 12 | sector (19.03°) |
| Total heated area | 311.2 m² | 8.82 m² | sector × l_R |
| Outlet-plenum ceiling height | 1.83 m | 1.47 m | l_R |

Scaling: top-down; material thickness and flow area kept 1:1; air velocity and Reynolds number
scale as √l_R = 0.707; wall heat flux scales as l_R^−0.5 = 1.414.

Design heat duty (the heat the RCCS is built to remove):

| Scenario | Full-scale decay power | ½-scale power | Wall heat flux (½-scale) |
|---|---|---|---|
| Normal operation | 700 kWt | 26.16 kWt | 3.18 kW/m² |
| Peak (depressurized conduction cooldown accident) | 1.5 MWt | 56.07 kWt | 6.82 kW/m² |

## 3. Heated cavity

- Insulated enclosure on a structural frame. **East wall = heated** (the mock RPV). The **north,
  south, and west sides are insulated (adiabatic).**
- Cavity height **22 ft (6.7 m)**, width **52 in (132 cm)**.
- Cavity depth (heated-wall face → riser-tube front face) adjustable **17.7–59 in (45–150 cm)**;
  **baseline 27.82 in ≈ 706.6 mm** (riser-front-to-plate spacing 70.66 cm).
- As-built heated-plate area ≈ **10.18 m²** (note: the Table-4 scaling line lists 8.82 m² for
  "heated area"; the ~12% difference is a reporting inconsistency in the source).

## 4. Heated wall / primary heated plate (radiation source surface)

- The cavity-facing surface is a **1-in (25.4 mm) thick steel plate**, **SAE 1020 low-carbon
  steel**.
- **Surface emissivity (measured): ε ≈ 0.78–0.79** (mill-scale oxidized; range 0.7–0.9).
- Driven from behind by a 40-zone ceramic heater array (see `04_boundary_conditions_*`).
- Spans the cavity width (52 in) over the heated height (~6.7 m, in ten 67-cm axial segments).
  Exact plate height × width is given only in a dimensional drawing (see §9).

## 5. Riser ducts (coolant channels)

- **12 vertical rectangular steel tubes**, **ASTM A500 Grade B**.
- **Cross-section 10 in × 2 in (outer), wall 0.188 in.** Internal ≈ 9.624 in × 1.624 in.
- **Length 295 in (7.49 m)** total; **272 in (6.91 m) inside the heated cavity** (7 in into the
  inlet plenum below, 16 in into the outlet plenum above).
- Single-duct internal flow area ≈ **0.0101 m²**; hydraulic diameter ≈ **0.0707 m** (derive from
  the cross-section).
- **Riser surface emissivity: not reported in the source** (material: oxidized structural steel).
- The 12 ducts sit in a row across the 52-in cavity width (center-to-center pitch given only in a
  drawing — see §9). The two **10-in "wide" faces** face the neighbouring ducts; one **2-in
  "narrow" face is the front face** with line-of-sight to the heated plate, the opposite narrow
  face is the rear.

## 6. Flow path — plena, downcomer, chimney

- **Inlet downcomer:** uninsulated **24-in (0.61 m) diameter** duct; vertical → 90° elbow →
  horizontal; equivalent centerline length 184.5 in. Flow conditioner at the top.
- **Inlet plenum:** ⅛-in aluminum. Interior **44 in tall × 51.75 in wide × ~31.75 in working
  depth** (flow volume ≈ 1.18 m³). Risers protrude 7 in below its ceiling.
- **Outlet plenum:** interior **74 in tall × 74 in (E–W) × 64 in (N–S)** (≈ 5.77 m³). Riser tubes
  protrude **16 in** above its floor. Two **24-in-diameter chimney-entrance ports** on the N and S
  walls, centerline **56.5 in above the plenum floor** (40.5 in above the riser tops).
- **Chimney stacks:** dual **24-in (0.61 m) diameter, 14-ga galvanized steel** ducts, insulated.
  Equivalent flow lengths from the outlet plenum: vertical 826 in, horizontal 470 in. **Discharge
  height adjustable 7.7–19.6 m; baseline 19.6 m.** Chimney flow area baseline 0.58 m². Five
  butterfly dampers + two optional forced blowers (baseline runs: natural circulation, dampers
  open).

## 7. Insulation

| Material | Where | Thickness | Conductivity k (BTU·in/hr·ft²·°F) |
|---|---|---|---|
| SuperIsol® | test-section panels, N/S/W cavity walls | 3–6 in | 0.416 @400°F · 0.554 @750°F · 0.693 @1100°F |
| Duraboard LD® | behind ceramic heaters | 2 in | 0.55 @400°F · 0.847 @1000°F |
| Enerwrap 80® | chimney ductwork | 3 in | 0.30 @200°F · 0.42 @400°F · 0.59 @600°F |

(1 BTU·in/hr·ft²·°F = 0.1442 W/m·K.) Not insulated: inlet downcomer, inlet plenum, horizontal
chimney runs. The N/S/W cavity walls carry **6 in of insulation**. Parasitic heat losses through
the structure exist; the measured heat-loss fraction is not provided here.

## 8. Coordinate / location conventions

- Axial coordinate z = 0 at the bottom of the heated riser, z ≈ 7.0 m at the top; mid-plane
  **z ≈ 3.5 m (3500 mm)** — where the four-face heat-flux sensors are, on the instrumented riser
  ("Riser 7").
- Gas inlet temperature is measured 0.75 in above the riser bottom lip; gas outlet 4.0 in below
  the top lip. Riser temperature rise = T_gas,outlet − T_gas,inlet.

## 9. Not numerically specified in the source

Given only in dimensional drawings, not as text values:
- Riser duct center-to-center pitch (≈ 4.3 in nominal across the 52-in width).
- Exact heated-plate height × width (spans the cavity; ~6.7 m × 1.32 m envelope).
- Riser internal corner radii / exact hydraulic diameter (derive from 10 × 2 × 0.188 in).
- Riser surface emissivity.
- East-wall layer-stack thicknesses (air gap between plate and heaters, etc.).
