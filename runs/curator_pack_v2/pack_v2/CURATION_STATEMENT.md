# Curation Statement — NSTF Input Pack (pack_v2)

**Source:** ANL-ART-47, *Final Project Report on RCCS Testing with the Air-based NSTF*
(Argonne National Laboratory, August 2016), full text in `source/report_full_text.txt`.

**Purpose:** This pack extracts only *design, description, material-property, instrumentation-
location, and controlled-input* material so that a modeling engineer can predict the facility's
thermal-hydraulic behavior. It deliberately omits every measured test outcome.

## Contents
- `01_geometry.md` — facility geometry & scaling (§1.3, §1.4, §3, §8.3.2; Tables 2–5, 8, 10, 56, 57).
- `02_materials.md` — structural materials, emissivities, insulation specs, reference fluid
  properties (§3.1–§3.4, §4.2.2, §6.4.3; Tables 9, 46, 47).
- `03_instrumentation.md` — DAQ, sensor types/ranges, and measurement *locations* (§4.1–§4.2;
  Tables 11–19).
- `04_conditions.md` — heater system/control and controlled test-case definitions incl. the
  ~82 kWe baseline and the accident decay-heat scenario (§3.3.5, §4.3, §6.4, §7 run definitions;
  Tables 25, 26).

## Declaration — no measured outcomes included
I confirm this pack contains **no measured test outcomes**. Specifically excluded:
- No measured mass/system flow rates.
- No measured gas, wall, plate, riser, or ceramic-heater temperatures from testing.
- No measured pressure drops (riser or chimney ΔP).
- No thermal efficiency or thermal (removed-power, kWt) measurements.
- No measured radiative/convective heat-flux values.
- No values from results Tables 29–51 (e.g. Tables 29, 30, 32, 34–40, 43–45, 50, 51), nor from
  results narrative in §5 and §7 outcome text.
- No RELAP5-3D or STAR-CCM+/CFD model results (including CFD-derived view factors from §6.4.3).

## Judgment calls (allowed inputs that could be mistaken for outcomes)
- **Table 5 / Table 25 scaled duty targets** (decay power, heat flux, ΔT, system flow) are included:
  the task explicitly permits these as design-basis *inputs*, not measurements.
- **Heated-plate emissivity 0.78–0.79** (§3.3.3) is included as a pre-test *material/surface property*
  (a radiation modeling input), not a facility-performance result.
- **Heat-flux-sensor Kradiative sensitivities** (Table 13) are included as per-sensor *calibration
  constants* accompanying the location list, not as measured fluxes.
- **Reference air/argon physical properties** (Tables 46, 47) are included as standard *published
  fluid properties* (working-fluid inputs), not facility measurements — flagged as such in the file.
- **Ambient/meteorological conditions** (outdoor temperature envelope −18.1 to +32.1 °C from §1.5;
  seasonal averages for the accident runs from §7.3.2 prose) are included as external *boundary-
  condition inputs*. These were taken from narrative text, not from the forbidden weather results
  tables (Tables 30, 36). Specific per-run measured weather from those tables was not copied.

All numeric values carry a source section/table reference for traceability.
