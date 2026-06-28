# inputs/ — everything the builder may use

These four files are the **complete, sanctioned input** for the task. Build your model from these
plus first-principles physics. They contain geometry, materials, sensor locations, and boundary
conditions — **no measured results**.

| File | Contents |
|---|---|
| `01_facility_geometry.md` | Facility description, scaling, cavity/plate/riser/plenum/chimney dimensions, items given only in drawings |
| `02_materials_and_properties.md` | Emissivities, steel & insulation properties, air properties, the dominant-mode intuition |
| `03_instrumentation_map.md` | Where each quantity is measured (predict at those locations) |
| `04_boundary_conditions_and_test_cases.md` | Heat-input & ambient BCs for each case to predict; the scored quantities |

**Do not read `../refs/` or `../sources/`** — they hold the answers and the original reports.
See `../TASK.md` for the full brief and rules.
