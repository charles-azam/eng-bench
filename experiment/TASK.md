# TASK — Calculation note: passive reactor cavity cooling

You are an engineer. Produce a **calculation note** for a passive **Reactor Cavity Cooling
System (RCCS)** — the system that removes a high-temperature reactor's decay heat after shutdown
with **no pumps**: a hot vessel wall transfers heat across an air-filled cavity to a bank of
steel riser ducts, and the air in those ducts warms, rises by buoyancy, and carries the heat up
a chimney by natural circulation.

Everything you need is in **`inputs/`** — facility geometry, materials, operating conditions, and
where each quantity is measured.

## What we want

For the operating cases in `inputs/04_boundary_conditions_and_test_cases.md`, predict and report
— with your reasoning and assumptions:

- the natural-circulation air **mass flow rate**;
- the air **temperature rise** across the riser ducts;
- the **riser duct wall temperature** and the **heated-wall (mock-vessel) temperature**;
- how the removed heat splits between **radiation and convection**;
- for the accident (decay-heat) case: the **peak temperatures**, and whether the vessel **stays
  below a safe limit** (does the temperature level off, or run away?);
- how performance changes with the **outdoor ambient conditions** (air temperature, wind).

State your confidence in each number and which assumption is the most uncertain.

## How to work

- You choose the methods and tools. Build from physics and the given conditions.
- Put the calculation note and all working files (scripts, models, intermediate results) in
  **`output/`**.

## Rules

- Do **not** look up this facility's published test reports or any pre-made model of it. (They
  exist online, and in `refs/` and `sources/` — all off-limits.) Predict the numbers yourself.
- Cite the source of any empirical correlation you use.
