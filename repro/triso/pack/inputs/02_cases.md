# Inputs 02 — Prediction cases (conditions only)

Five accident-heating cases. For each element: the particle geometry/composition is in
`01_particles_and_elements.md`; the material properties and release correlations are in
`03_material_properties.md`. Each case below gives the element type and particle count, the
irradiation history the element accumulated in the reactor, and the furnace heating schedule it
was then subjected to.

Fast fluences are quoted for **E > 0.1 MeV** unless noted. To convert to **E > 0.18 MeV**, divide
by 1.10. Irradiation temperatures marked (s)/(c) are surface/centre; "efpd" = effective full-power
days.

A heating schedule is read as a staircase: each row is a temperature set-point, the "ramp" column
is the time taken to reach that set-point from the previous one, and the "hold" column is the time
held at that set-point. Drops back to 300 °C or 20 °C are intermediate cool-downs.

---

## Case A1 — HFR-K3/1 (sphere)

- **Element:** GLE-3 graphite sphere, **16,400** coated particles.
- **Irradiation history:**
  - Burnup: **7.7 % FIMA**
  - Fast fluence: **3.9 × 10²⁵ n/m² (E > 0.1 MeV)** (≈ 4.0 × 10²⁵ per Table 10.11)
  - Irradiation temperature: **1020 °C (surface) – 1216 °C (centre)**
  - Duration: **359 efpd (8616 h)**
- **Heating schedule (furnace):**

  | Set-point (°C) | Ramp to set-point (h) | Hold at set-point (h) |
  |---|---|---|
  | 300 | — | 0.5 |
  | 1050 | 1.5 | 5.5 |
  | 1250 | 0.5 | 16.5 |
  | 1550 | 6.5 | — |
  | 300 | 1 | — |
  | 1600 | 9 | 500 |

  Total ≈ 541 h. The case of interest is the **1600 °C hold for 500 h**.

---

## Case A2 — HFR-K3/3 (sphere)

Sister sphere to A1 (same batch and element design), taken to higher burnup and heated hotter.

- **Element:** GLE-3 graphite sphere, **16,400** coated particles.
- **Irradiation history:**
  - Burnup: **10.2 % FIMA** (10.6 % FIMA quoted for the heating-phase inventory in Table 10.11)
  - Fast fluence: **6.0 × 10²⁵ n/m² (E > 0.1 MeV)** (5.9 × 10²⁵ per Table 10.11)
  - Irradiation temperature: **700 °C (surface) – 983 °C (centre)**
  - Duration: **359 efpd (8616 h)**
- **Heating schedule (furnace):**

  | Set-point (°C) | Ramp to set-point (h) | Hold at set-point (h) |
  |---|---|---|
  | 300 | — | 0.5 |
  | 1050 | 1.5 | 5.5 |
  | 1250 | 0.5 | 13.5 |
  | 1800 | 12 | 25.5 |
  | 300 | 1 | — |
  | 1050 | 1.5 | 19.5 |
  | 1250 | 0.5 | 19 |
  | 1800 | 12 | 74.5 |

  Total ≈ 187 h. The **1800 °C exposure totals 100 h** (25.5 h + 74.5 h across two segments,
  the schedule having been interrupted and resumed).

---

## Case B — HFR-K6/3 (sphere), staged heating

- **Element:** GLE-4 graphite sphere (AVR 21), **14,580** coated particles.
- **Irradiation history:**
  - Burnup: **10.9 % FIMA**
  - Fast fluence: **4.8 × 10²⁵ n/m² (E > 0.1 MeV)**
  - Irradiation temperature: **1140 °C (surface)**
  - Duration: **634 efpd (15,216 h)**
- **Heating schedule (furnace), staged:**

  | Set-point (°C) | Ramp to set-point (h) | Hold at set-point (h) |
  |---|---|---|
  | 300 | — | 7 |
  | 1050 | 2 | 13.5 |
  | 1600 | 11 | 99 |
  | 20 | 17 | — |
  | 1700 | 5.5 | 100 |
  | 20 | 17 | — |
  | 1800 | 2 | 100 |
  | 20 | 17 | — |
  | 300 | 7 | — |
  | 1800 | 1 | 300 |

  Total ≈ 699 h. Four heating phases: **1600 °C / 100 h**, **1700 °C / 100 h**, **1800 °C / 100 h**,
  then a fourth phase **again at 1800 °C for a further 300 h**.

---

## Case C1 — HFR-P4/3-7 (compact)

Higher-burnup member of the HFR-P4 compact pair. Same heating schedule as C2 — the pair isolates
the effect of burnup at fixed temperature.

- **Element:** LEU-phase-1 compact, **1631** coated particles.
- **Irradiation history:**
  - Burnup: **13.9 % FIMA**
  - Fast fluence: **7.5 × 10²⁵ n/m² (E > 0.1 MeV)** (7.2 × 10²⁵ E > 0.18 MeV equivalent)
  - Irradiation temperature: **1075 °C** (irradiation-phase temperature ≈ 1050–1075 °C)
  - Duration: **351 efpd (8424 h)**
- **Heating schedule (furnace):**

  | Set-point (°C) | Ramp to set-point (h) | Hold at set-point (h) |
  |---|---|---|
  | 300 | — | 0.5 |
  | 1050 | 1.5 | 5.5 |
  | 1250 | 0.5 | 13.5 |
  | 1600 | 7.5 | 304 |

  Total ≈ 333 h. The case of interest is the **1600 °C hold for 304 h**.

---

## Case C2 — HFR-P4/1-12 (compact)

Lower-burnup member of the pair; identical heating schedule to C1.

- **Element:** LEU-phase-1 compact, **1631** coated particles.
- **Irradiation history:**
  - Burnup: **11.1 % FIMA**
  - Fast fluence: **5.5 × 10²⁵ n/m² (E > 0.1 MeV)**
  - Irradiation temperature: **940 °C** (irradiation-phase temperature ≈ 900–940 °C)
  - Duration: **351 efpd (8424 h)**
- **Heating schedule (furnace):**

  | Set-point (°C) | Ramp to set-point (h) | Hold at set-point (h) |
  |---|---|---|
  | 300 | — | 0.5 |
  | 1050 | 1.5 | 5.5 |
  | 1250 | 0.5 | 13.5 |
  | 1600 | 7.5 | 304 |

  Total ≈ 333 h. The case of interest is the **1600 °C hold for 304 h**.

---

### Summary table (conditions)

| Case | Element | Particles | Burnup (%FIMA) | Fluence (10²⁵, E>0.1 MeV) | Irrad. T (°C) | Peak heating T (°C) | Time at peak (h) |
|---|---|---|---|---|---|---|---|
| A1 | HFR-K3/1 sphere | 16,400 | 7.7 | 3.9 | 1020(s)–1216(c) | 1600 | 500 |
| A2 | HFR-K3/3 sphere | 16,400 | 10.2 | 6.0 | 700(s)–983(c) | 1800 | 100 |
| B | HFR-K6/3 sphere | 14,580 | 10.9 | 4.8 | 1140(s) | 1800 | 100 + 300 (staged) |
| C1 | HFR-P4/3-7 compact | 1631 | 13.9 | 7.5 | 1075 | 1600 | 304 |
| C2 | HFR-P4/1-12 compact | 1631 | 11.1 | 5.5 | 940 | 1600 | 304 |
