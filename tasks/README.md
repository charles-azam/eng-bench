# Frozen task-pack assembly map

These directories are source material for two isolated agent-visible packs. Do not mount this
README, `protocol/`, source reports, measurements, evaluator code, or old runs.

## `nstf_blind_derive_duty`

Assemble a fresh pack as:

```text
TASK.md                         <- tasks/nstf_blind_derive_duty/TASK.md
inputs/01_geometry.md           <- tasks/nstf_common/inputs/01_geometry.md
inputs/02_materials.md          <- tasks/nstf_common/inputs/02_materials.md
inputs/03_measurement_locations.md
inputs/04_electrical_cases.md
inputs/accident_electric_power.csv
output/                         <- empty writable directory
```

The last three input files come from the corresponding paths under `tasks/nstf_common/inputs/`.

## `nstf_supplied_duty`

Use the same common inputs, replace `TASK.md` with
`tasks/nstf_supplied_duty/TASK.md`, and add
`tasks/nstf_supplied_duty/inputs/05_supplied_thermal_duty.csv` under `inputs/`.

Before hashing any assembled pack, run `protocol/validate_task_packs.sh`. The final freeze manifest
must hash the assembled copies, not only these source paths.
