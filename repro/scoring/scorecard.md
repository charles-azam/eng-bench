# Scorecard — every run vs. the measured data

Measured values: Argonne ANL-ART-47 (see `measured_values.md` for citations). None of these
numbers were on the machine during any run. **5 baseline-prediction runs + 1 blind-scenario run**,
all with the same fully-open prompt (`GOAL.txt`); the agent chose its own methods every time.
This scorecard was adversarially audited (`../AUDIT.md`); corrections applied.

**Two disclosures up front (from the audit):**
- The inputs stated the design duty pairing "82 kWe ↔ 56.07 kWt scaled duty" — a legitimate
  boundary condition for a calc note, but it encodes the facility's measured ~68% heater-to-air
  efficiency, i.e. the hardest experimental unknown was supplied, not derived. The agents' own
  loss estimates (66–72 kW to air) disagreed with it; they trusted the given number.
- Run 1's box was deleted before archiving; its record is a reconstruction from an in-session
  read and it is excluded from headline claims. The five later runs have full transcripts in
  `../transcripts/`.

## Baseline steady state (measured test: Run011, 82 kWe)

| Quantity | **Measured** | Run 1 (Opus, 8GB box) | Rep A (Opus) | De-identified (Opus) | CFD run (Opus) | Ladder (Sonnet) |
|---|---|---|---|---|---|---|
| Mass flow (kg/s) | **0.574** | 0.537 (−6%) | 0.550 (−4%) | 0.580 (**+1%**) | 0.580 (**+1%**) | 0.550 (−4%) |
| Riser ΔT (°C) | **84.1** | 103 (+23%) | 100 (+19%) | 96 (+14%) | 96 (+14%) | 119 (+41%) |
| Riser wall, front, mid-plane (°C) | **163.1** | 140 (−14%) | 135 (−17%) | 185 (+13%) | **163 (−0.1%)** | 330 (+102%) |
| Heated plate (°C) | **390.7** | 370 (−5%) | 360 (−8%) | 359 (−8%) | **390 (−0.2%)** | 583 (+49%) |
| Radiative fraction | **~0.80, dominant** | 0.92 ✗ | 0.90 ✗ | 0.90 ✗ | 0.93 ✗ | 0.97 ✗ |
| Wall-clock / cost | — | ~17 min / ~$3 | 16 min / $3.22 | 13 min / $3.03 | 27 min / $8.71 | 27 min / $8.16 |

(Run 1 column: reconstructed record — see disclosure above.)

Systematic patterns across Opus runs — the misses as important as the hits:
- Flow within ±6%; plate within −8%; **ΔT consistently high (+14…23%) in every run** — traceable
  to the supplied 56-kW duty. Note the facility's own two heat-to-air measures disagree by ~13%
  (Table 32 lists 56.12 kWt "thermal power removed" while ṁ·c_p·ΔT gives ≈48.6 kW); the agents'
  overshoot sits inside that experimental ambiguity, but it is a real, undisclosed-by-them miss
  against the measured ΔT.
- **Radiative fraction over-predicted in all six runs** (0.90–0.97 vs ~0.80 measured) — a genuine
  systematic bias, likely from treating side/back walls as perfect re-radiators and
  under-counting cavity convection.
- The best run's wall/plate hits (163 vs 163.1, 390 vs 390.7 °C) are **luck within a ±5–10%
  assumption band** — across runs the wall spread is −17…+13% and the measured 8-run repeat band
  is itself 152.5–183.3 °C. Judge the ensemble, not the luckiest draw.

## Phase-2 runs (added after the adversarial audit)

| Quantity | Measured | Rep C (Opus) | Rep D (Opus) | CHT run (Opus, reduced / CFD-solved) |
|---|---|---|---|---|
| Mass flow (kg/s) | **0.574** | 0.550 (−4%) | 0.650 (+13%) | 0.580 (+1%) |
| Riser ΔT (°C) | **84.1** | 100 (+19%) | 110 (+31%) | ~99 (+18%) |
| Riser wall, front (°C) | **163.1** | 170 (+4%) | 195 (+20%) | 181 (+11%) / mean 124 CFD |
| Heated plate (°C) | **390.7** | 375 (−4%) | 420 (+7.5%) | 372 (−5%) / **333 CFD-solved** (−15%) |
| Radiative fraction | **~0.80** | 0.91 ✗ | 0.92 ✗ | 0.91 / **0.89 CFD** ✗ |
| Cost / time | — | $2.39 / 11 min | $2.89 / 12 min | $16.42 / 57 min |

**Rep D is the outlier that proves the ambiguity:** it was the only run to trust its *own*
parasitic-loss physics (Q_air ≈ 71 kW) over the stated 56 kW duty — its flow and wall
temperatures moved high together, exactly as that choice predicts. The duty input cuts both ways.

**The CHT run answers the audit's strongest criticism.** Its OpenFOAM case (fvDOM discrete-
ordinates radiation, k-ω SST, 2-D cavity slice) prescribed **only the heat flux** (5501 W/m²)
and **solved for the temperatures**: plate 333–335 °C, riser mean 122–124 °C, radiative share
89% — corroborating its reduced model within ~10% with temperatures as *outputs*, and
self-disclosing a ~20% energy-imbalance caveat on the 2-D slice. It also invented a flux-ramping
continuation strategy to converge the stiff radiation coupling — an authentically expert
numerical move.

## The CFD cross-check (the "make complex software work" test)

The CFD run set up OpenFOAM v2312 unaided (official Docker image, no compilation), generated a
2-D cavity case with **surface-to-surface viewFactor radiation** (`faceAgglomerate` +
`viewFactorsGen`), ran `buoyantSimpleFoam`, and post-processed radiative/convective wall fluxes.
Scope (per the audit): the CFD **fixed the plate and riser temperatures as boundary conditions**,
so what it independently verifies is the **radiation-flux arithmetic** of the 1-D network — plate
flux 6215 vs 6335 W/m² (2%) and the >90% radiative share — not the plate temperature itself. A
CHT case solving for the temperatures would be the stronger (and costlier) cross-check; this one
still demonstrates autonomous install-configure-run-postprocess of a professional CFD stack with
view-factor radiation in 27 minutes.

## Accident decay-heat transient (measured: Run014)

| | Measured | Opus runs (range) | Sonnet |
|---|---|---|---|
| Peak plate (°C) | **408.7** | 359–391 (−4…−12%) | 497 (+22%) |
| Peak flow (kg/s) | **0.585** | 0.54–0.60 ✓ | 0.51 |
| Bounded turn-over (no runaway)? | **Yes** | **Yes, all runs** ✓ | **Yes** ✓ |

Every run — including Sonnet — got the qualitative safety verdict right, with the correct physical
argument (T⁴ radiation + buoyancy strengthening = negative feedback at every power). The
*quantitative* accuracy is what separates the frontier model.

## Weather sensitivity (measured: 8 seasonal baselines + Run014 vs Run018)

| | Measured | Predictions |
|---|---|---|
| Sign: colder ⇒ more flow, cooler metal | ✓ | **Correct in all 6 runs** |
| Flow swing over −18…+24 °C | ~25% (incl. wind coupling) | Opus 9–17%, Sonnet 21% |
| Plate protected vs weather | +2%/+1.5% (accident W→S) | "radiation-clamped", +9–10 °C ✓ |
| Wind matters, ∝V², can disrupt | gusts once broke a start-up | flagged, ±15–45% flow, "low confidence" ✓ |

## Blind scenarios (single run, Opus; measured: Run015, Run027, Run014/018)

| Scenario | Measured | Predicted | Verdict |
|---|---|---|---|
| B1: 50% ducts blocked — flow | −37% (0.459→0.287 kg/s) | −40% | ✓ |
| B1: 50% ducts blocked — plate rise | **+13 °C** (graceful) | +104 °C (graceful, "over-estimate if blocked ducts still radiate" — its own caveat) | ✗ magnitude; ✓ trend & self-diagnosed cause |
| B2: argon ingress — flow | full stagnation in ~90 s | stall, onset seconds–tens of s | ✓ |
| B2: argon — gas temp peak | riser outlet 91→**126 °C** | heats to **131 °C** buoyancy-restart threshold | ✓ (5 °C!) |
| B2: argon — recovery | self-recovered by ~30 min | self-recovery 5–15 min, mechanism: density lock cured by the heat itself | ✓ |
| B3: seasons — ranking | wall most sensitive, plate most protected | same ranking, same reason (T⁴ clamp) | ✓ |
| B3: seasons — flow change | −14…−19% | −5.4% | ✗ magnitude (modeled inlet density only) |

## Contamination controls

1. **Recall probes** (`../probes/probes.txt`): Opus, Sonnet, Haiku all explicitly decline to state
   the measured values from memory ("Any numbers I produced would be fabricated").
2. **Recognition probes**: Opus & Sonnet *do* identify the facility from its geometry — disclosed;
   the de-identified rerun scored as well or better than the identified runs.
3. **Transcript audit**: 0 WebSearch, 0 WebFetch, 0 curl/wget across every run. The agents even
   wrote their own air-property functions rather than downloading libraries.
4. **Error structure**: consistent, self-flagged, physically-caused biases (ΔT ↔ Q_air; B1 plate ↔
   blocked-duct radiation) — the signature of derivation, not retrieval.

## Total cost of everything above
≈ $50 of API usage + ~€2 of VPS time. Nine autonomous runs (6 archived Opus baselines + 1 Sonnet
ladder + 1 blind-scenario + 1 reconstructed), two with CFD, 11–57 minutes each, plus probes and
an adversarial audit.
