# TASK — Calculation note: TRISO particle failure under accident heating

You are an engineer. `inputs/` describes TRISO-coated fuel particles (a UO₂ kernel inside
buffer / inner-PyC / SiC / outer-PyC layers), the fuel elements that contain them (spheres of
16,400 particles; compacts of ~1,600), the irradiation each element experienced, and the
accident-heating schedule each was then subjected to in a furnace. A material-property annex is
provided — it is deliberately complete.

For each heating case in `inputs/02_cases.md`, predict — with your reasoning, assumptions, and
a confidence level per number:
1. how many particles fail during the heating (out of the element's population), and when
   (onset time, or which phase of a staged schedule);
2. the final fractional release of Kr-85 and Cs-137 from the element;
3. the ranking: which case suffers most and why (temperature and burnup sensitivities).

State which assumption is most uncertain. Work fully offline — build from physics and the given
inputs only; do not look up these experiments' published results. Cite the correlations you use.
Put the calculation note (output/calculation_note.md) and all working files in output/.
