# Measured values (the answer key)

Source: **ANL-ART-47**, *Final Project Report on RCCS Testing with the Air-Based NSTF*,
Argonne National Laboratory, August 2016 (public, OSTI 1350591) — plus the companion ambient-
effects paper (ICONE25-67418, 2017). Section/table cited per line. These values were **not** on
the machine during any agent run.

## Baseline steady state — test Run011 (§7.1, Table 32)
| Quantity | Measured | Note |
|---|---|---|
| Heater electric power | 81.99 kWe | the controlled input |
| Thermal power removed by air | 56.12 kWt | ⇒ electric→air efficiency ≈ 68% |
| System mass flow rate | 34.46 kg/min = 0.574 kg/s | whole 12-duct loop |
| Riser gas ΔT (outlet−inlet) | 103.85 − 19.74 = 84.1 °C | |
| Riser duct wall temperature | 163.1 °C | instrumented riser, mid-plane |
| Heated plate (mock vessel) front | 390.7 °C | |
| Radiation vs convection | radiation-dominant | four-face heat-flux sensors, §7.1.1/Fig 78; convective h ≈ 3–6 W/m²K (Table 22) |

Across all 8 baseline repeats (weather −18.1…+23.7 °C outdoors): flow 28.1–36.3 kg/min,
riser wall 152.5–183.3 °C, thermal power 48.6–56.1 kWt (Table 31/32).

## Accident decay-heat transient — Run014 (§7.3.1, Table 35)
| Quantity | Steady (normal) | Peak accident |
|---|---|---|
| Electric power | 42.08 kWe | 90.07 kWe |
| Thermal power | 25.06 kWt | 54.49 kWt |
| System flow | 0.499 kg/s | 0.585 kg/s |
| Riser ΔT | 49.4 °C | 90.3 °C |
| Heated plate | 275.3 °C | **408.7 °C** |

Outcome: **bounded turn-over** — plate peaked ≈409 °C near the decay-heat peak (t ≈ 92 h) and
then cooled as the source decayed. Not a runaway.

## Weather sensitivity (§7.5; Table 37; ICONE25-67418)
- Colder outdoors ⇒ denser air ⇒ **more** flow, **lower** ΔT and metal temperatures.
- Magnitude: summer→winter across the baseline repeats, flow 28.1→36.3 kg/min (~25% spread);
  accident winter vs summer: flow −19.2% (normal) / −13.8% (peak); riser wall +14.4% / +9.1%.
- Wind: assists draft (2nd-order, ΔP ∝ V²); fitted zero-power correlation
  ṁ = (5.53·ΔT + 3.75·V²)^(1/1.8) kg/min. A 6 m/s wind once broke a start-up (reverse flow).

## Blind scenarios (packs/blind2)
| Scenario | Measured outcome |
|---|---|
| B1: 50% of risers blocked (Run015, Table 45) | flow 0.459→0.287 kg/s; plate rose only 278.9→292.0 °C (**+13 °C — graceful**) |
| B2: argon ingress (Run027, Tables 50/51) | circulation collapsed to stagnation within ~90 s; riser outlet spiked 91→126 °C; **self-recovered** by ~30 min |
| B3: accident summer vs winter (Table 37) | flow −19%/−14%; riser wall +14%/+9%; plate only +2%/+1.5% (radiation-protected) |
