# Inputs 01 — Particles and fuel elements

Geometry, composition and density data for the coated particles and the fuel elements used by
the prediction cases in `02_cases.md`. All values from the fuel/particle characterization of the
accident benchmark (LEU UO₂ TRISO). Layer thicknesses are given as mean ± standard deviation
of the as-fabricated batch.

## What a TRISO particle is (layer functions)

A TRISO particle is a small (~0.9 mm) sphere built up from a fissile kernel and four coating
layers. From the inside out:

- **UO₂ kernel** — the fuel; holds the fission-product inventory and is where fission gases and
  metallic fission products are born.
- **Buffer (porous PyC)** — a low-density pyrocarbon sponge that gives fission gases and CO a
  void volume to collect in (limiting internal pressure) and absorbs kernel swelling and recoil
  damage. It is mechanically weak and is conventionally treated as load-bearing-free.
- **Inner PyC (IPyC)** — a dense pyrocarbon layer that protects the SiC from corrosive fission
  products and, under irradiation, shrinks and puts the SiC into compression.
- **SiC** — the dense structural and primary diffusion barrier layer. It carries the internal
  gas pressure load and is the main retention barrier for metallic fission products (Cs, Sr, Ag).
  Its failure is the event that lets fission products escape a particle.
- **Outer PyC (OPyC)** — a second dense pyrocarbon layer that protects the SiC from the outside,
  puts it into additional compression under irradiation, and provides a bonding surface to the
  surrounding matrix.

## Coated-particle characteristics

Batches: HFR-P4 and HFR-K3 use particle batch EUO 2308; HFR-K6 uses batch EUO 2358–2365.
Kernel composition is LEU UO₂ in all cases.

| Parameter | HFR-P4 | HFR-K3 | HFR-K6 |
|---|---|---|---|
| Coated-particle batch | EUO 2308 | EUO 2308 | EUO 2358–2365 |
| Enrichment (U-235 wt%) | 9.82 | 9.82 | 10.6 |
| Kernel diameter (µm) | 497 ± 14.1 | 497 ± 14.1 | 508 ± 10.0 |
| Buffer thickness (µm) | 94 ± 10.3 | 94 ± 10.3 | 102 ± 11.5 |
| IPyC thickness (µm) | 41 ± 4.0 | 41 ± 4.0 | 39 ± 3.9 |
| SiC thickness (µm) | 36 ± 1.7 | 36 ± 1.7 | 36 ± 3.4 |
| OPyC thickness (µm) | 40 ± 2.2 | 40 ± 2.2 | 38 ± 3.5 |
| Kernel density (Mg/m³) | 10.81 | 10.81 | 10.72 |
| Buffer density (Mg/m³) | 1.00 | 1.00 | 1.02 |
| IPyC density (Mg/m³) | ~1.9 | ~1.9 | 1.92 ± 0.005 |
| SiC density (Mg/m³) | 3.20 | 3.20 | 3.20 |
| OPyC density (Mg/m³) | 1.88 | 1.88 | 1.92 |
| IPyC anisotropy BAF | 1.053 | 1.053 | 1.042 |
| OPyC anisotropy BAF | 1.019 | 1.019 | 1.023 |

(Source: fuel/particle characterization tables of the accident benchmark, TECDOC-1674 Table 10.2.)

## Fuel-element characteristics

- **Spheres (HFR-K3, HFR-K6):** graphite-matrix pebbles, 60 mm outer diameter, ~50 mm fuel-zone
  diameter, matrix graphite grade A3-3 / A3-27, matrix density ~1750 kg/m³.
- **Compacts (HFR-P4):** small cylindrical compacts, ~23–29 mm diameter × 32 mm length, fuel-zone
  diameter 20 mm, matrix graphite grade A3-27.

| Parameter | HFR-P4 (compact) | HFR-K3 (sphere) | HFR-K6 (sphere) |
|---|---|---|---|
| Fuel element type | Compact, LEU phase 1 | Sphere GLE-3, LEU phase 1 | Sphere GLE-4 (AVR 21) |
| Coated particles per element | 1631 | 16,350 (nominal 16,400) | 14,580 |
| Packing fraction (%) | 14.6 | 10.2 | 9.6 |
| Heavy-metal loading (g/element) | 1.018 | 10.22 | 9.4346 |
| U-235 content (g/element) | 0.10016 | 1.004 | 1.0 |

(Source: TECDOC-1674 Table 10.1.)

**Notes for the analyst**
- Use **16,400** as the round particle count for the spheres when converting a per-element release
  to a per-particle basis (16,350 is the exact characterization figure for HFR-K3; the two are
  used interchangeably in the benchmark). HFR-K6 spheres contain 14,580 particles.
- Use **1631** particles for the HFR-P4 compacts.
