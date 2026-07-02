# TASK — Predict a real reactor's loss-of-forced-cooling test

You are a reactor physicist with this whole machine (8 cores, 30 GB RAM, large disk) and as much
compute time as you need — long downloads and long Monte Carlo runs are expected and welcome.

The HTTR (High Temperature Engineering Test Reactor, JAEA, Japan) is a 30 MWt prismatic-core
high-temperature gas-cooled reactor: graphite-moderated, helium-cooled, pin-in-block fuel,
~950 °C outlet capability. In its loss-of-forced-cooling (LOFC) test campaign, operators tripped
ALL helium gas circulators while the reactor was at 9 MWt (30% power) — WITHOUT scram, control
rods frozen in position — with the vessel cooling system (VCS) running.

## Predict, from physics

1. What happens to fission power in the first minutes after the trip, and why.
2. Whether and WHEN the reactor spontaneously returns to criticality (recriticality time, in
   hours), and the physical mechanism governing that timing.
3. The approximate power level the reactor stabilizes at afterwards.
4. The fuel and vessel temperature trend — bounded or runaway, with the reasoning.

## Method (yours to choose, but note)

A serious answer computes the core's temperature feedback rather than assuming it:
- Install OpenMC and a nuclear data library (downloads are GB-scale; that is fine — this
  machine and this run are meant for long computations).
- Build a defensible HTTR-like core model from PUBLIC DESIGN DATA (geometry, enrichment zoning,
  materials — design publications are allowed sources).
- Compute k_eff and the isothermal temperature coefficient at several temperatures (long MC
  runs, low statistical uncertainty — take the time).
- Couple: point kinetics + decay heat + a lumped core thermal model (graphite heat capacity is
  the star of this show) + the VCS as the ultimate heat sink.

## HARD RULES

- You MAY search the web for: HTTR DESIGN data (core geometry, fuel/block specs, compositions,
  enrichments, thermal properties), software, and nuclear data.
- You MUST NOT search for, open, or use: any LOFC / loss-of-forced-cooling TEST RESULTS (power
  traces, measured recriticality times, measured temperatures), any paper or page whose title
  or abstract indicates it reports those tests, or benchmark comparisons of them. If a design
  source you open turns out to contain LOFC results, stop reading it and log the incident.
- Log every source consulted in output/sources.md (URL + what you took from it).
- Checkpoint your progress every few steps in output/PROGRESS.md (what's done, what's running,
  ETA) — this run may take many hours and must be resumable by inspection.

Deliver output/calculation_note.md with the four predictions, your computed coefficients
(with statistical uncertainties), assumptions, and confidence levels.
