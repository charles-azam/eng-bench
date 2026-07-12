# Electrical boundary conditions

Use linear interpolation between tabulated transient points. Do not extrapolate the accident curve
beyond its final row.

## Case B0: baseline steady state

- Uniform axial heater profile.
- Total electric heater input: 82 kWe, held to steady state.
- Natural circulation; both vertical stacks open; baseline geometry.
- Outdoor air: approximately 2 C; building/inlet air: approximately 20 C; low wind.

The net thermal duty reaching the cavity and loop is **not supplied**. Account for heat stored in and
lost through the heater/structure and estimate that duty with uncertainty.

## Case A: accident-shaped electric input through peak

Start from a converged state at the first electrical input in
`inputs/accident_electric_power.csv`, then follow that table through 84.85 h. The table is a validated
tabulation of the source's intended electrical command shape because the source omitted the tenth
coefficient of its polynomial. Predict the response only through the final row.

The experiment exercised the rising portion through its peak. Do not assume that a post-peak decline
was experimentally observed. Report the plate temperature, flow, and gas temperature rise at the
84.85 h endpoint and judge whether the response remains bounded over that interval.

## Case W: weather sensitivity

Repeat B0 over outdoor temperatures from -18 C to +24 C and wind speeds from 0 to 11 m/s. Keep the
building/inlet reference at 20 C unless your model explicitly couples it to outdoor conditions.
Report endpoint mass flow and plate temperature in the note as unscored sensitivity outputs. The
required categorical output is the direction of the outdoor-temperature effect. Discuss wind as an
unscored, direction-dependent sensitivity rather than assuming the historical tests were controlled
zero-wind experiments.

Provenance: ANL-ART-47 Sections 4.3, 6.4.1, and 7.1. The electrical curve shape is audited in the
human-only protocol record; it contains no measured thermal-duty or response target.
