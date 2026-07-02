# Curation protocol — build an input pack from the raw report

You are a CURATOR, not a modeler. In `source/report_full_text.txt` is the full text of a
test-facility report. Your job: extract a self-contained input pack (`pack_v2/`) that a modeling
engineer could use to PREDICT the facility's behavior — without revealing any measured outcome.

## Extract (design/description material ONLY):
- Facility geometry & scaling (report §1.4, §3): dimensions, counts, materials, configuration.
- Instrumentation locations (§4.2): where quantities are measured (locations/types only).
- Heater system & test-case definitions (§4.3, §6.4, §7 run definitions): powers, profiles,
  configurations, ambient conditions — the CONTROLLED inputs of the baseline test (~82 kWe,
  linear profile, natural circulation, dual chimney) and the accident decay-heat scenario.
- Material properties stated in the report (emissivities, insulation conductivities).

## STRICTLY FORBIDDEN in the pack — measured OUTCOMES, including:
any measured mass flow rate, any measured gas/wall/plate temperature from testing, measured
pressure drops, thermal efficiency or thermal (removed) power values, radiative/convective flux
measurements, any number from results Tables 29–51 or results §5–§7 outcome text, and any
RELAP5/CFD model result. Design-basis values (e.g. scaled duty targets in §1.4 Table 5) are
allowed — they are inputs, not measurements.

## Output format
Write pack_v2/01_geometry.md, 02_materials.md, 03_instrumentation.md, 04_conditions.md in your
own words with all numeric values you extracted, each traceable (note the report section it came
from). Completeness matters: a modeler must be able to compute flow areas, heights, emissivities,
heat input. When done, write pack_v2/CURATION_STATEMENT.md declaring you included no measured
outcomes.
