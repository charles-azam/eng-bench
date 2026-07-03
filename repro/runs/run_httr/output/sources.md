# Sources consulted

Rule: DESIGN DATA, SOFTWARE, and NUCLEAR DATA only. No LOFC / loss-of-forced-cooling
test results (power traces, measured recriticality times/temperatures). If a source turns out
to contain such results, reading stops and the incident is logged here.

## Software
- OpenMC 0.15.3 (conda-forge). Monte Carlo neutron transport. https://openmc.org , https://docs.openmc.org

## Nuclear data
- ENDF/B-VIII.0 HDF5 library for OpenMC (LANL Lib80x / ENDF80SaB2 conversion). Incident neutron at
  0.1/250/293.6/600/900/1200/2500 K + graphite thermal scattering S(a,b).
  Direct: https://anl.box.com/shared/static/uhbxlrx7hvxqw27psymfbhi7bx7s6u6a.xz
  (referenced from https://openmc.org/data/ and https://github.com/openmc-dev/data). Used for: all cross sections.

## HTTR design data
- IAEA coated-particle fuels paper "Fabrication of HTTR First Loading Fuel" (Kato/Sawa et al., XA0100873),
  https://www.osti.gov/etdeweb/servlets/purl/20158164 — TRISO layer thicknesses & densities (Table 1),
  compact 26 mm OD / 39 mm h, 14 compacts/rod, 12 enrichments (3.4–9.9 wt%), 31/33 rods/block, block 360 mm AF x 580 mm.
- INL "Deterministic Modeling of the High Temperature Test Reactor" (INL/EXT, benchmark design compilation),
  https://inldigitallibrary.inl.gov/sites/sti/sti/4633194.pdf — full core geometry (Tables 1–6), enrichment zoning
  (Table 2), BP B4C 2.0–2.5 wt% nat-B, graphite grades/densities/impurities (IG-110, PGX), reflector thickness,
  packing fraction ~30 vol%, CR/RSS specs. AUTHORITATIVE primary compilation.
- INL Virtual Test Bed HTTR reactor description, https://mooseframework.inl.gov/virtual_test_bed/htgr/httr/httr_reactor_description.html
  (cross-check; page fetch 403 but content mirrored in INL modeling report).
- JAEA official HTTR outline (O-arai), https://www.jaea.go.jp/04/o-arai/nhc/en/faq/httr.html — 30 MW, 395/850/950 °C,
  4 MPa, 2.9 m x 2.3 m core, 2.5 MW/m3, RPV 2.25Cr-1Mo steel.
- Takizuka "Reactor technology development under the HTTR project", https://www.ne.titech.ac.jp/archive/coe21/eng/events/ines1/pdf/87_takizuka.pdf
  — He flow 12.4 kg/s (rated, 850 °C) / 10.2 kg/s (high-temp, 950 °C); main cooling removes ~97% of power.
- VCS design heat removal ~0.6 MW (600 kW) at rated operation (RPV heat loss), corroborated via
  INIS "Design and fabrication of the reactor Vessel Cooling System (VCS) in HTTR" https://inis.iaea.org/records/h75a9-kty70
  and RCCS/VCS literature. VCS = water cooling panels around RPV, radiation + natural convection, panels kept <90 °C.
- IG-110 nuclear graphite impurity (equivalent boron content): High-Purity class, EBC < 2 ppm; ash ~12.7 ppm
  (Sci. papers on IG-110 impurity). HTTR design spec lists IG-110 <1 ppm boron-equiv (fuel block/sleeve/refl),
  PGX permanent reflector <5 ppm boron-equiv, fuel matrix <1.2 ppm, CFP <3 ppm.

## Incidents
- Search results repeatedly surfaced LOFC/"no forced cooling" test papers (e.g. Tandfonline
  "Experiments and validation analyses of HTTR on loss of forced cooling under 30% reactor power";
  ScienceDirect "Passive heat removal by VCS during no forced cooling accidents"). These were NOT opened,
  per the hard rule. Only steady-state DESIGN data was taken from opened sources.
