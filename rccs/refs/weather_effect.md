# ⛔ HELD-OUT — The Weather / Ambient Effect (Case 3 answer)

Sources: ANL-ART-47 §6.3/§7.5 and companion **ICONE25-67418** (Hu et al., 2017).

## The finding

Repeating the *identical* baseline test across seasons gave **different flow and ΔT** even though
power was unchanged — passive cooling performance is set partly by the **weather outside the
building**. This is the project's surprise beat.

## Which variables matter

- **Outdoor air temperature** — dominant. Sets the stack-effect driving head via the indoor/
  outdoor density difference.
- **Wind speed** — dominant. Wind over the chimney exits lowers pressure there and **enhances**
  the draft (2nd-order in wind speed).
- **Humidity** — **negligible** (≲ 2% flow effect; once air is heated to ~100 °C its RH < 2%).
- **Absolute** inlet temperature matters, not just ΔT, because ρ(T) is non-linear (Δρ/ΔT shrinks
  at higher absolute T).

## Direction & magnitude (measured)

- **Colder outdoor air → denser air → larger driving head → HIGHER mass flow** → at fixed power,
  **LOWER riser ΔT and lower peak wall temperature.**
- Across the 8 baseline runs (outdoor −18.1 → +23.7 °C, span 41.8 °C):
  - Mass flow **28.08 (summer) → 36.27 kg/min (winter)** — ~25% spread.
  - Riser ΔT **~94 °C (summer) → ~77 °C (winter)** — ~17 °C swing.
  - Riser wall temp **152.5 → 183.3 °C** across runs.
- Accident winter vs summer (Run014 vs Run018, ~15 °C warmer): flow **−19%** (normal) / −14%
  (peak), riser-wall temps **+9–14%**.
- **Wind can break start-up:** a 6 m/s sustained wind caused reverse-flow oscillations that
  pushed 58 °C air back into the inlet plenum (Run016), forcing emergency blowers.

## Empirical correlation (the stretch target)

Fitted zero-power natural-circulation flow:

```
m_dot = ( 5.53 * dT + 3.75 * V_w^2 ) ^ (1/1.8)        [kg/min]
   dT  = T_inlet - T_outdoor   [K or degC]
   V_w = wind speed            [m/s]
```

Derived from: stack pressure P_s = ρ_out·g·H·(T_in−T_out)/T_in, wind pressure ΔP_w =
C_w·ρ_out·V_w²/2, balanced against turbulent friction loss (Blasius, exponent n=1.8).
Fit quality: R² = 0.87 (in-sample) / 0.93 (blind out-of-sample); RMSE ≈ 0.7 kg/min ≈ measurement
uncertainty.

## Scoring intent

- **Required gate:** get the **sign** right (colder → more flow).
- **Good:** order-of-magnitude of the effect (~20–25% flow swing across the ambient range).
- **Stretch:** reproduce the correlation's structure (stack term linear in ΔT, wind term in V²).
