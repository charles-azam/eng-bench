# ⛔ HELD-OUT REFERENCE DATA — off-limits to the builder

This directory holds the **measured experimental results** (and the original lab's own model
outputs). It is the **answer key**. It exists so that a **separate, independent checker** — an
agent we design later — can, after the builder has committed its calculation note:

- compare the predictions against the real measurements,
- confirm the builder did not look up or copy these results,
- review what the builder did, the problems it hit, and how it solved them.

**The builder agent must not read anything here**, nor in `../sources/`. It builds its prediction
only from `../inputs/`, `../TASK.md`, and physics.

| File | What it is |
|---|---|
| `measured_data.md` | The measured results (baseline values, radiation/convection split, accident transient, robustness points) |
| `weather_effect.md` | The measured ambient/weather sensitivity + the fitted correlation |
| `national_lab_own_models.md` | The lab's own RELAP5-3D / CFD results — a model, not the measurement; secondary cross-check only |

Provenance: all numbers trace to the source reports in `../sources/` (Argonne ANL-ART-47, 2016,
and a 2017 companion paper).
