# Independent Adversarial Audit

> This audit was produced by a fresh-context AI agent (Claude Opus) that saw none of the
> reasoning that produced the runs or the scorecard. Its charter: "try to find why the claim is
> WRONG, overstated, or not supported." It read every artifact, grepped the inputs for leaked
> values, diffed the model code across runs, executed the best run's model itself, and inspected
> the OpenFOAM case files. Published unedited. The wording corrections it required have been
> applied to the scorecard and README; the original findings stand below for transparency.

**Verdict: SUPPORTED WITH CORRECTIONS.**

"The core phenomenon is real and reproducible from the artifacts: genuinely derived physics
models (verified by execution), no measured values in the inputs or code, honest disclosure of
most failures, and impressive flow/plate/stability predictions at trivial cost. But the headline
claim as worded oversells the best run's two luckiest numbers, hides a +14% ΔT miss inside
'0–8%', omits that the decisive heat-duty input encoded a measured quantity, and rests its 'no
lookup' guarantee on transcripts the repo does not contain."

## Key findings (all now addressed)

1. **Input leakage — none direct** (grep of all input packs for every held-out value: zero hits),
   **but one structural leak**: the inputs' "82 kWe corresponds to the scaled 56.07 kWt duty"
   pairing encodes the facility's measured ~68% heater-to-air efficiency — the single hardest
   experimental unknown was effectively supplied. The agents' own parasitic-loss estimates
   (66–72 kW to air) disagreed with it; the runs that trusted the given number scored best.
   → Disclosed prominently in README and article.
2. **Scores verified**: "I ran run_cfd/rccs_model.py myself — it reproduces the note's headline
   numbers exactly (0.577 kg/s, 96.2 K, 162.9 °C, 390.5 °C, 92.7% radiative) from geometry +
   textbook correlations." No fabrication, no misquotes found.
3. **Suspicious precision (163 vs 163.1 °C, 390 vs 390.7 °C): not leakage — luck.** Deterministic
   outputs of code containing no measured values, but landing within 0.2% is coincidence inside a
   self-declared ±5–10% assumption band, against one run of an 8-run series spanning
   152.5–183.3 °C / 382.5–397.5 °C. → No longer presented as headline accuracy.
4. **CFD cross-check is narrower than claimed**: the OpenFOAM case fixed plate/riser temperatures
   as boundary conditions; it independently verifies the radiation-flux arithmetic (within 2%),
   not the plate temperature itself. → Reworded.
5. **Radiative fraction overpredicted in every run** (0.90–0.97 vs measured ~0.80). → Marked as
   a systematic miss.
6. **Run 1's artifacts were destroyed** (VPS deleted before archiving); its record is a
   reconstruction. → Disclosed; Run 1 excluded from headline claims.
7. **Transcripts were not published** and WebSearch/WebFetch were enabled in the tool whitelist.
   → All five surviving run transcripts now in `transcripts/` (grep them yourself:
   `grep -c '"name":"WebSearch"' transcripts/*.log` → 0 in all).
8. **ΔT excuse was partly circular**; the defensible framing is that the facility's own two
   heat-to-air measures disagree by ~13% (56.12 kWt "thermal power removed" vs 48.6 kW ṁ·c_p·ΔT),
   and the agents' +14–23% ΔT overshoot sits inside that experimental ambiguity. → Reframed.
9. Residual caveats that cannot be fully closed and are simply disclosed: the input packs were
   curated by the same party holding the answers (third-party curation would be stronger); the
   models recognize the facility from geometry alone, and refusal-based recall probes cannot
   strictly exclude latent memory steering assumption choices — the run-to-run spread of those
   choices (and the misses) is the real defense.
