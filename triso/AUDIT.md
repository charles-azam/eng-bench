# TRISO Adversarial Audit (fresh-context Opus, 2026-07-03) — published unedited, corrections applied

**Verdict: SUPPORTED WITH CORRECTIONS.** Foundation honest: no input leakage (independently
re-grepped), all five model scripts re-run by the auditor and reproduce every headline number
from real physics chains (nothing hardcoded), zero-failure calls and temperature ranking real,
Cs-137 bias story source-verified. Required corrections (ALL APPLIED to SCORECARD.md):

1. **"Two runs invented a SiC-degradation mechanism" was half false.** Only Fable CODED a
   mechanism (ad-hoc Arrhenius thinning anchored to the ~2200 °C TRISO destruction point —
   domain knowledge from outside the annex, disclosed; it overshot Case B ×60). Opus C's code
   contains NO degradation model (predicts ~0 failures everywhere); its "0–5" for Case B was a
   self-described low-confidence *judgment band* in prose, not a calibrated model. "Brackets
   exactly" oversold a wide band whose upper edge coincides with the measured 5, while the same
   run missed A2 (0–2 vs 10–12) and C1 (0 vs 3).
2. **"~×2 at 1800 °C" was true only for A2**; Case B is ×3–12 high — though the source shows
   the professional codes also overpredicted Case B specifically ("reduced to about a factor of
   10 at the end", line 25137), so the tracking claim survives case-by-case.
3. **Cherry-pick found and fixed:** Opus B and Sonnet were omitted from the release tables.
   Sonnet's A1 Cs (2.4e-5) UNDER-predicts — the one counter-example to the "always high at
   1600 °C" narrative. Now included: the bias is a tendency across runs, not a law.
4. **"Gate-checked" reworded**: manual curation + independent re-grep (mine and the auditor's);
   no automated gate artifact exists.
5. **Failure-count circularity now disclosed in the scorecard**: the original benchmark codes
   never predicted failure counts (counts were imposed as boundary conditions in their
   postcalculations); the agents attempted a harder task than the reference codes.
6. Also: A2 burnup used inconsistently across runs (10.2 vs 10.6 %FIMA, both in pack) — noted;
   sister-sphere batch-difference explanation labeled a hypothesis; N=1 per model config noted.
