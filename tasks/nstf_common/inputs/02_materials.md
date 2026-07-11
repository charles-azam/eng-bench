# Materials and physical properties

## Surfaces

| Surface | Material | Emissivity |
|---|---|---:|
| Heated plate | SAE 1020 steel with mill scale | measured 0.78-0.79 |
| Ceramic-heater backing sheets | sandblasted stainless steel | about 0.90 |
| Riser ducts | oxidized ASTM A500 steel | not reported |
| Side/back insulation faces | board insulation | not reported |

Treat unreported emissivities as uncertain inputs and propagate a justified range.

## Solids

The source does not tabulate temperature-dependent steel properties. A defensible initial model may
use `k = 50 W/(m K)`, `rho = 7850 kg/m3`, and `cp = 480 J/(kg K)` for the plate and risers, with a
sensitivity range appropriate to the modeled temperatures.

The cavity side/back walls carry 6 in (0.152 m) of SuperIsol insulation. Representative conductivity
is about 0.060 W/(m K) near 200 C, 0.080 near 400 C, and 0.100 near 600 C. Chimney insulation is
3 in Enerwrap 80, approximately 0.043 W/(m K) near 200 C, 0.061 near 400 C, and 0.085 near 600 C.

## Working fluid

The coolant is atmospheric air in an open loop near 1 atm. Use temperature-dependent density,
viscosity, heat capacity, conductivity, Prandtl number, and expansion coefficient. A correlation or
property fit already known to you may be used offline, but its source and valid range must be stated.

Provenance: ANL-ART-47 Sections 3.3-3.4 (report pp. 40-50) and Section 5.4 (report pp. 123-132).
