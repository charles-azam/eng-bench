# 02 — Materials & Physical Properties

Design/description material properties stated in ANL-ART-47. Each item cites its source section/
table. These are stated design/material properties (allowed inputs), not measured test outcomes.

---

## 1. Structural / component materials (§3.1–§3.3)
| Component | Material |
|---|---|
| Base support | W12×65 I-beam sections |
| U-channel framework | ASTM A36 channels (MC12×45, MC6×18) on 1″ steel plates |
| Inlet plenum | Aluminum alloy 3003, 1/8″ thick |
| Riser ducts | ASTM A500 Grade B rectangular steel tubing, 10″×2″×0.188″ |
| Riser support plate | 1″ ASTM A36 steel |
| Outlet-plenum / west-wall panels | L3×2×1/4″ steel angle frame, 1/8″ aluminum skins |
| N/S unheated panels | 16-gauge aluminum alloy #3000 skin |
| Primary heated plate | SAE 1020 low-carbon steel, 1″ thick |
| Heater sub-panel sheets | Stainless steel (sandblasted, heat-treated 1900 °F) |
| Chimney ducts | 24″ dia, 14-gauge galvanized steel, 0.016″ Al jacket |

### Primary heated-plate composition (§3.3.3)
SAE 1020 ladle composition limits: **0.18–0.23 % C, 0.30–0.60 % Mn, 0.040 % P (max), 0.50 % S (max),
balance Fe.** Surface: mill-scale oxidized (thin, electrically non-conducting oxide, dull dark-purple
coloration). (Plates were salvaged from the earlier PRISM/RVACS program.)

---

## 2. Surface emissivities (§3.3.3, §3.3.4, §4.2.2, §6.4.3)
| Surface | Emissivity | Source |
|---|---|---|
| Primary heated plate (mill-scale oxidized) | initially 0.7–0.9; **measured pre-test avg 0.78–0.79** | §3.3.3 |
| Heater sub-panel stainless sheets (post sandblast/heat-treat) | ≈ 0.90 (from ≈ 0.25 before) | §3.3.4 |
| Heat-flux-sensor matte-black surface | ε ≈ 1.0 | §4.2.2 |
| Heat-flux-sensor reflective (golden polyimide) surface | ε ≪ 1.0 | §4.2.2 |
| NSTF cavity sidewalls (assumed in view-factor analysis) | 0.2 | §6.4.3 |

Note: the plate emissivity 0.78–0.79 is a pre-test surface-property calibration of the plate material
(a modeling input for radiation), not a test-performance result.

---

## 3. Insulation materials & thermal specifications (§3.4, Table 9)

Applied locations: SuperIsol on all test-section insulated panels/walls; Duraboard LD as backing for
the ceramic heaters; Enerywrap 80 on chimney ductwork; Durablanket S as filler/patchwork.
**Non-insulated** areas: inlet downcomer, inlet plenum, horizontal chimney (fan-loft) ducts.
North/south/west cavity walls include 6″ of Duraboard LD. Chimney: 3″ mineral wool + 0.016″ Al jacket.

Thermal conductivity values in **BTU·in/(hr·ft²·°F)** at the listed temperatures:

| Material | Thickness | Max temp | Density | k values (°F: value) |
|---|---|---|---|---|
| Super Isol | 3″ | 1,800 °F | 16 pcf | 400 °F: 0.416 · 750 °F: 0.554 · 1100 °F: 0.693 |
| Duraboard LD | 2″ | 2,300 °F | 16 pcf | 400 °F: 0.55 · 1000 °F: 0.847 · 1600 °F: 1.339 |
| Durablanket S | 1″ | 2,150 °F | 8 pcf | 600 °F: 0.56 · 1000 °F: 0.977 · 1600 °F: 2.003 |
| Enerywrap 80 | 3″ | 1,200 °F | 8 pcf | 200 °F: 0.30 · 400 °F: 0.42 · 600 °F: 0.59 |

(pcf = lb/ft³. To convert k: 1 BTU·in/(hr·ft²·°F) ≈ 0.1442 W/(m·K).)

---

## 4. Working-fluid physical properties (reference data, §7.4.2, Tables 46 & 47)

These are **standard published fluid properties** of dry air and argon (needed as modeling inputs for
the natural-circulation working fluid and for the heavy-gas ingress scenario). They are reference
property values, not facility measurements.

### Table 46 — Dry air & argon at STP (0 °C, 101.325 kPa)
| Property | Unit | Air (dry) | Argon |
|---|---|---|---|
| Molecular weight | g/mol | 28.970 | 39.948 |
| Density ρ | kg/m³ | 1.292 | 1.784 |
| Heat capacity Cp | kJ/kg·K | 1.005 | 0.522 |
| Thermal conductivity k | W/m·K | 0.024 | 0.016 |
| Prandtl Pr | – | 0.711 | 0.665 |
| Dynamic viscosity µ | ×10⁻⁶ N·s/m² | 17.220 | 21.020 |

### Table 47 — Air & argon, 0 °C vs 100 °C (101.325 kPa)
| Property | Unit | Air 0 °C | Air 100 °C | Argon 0 °C | Argon 100 °C |
|---|---|---|---|---|---|
| Molecular weight | g/mol | 28.970 | 28.970 | 39.948 | 39.948 |
| Density ρ | kg/m³ | 1.292 | 0.946 | 1.784 | 1.305 |
| Heat capacity Cp | kJ/kg·K | 1.005 | 1.012 | 0.522 | 0.521 |
| Thermal conductivity k | W/m·K | 0.024 | 0.032 | 0.016 | 0.021 |
| Prandtl Pr | – | 0.711 | 0.701 | 0.665 | 0.664 |
| Dynamic viscosity µ | ×10⁻⁶ N·s/m² | 17.220 | 21.900 | 21.020 | 27.170 |
