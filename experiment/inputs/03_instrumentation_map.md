# Instrumentation Map — Agent Input

> Where each quantity is measured in the NSTF, so you can report your model's predictions at the
> **same locations** the experiment recorded them. Curated from ANL-ART-47 §4. This file gives
> sensor **locations and types only** — never the measured values (those are held out).

## Why this matters

The measurements were taken at specific places. Report your predicted quantities at the same
locations — e.g. riser wall temperature is measured **at axial mid-plane (z = 3500 mm) on the
instrumented riser ("Riser 7")**, not as a volume average.

## Sensor inventory (counts, types, accuracy)

| Quantity | Instrument | Count | Accuracy |
|---|---|---|---|
| Zone electric power | Eurotherm EPower | 40 | ±1% |
| Heat flux (riser faces) | iTi BHT (matte + reflective) | 16 | ±5% |
| Gas-space temperature | Type-K TC | 34 | ±1.1 °C |
| Riser wall temperature | Type-K TC | 32 | ±1.1 °C |
| Heated-plate temperature | Type-K TC | 125 | ±1.1 °C |
| Insulated-wall temperature | Type-K TC | 193 | ±2.2 °C |
| System mass flow | Sierra 640S thermal mass-flow meter | 1 | ±1% rdg + 0.3 kg/min |
| Riser ΔP | Dwyer 668-11 | 8 (risers 1,2,4,6,7,9,11,12) | ±1% |
| Chimney velocity | Dwyer 160F pitot | 2 | ±8.3% |
| Inlet humidity | Dwyer RHP | 1 | ±2% |
| Weather (outdoor T, wind, RH, baro, rain) | Davis Vantage Vue (roof) | 1 | — |

## Key measurement locations

### System mass flow rate
- **Sierra 640S**, in the **inlet downcomer**, 24 in past the flow conditioner, at duct
  centerline. This measures the **total loop air mass flow** (kg/min or kg/s) through all 12
  risers. Report this whole-loop number.

### Gas (air) temperatures — per riser
- **Riser inlet gas TC:** 0.75 in above the riser bottom lip, cold side.
- **Riser outlet gas TC:** 4.0 in below the riser top lip, hot side.
- **Riser ΔT** (the headline coolant temperature rise) = outlet − inlet.
- Outlet-plenum gas and chimney gas TCs exist further downstream.

### Riser wall temperatures
- 32 Type-K TCs on riser walls. The **fully instrumented riser is "Riser 7"** (a central duct).
  Report wall temperature at the **axial mid-plane, z = 3500 mm**, on the **hot (front) face**
  unless you specify otherwise.

### Heat-flux sensors — the radiation/convection split (Riser 7, all four faces at z = 3500 mm)
- Two sensor types co-located: **matte black (ε≈1.0)** reads **total** incident flux;
  **reflective gold (ε≪1)** reads **convection-only** flux. The difference = **radiative flux**.
- Faces: **Hot/front (narrow, line-of-sight to plate)**, **Cold/rear (narrow)**, **North side
  (wide)**, **South side (wide)**.
- This is how the experiment decomposes heat removal into radiation vs convection and by face —
  your model should report the **radiative fraction of total heat removal** and, ideally, the
  per-face split (front / sides / rear).

### Heated-plate temperature
- 125 TCs flush-mounted on the 1-in steel plate. Report a **representative front-face plate
  temperature** (the report's Table-32 quantity is "heated plate, front").

### Weather station
- Davis Vantage Vue on the building roof logs outdoor air T (−40…60 °C), wind speed (to 80 m/s)
  & direction, RH, barometric pressure, at 1 record/min. These outdoor conditions are the
  **inputs** for the weather-sensitivity part of the task (the ambient T and wind drive the
  natural-circulation strength).

## Quantities to report, and where they are measured

| Predicted quantity | Where measured | Units |
|---|---|---|
| System mass flow rate | inlet downcomer (total loop) | kg/min and kg/s |
| Riser gas ΔT | outlet − inlet TC, per riser | °C |
| Riser wall temperature | Riser 7, z = 3500 mm, hot face | °C |
| Heated-plate front temperature | plate front face | °C |
| Radiative fraction of heat removal | Riser 7 four-face heat-flux sensors | – (fraction) |
| (Accident case) peak plate temperature & peak flow | as above, transient peak | °C, kg/s |
