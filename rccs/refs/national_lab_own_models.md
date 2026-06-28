# ⛔ HELD-OUT — Argonne's Own Models (secondary cross-check only)

> These are **models, not measurements.** They are kept here so the verifier can see how a
> national lab tackled the same problem and what accuracy it reached. The builder agent must
> **not** read or copy these — predicting the *measurement* from physics is the task. If a
> submission matches these model numbers more closely than the measurement, or reuses ANL's exact
> mesh/turbulence/correlation choices, flag it.

## RELAP5-3D (1-D system thermal-hydraulics)

- Modeled the integral loop: air mass flow rate and riser air temperature rise; ambient handled
  via "virtual volumes" (stack effect) and an imposed inlet–outlet ΔP (wind).
- Calibrated to **one** test (Run022); validated against Run011, Run020, Run024.
- **Accuracy: mass-flow average absolute error < 5%; riser ΔT error < 6%**, over outdoor T
  −22 → +33 °C and wind 0–8.5 m/s.
- With wind+temperature modeled, Run022 flow error dropped to **< 2%** (≈ measurement
  uncertainty).
- Cautionary baseline: early *pre-construction* RELAP models (before as-built geometry/losses/
  weather were known) **over-predicted flow by 160% and surface temps by 150%** — i.e. getting
  this right depends entirely on honest geometry, losses, and ambient handling. A good warning
  for the builder about error budgets.

## STAR-CCM+ (3-D CFD), v10.06

- 3-D, steady-state, conjugate heat transfer (cavity air ↔ riser ducts ↔ main air), **radiation
  via ray-traced surface-to-surface view factors**, convection resolved.
- BCs: uniform heat flux on the heated East wall, adiabatic other walls; run both forced (inlet
  flow fixed to experiment) and **a-priori natural-convection** (only ambient T + heat flux +
  geometry given — the honest benchmark).
- **Accuracy: bulk flow predicted within ~10%** in a-priori natural-convection cases.
- Turbulence findings (useful guidance, not answers): Xu k-ε and SST k-ω over-predicted turbulent
  diffusion on coarse wall meshes → under-predicted local wall temps; **Wolfstein** model did
  better at similar cost; **wall-mesh refinement mattered more than turbulence-model choice**.
  Recommended: Wolfstein + coarse mesh for scoping, low-Re k-ε + refined wall mesh for local temps.
- Insulation conductivity alone under-estimated heat loss; thermal imaging of external surfaces
  was needed to set the loss distribution → a real lesson about parasitic losses.
- Adding the weather pressure BC improved the low-power flow prediction from −8.7% to −1.7%.

## What "good" looks like for the builder

A from-scratch reduced-order model landing within ~15% of the measurement, and an OpenFOAM CFD
landing within ~10%, would **match the national lab's own tools** — which is exactly the
David-vs-Goliath result the project is after. The bar is set by these numbers, but the builder
must reach it independently.
