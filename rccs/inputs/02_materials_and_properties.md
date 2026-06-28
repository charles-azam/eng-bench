# Materials & Physical Properties

> Model inputs. Where the source does not tabulate a property, that is noted — supply it from a
> cited standard source and state the value used.

## 1. Surfaces & emissivities

| Surface | Material | Emissivity ε | Note |
|---|---|---|---|
| Heated plate (mock RPV) | SAE 1020 steel, mill-scale | **0.78–0.79** | measured |
| Ceramic-heater backing sheets | sandblasted stainless | ≈ 0.90 | measured |
| Riser ducts | ASTM A500 steel, oxidized | not reported | — |
| Cavity side/back insulation faces | board insulation surface | not reported | — |

## 2. Solid material thermal properties

The source does not tabulate k, ρ, c_p for the steels. Use standard values and state them:

| Material | Use | Typical k (W/m·K) | ρ (kg/m³) | c_p (J/kg·K) |
|---|---|---|---|---|
| SAE 1020 steel | heated plate | ~50 | 7850 | ~480 |
| ASTM A500 steel | riser ducts | ~50 | 7850 | ~480 |
| ASTM A36 steel | support plate | ~50 | 7850 | ~480 |

## 3. Insulation thermal conductivity (temperature-dependent)

Convert from BTU·in/hr·ft²·°F with **× 0.1442 = W/m·K**:

| Material | k @ ~200 °C | k @ ~400 °C | k @ ~600 °C |
|---|---|---|---|
| SuperIsol® (cavity walls) | ~0.060 | ~0.080 | ~0.100 W/m·K |
| Duraboard LD® (behind heaters) | — | ~0.079 | ~0.122 |
| Enerwrap 80® (chimney) | 0.043 | 0.061 | 0.085 |

Cavity-wall insulation thickness: **6 in (0.152 m)**.

## 4. Working fluid — air

The coolant is **atmospheric air** (open natural-circulation loop: outdoor air in, heated air out
the chimney). Operating pressure ≈ **1 atm (101325 Pa)** (facility near Chicago, ~180 m
elevation). Use temperature-dependent properties (ρ, μ, c_p, k, Pr, β) from a cited source — e.g.
CoolProp or standard correlations. The source evaluates fluid properties at the mean gas
temperature T_m = (T_inlet + T_outlet)/2.
