# HTTR Adversarial Audit (fresh-context agent, 2026-07-03) — published unedited

Charter: prove the claims wrong. The auditor had the full run outputs, transcript,
pack, refs, and the capstone article's Problem-3 claims; it independently fetched the
INL primary source (OSTI 3013713). Corrections below are applied in SCORECARD.md and
the articles.

---

# ADVERSARIAL AUDIT — HTTR LOFC CAMPAIGN

**Auditor charter:** prove the claims wrong. Evidence: `httr/SCORECARD.md`, `httr/refs/measured_data.md`, `httr/pack/`, `runs/run_httr/`, `repro/transcripts/httr.run.log` (2.36 MB, parsed event-by-event), `articles/article3_capstone.md`, plus independent fetch of the INL primary source (OSTI 3013713).

## VERDICT: SUPPORTED WITH CORRECTIONS

The experiment's **integrity core is genuine and survives the strongest checks I could construct**: no LOFC test result entered the agent's context (verified by regex sweep of every tool result in the transcript, not just the agent's own log); the OpenMC computation is real and its numbers reproduce from the raw CSVs; the pre-registration of the conductance uncertainty is verifiably in-run and pre-results. However, the **headline claim — "the $23 agent beat the professional analysis" — is not supported as stated** (wrong quantity compared, nominal cherry-picked against its own median, and the winning number is nearly an echo of a memory-seeded input assumption), the "right mechanism" claim for recriticality is contradicted by the owner's own refs file (zero xenon anywhere in the agent's model), and the cost/turn figures are wrong.

---

## Finding 1 — Web compliance: VERIFIED (the claim holds)

**Claim** (SCORECARD.md:4–6): "compliance verified — every logged query/URL is design/software/nuclear-data; the agent logged and declined LOFC papers that surfaced."

**Evidence.** I extracted every tool call from the transcript. There were exactly **23 WebSearch/WebFetch calls**, all inside one design-data subagent (launched L82, all sub-calls captured in the log with `parent_tool_use_id`), plus Bash `curl` of Miniforge, the ENDF tarball, and two design PDFs (OSTI 20158164 fuel-fabrication; INL 4633194 deterministic-modeling). Every query/URL is design/software/nuclear-data. I then swept **all tool results** (including search snippets and pdftotext output) for `recritical|Takamatsu|power peak…hours|0.65 MW|650 kW|RELAP5|about 8 h`: **zero measured LOFC numbers entered the context**. LOFC paper *titles* did surface in three search results (transcript L173, L259, L264, L318 — including the Takamatsu 2014 title) and were never fetched; `sources.md:38–41` logs exactly this incident, truthfully. The finish session (init L1398) made zero web calls and its prompt re-imposed the ban (L1453). The IAEA TECDOC-1382 fetch (HTTR *start-up* benchmark — permitted) yielded no numeric physics ("I would need access to the actual readable text content", L258).

**Severity:** none. This — the check on which "the whole experiment is dead" — passes cleanly. One caveat feeds Finding 3 below.

## Finding 2 — "287 kW beat the professional code": NOT SUPPORTED as framed

**Claim** (SCORECARD.md:25 "✓✓ beat the professional code"; article L123–125: "The stabilized power: predicted 287 kW. Measured: ~300 kW. The national lab's post-hoc code predicted 650 kW — the $23 agent beat the professional analysis").

Three independent defects:

**(a) Quantity mismatch, verified from the primary source.** I fetched OSTI 3013713 myself. Exact text: *"The LOFC test showed a power peak approximately 8 hours after the onset of the LOFC, and the magnitude of the peak was less than 0.5 MW. Lu reports a recriticality that occurred at 7 hours and a magnitude of approximately 0.65 MW, which he reported as being 'about 0.35 MW higher' than the measured value."* Both the INL 0.65 MW and the "measured ~0.3 MW" are the **recriticality peak**. The agent's 287 kW is its **asymptotic stabilized level**, and the agent explicitly predicted the opposite of a peak (note L121: "a gentle, well-damped drift… **not a sharp power spike**") — while the measured trace *has* a peak followed by damped oscillations settling to a *lower* simmer (refs §3; the 30 MW analog settled at roughly half its peak). The measured **stabilized** power for the 2010 test is not in any open source (refs L90: "Exact stabilized % for the 9 MW test not text-quoted"). So "predicted 287 / measured ~300" compares the agent's floor to the experiment's peak. Also, "~300 kW measured" is an arithmetic inference (0.65 − 0.35), labeled MEDIUM-HIGH in refs L84 — the article states it as flat fact.

**(b) Nominal vs median.** The 287 kW "nominal" sits **below the P10 (312 kW) of the agent's own 400-sample band**; the band median is **575 kW** (`results.json`). Median-vs-measured-peak is +92% — statistically indistinguishable from INL's +117%. The nominal comes from a parameter corner: `analyze.py:78-80` sets nominal `Gcr=2000 W/K` while the sensitivity sampler draws `Gcr∈U(3000,12000)` (`analyze.py:98`) — the nominal isn't even inside its own sampled space — and `L0=Q0=0.3 MW` is the exact bottom edge of the sampled `U(0.3e6,0.9e6)`. Only the corner case "beats" INL.

**(c) The winning number is an input echo with a memory-seeded input.** By the model's own logic, stabilized power ≈ passive-removal capacity: P_stab (287 kW) ≈ L0 (0.3 MW), and across the band P_stab tracks L0 nearly 1:1 (312–826 kW for L0 0.3–0.9 MW). Where did 0.3 MW come from? The transcript's **first occurrence of "0.3 MW" anywhere is inside the agent's own search query** (L311: `HTTR vessel cooling system design heat removal "0.6 MW" OR "0.3 MW"…`). The search confirmed only the 0.6 MW *rated* figure; the halving to "0.3 MW at the 30%-power condition" was never confirmed by any source (`sources.md:30-32` cites only the 0.6 MW rating). HTTR LOFC results (published 2013–2014) are firmly inside the model's training data — the article itself calls recriticality "the famous result" — so a memory-anchored 0.3 MW cannot be excluded. To be fair: the agent designated the nominal *before* any comparison, and the scorer did not choose it post-hoc; but the write-up chose to headline it.

**Required correction:** retract "beat the professional code." Defensible replacement: "the agent's stabilized-power band (0.3–0.8 MW) is consistent with the measured recriticality peak (<0.5 MW, ≈0.3 MW inferred); its low-end nominal coincided with that peak value; INL's peak prediction was 2× high. The directly comparable measured stabilized level is not openly published, and the agent's number scales one-to-one with its assumed VCS capacity."

## Finding 3 — "Right mechanism": contradicted by the owner's own refs; zero xenon in the model

**Claim** (article L121–122: "Spontaneous recriticality: predicted, with the right mechanism (**graphite heat capacity governs everything**) ✓"; note L108/117: the miss is "thermal, not neutronic").

**Evidence.** `refs/measured_data.md:170-171` (the owner's own diligence): *"reactivity falls for 2–3 h (Doppler + moderator), then **rises with Xe-135 decay**, giving recriticality at 6–7 h (analysis) / ~8 h (test)."* The word **xenon appears zero times** in the entire 2.36 MB transcript, in `transient.py`, `analyze.py`, and the calculation note (grep count: 0). The agent's model has no I-135/Xe-135 chain at all; its only reactivity channel is temperature. Per the published analysis the owner himself compiled, a first-order driver of the 6–8 h timing is a neutronic effect the agent never modeled and never flagged. The ×7 miss is therefore at best *co*-explained by the pre-registered conductance; the agent's confident "thermal, not neutronic" is itself likely wrong, and the article's "right mechanism" checkmark and the "structured, self-flagged error" thesis are oversold — part of the error was structured and **un**-flagged.

**Severity:** high (it is the article's central interpretive thesis). **Correction:** score the mechanism as "half right — thermal relaxation captured; Xe-135 poisoning dynamics, which the published analyses name as the reactivity-recovery driver, absent and unflagged."

## Finding 4 — Pre-registration of the conductance uncertainty: VERIFIED

**Claim** (scorecard L32–35; article L129–131 "pre-registered exactly this dependency… in writing, before any comparison existed").

**Evidence.** True in-run and pre-results: transcript L1088 ("the recriticality *time* is governed mainly by the core↔reflector thermal coupling (Gcr)… which my grid didn't vary") and L1272 ("my nominal Gcr was too high. A geometry-based estimate… gives ~1–3 kW/K, not 6 kW/K. Let me lower the nominal… since this is the key uncertainty in the recriticality time") — both before the OpenMC sweep results existed; note L108, L117–118 state it in the deliverable. Integrity-positive extra: at 22:42 the agent's PROGRESS said its physical picture was "recriticality in a **FEW HOURS**" (L1430), yet it published its computed 1.0 h anyway — evidence *against* answer-shopping toward the famous 7–8 h (and evidence the model, not memory, produced the timing). The scorecard's admission that the band missed the truth (L36–37) is honest.

**Caveat:** the band itself is incoherent — the nominal parameters lie outside the sampled sensitivity space (Gcr 2 kW/K vs sampled 3–12 kW/K, despite the agent's own geometry estimate of 1–3 kW/K in the `analyze.py:73-75` comment). The "0.24–1.1 h band" is not a credible interval over the agent's actual beliefs; had the sampler included its own geometry-estimated 1–3 kW/K range, the band would extend past 1.1 h (though nowhere near 7 h).

## Finding 5 — Collapse row scored against an unlabeled proxy from a different test

**Claim** (scorecard row 1: measured "<1% within ~13 min" → "✓ mechanism & speed right"; article L119–120: "power collapses five orders of magnitude in minutes… Measured: yes, within minutes ✓").

**Evidence.** The "<1% in ~13 min" figure is the **2024, 30 MW test** (refs L42–46), which the refs explicitly warn to label ("this exact number is the 30 MW test, not the 2010 9 MW test. Label accordingly if used"). The scorecard presents it unlabeled as the measured value for the 2010 test, whose collapse time is not openly published (refs L35–36). "Five orders of magnitude… Measured: yes" is unsupported: the measured statement establishes two orders (<1%); five orders is model output only — and the agent's own nominal trace takes **29.4 min** to reach its 0.01 kW minimum (`results.json` nominal `tmin_min: 29.42`), so even "five orders in minutes" is generous to its own prediction. Mechanism ✓ is fine.

**Correction:** measured column should read "9→~0 MW without scram (HIGH conf.); exact collapse time unpublished; 30 MW-test analog <1% in ~13 min"; article sentence should drop "five orders… measured yes."

## Finding 6 — Vessel-temperature row hides the agent's own worst case

**Claim** (scorecard row 5: "vessel ~280–336 °C … ✓").

**Evidence.** The note's own sensitivity gives a **worst-case vessel peak of 605 °C** (note L134; `results.json` `Tvpeak_C: [335.6, 605.2]`) — above the 440 °C RPV service limit the refs quote — waved off in the note as "below short-term steel limits" (unsubstantiated). The scorecard quotes only 280–336 °C. Also the measured column ("RPV <440 °C") is a design limit plus 30 MW-test data, not 2010 measurements (refs §4). Severity: low-medium; correction: state the tail.

## Finding 7 — Cost and turn counts are wrong

**Claim:** "$23 agent" (article L124), "~$20+3" and "~340 turns" (scorecard L3).

**Evidence.** The transcript contains exactly two harness result events: **$13.0738 (num_turns 86)** at L1389 and **$3.0106 (num_turns 58)** at L1755. **Total: $16.08, num_turns 144.** Assistant message events: 311 main-thread + 98 subagent = 409. No metric yields 340 or $23. (The error overstates cost — anti-hype in direction, but it's the article's most quotable number and it's wrong.) **Correction:** "$16" (or "$13+$3"), and pick one turn metric and state it.

## Finding 8 — The compute story: VERIFIED

Every element checks out against raw evidence: ENDF tarball **3,383,607,420 bytes** (= 3.4 GB, transcript L176); **15,235 explicit TRISO** particles (L429 and every `keff.csv` row); sweep = 12,000 particles × 170 batches × 4 temps (launch command L567); OpenMC per-point runtimes in the CSVs sum to **11,997 s ≈ 3.3 h**, and `followups.log` mtime is **Jul 3 01:44** (L1403) — matching "~3.5 h of background compute… orchestrator finishing at 01:44". β_eff recomputes exactly from the kin CSV: 1 − 1.0281383/1.0356737 = **0.007276**, σ propagation gives 0.00093 as quoted; α from the k(T) endpoints reproduces ≈ −6.9 pcm/K. Quoted MC precisions are consistent with the k σ's (~6–8×10⁻⁴).

## Finding 9 — β_eff/α framing: mildly oversold, provenance-weak anchors

**Claims** (scorecard L13–16). (a) "β_eff = 0.00728 ± 0.00093" vs "design references quote β_eff ≈ 0.0065": consistent at 0.85σ, but with a ±13% error bar this is a weak-consistency check, not a validation; and the "HTTR design reference" for 0.0065 is **unsourced in the repo** — the agent's own search for it (query literally "HTTR beta effective 0.0065…", L285) returned only the *generic U-235* value. Note the query itself shows the agent held the target value in memory before computing. (b) "the two variants bracket to ±0.1" — that ±0.1 pcm/K is only the burnable-poison-treatment spread, not total α uncertainty (single 6 wt% enrichment vs 12-zone design, BOL fuel, no leakage, isothermal — all acknowledged in the note but absent from the scorecard's precision language). (c) "k_inf at 4 temperatures × 2 variants" — the BP-off variant ran 3 temperatures (294/900/1200), not 4. Severity: low. 

## Finding 10 — The task pack leaks the qualitative answers; training-data familiarity bounds what "prediction" can mean

**Evidence.** `pack/GOAL.txt` presupposes the outcome: "a predicted **recriticality time in hours** with its governing mechanism, (3) **the stabilized power level afterwards**" — recriticality occurrence, its hours timescale, and the existence of a stable level are given, not predicted. TASK.md's "whether and WHEN… (recriticality time, in hours)" softens "whether" then anchors the unit. Scorecard row 2 ("Recriticality occurs? YES ✓") and part of row 5 credit given-away answers. Separately, the queries seeded with recalled design values (0.0065; 12.4 kg/s; "0.3 MW"; "5.9 wt%") prove training-data recall was active throughout; the 2010 test outcome is, in the article's own words, "famous." No numeric outcomes were supplied and no lookup occurred — but honest phrasing is "the agent was barred from *retrieving* the results," not that it predicted from ignorance. The quantitative predictions (timing, power level) remain the only genuinely blind-ish outputs — and of those, timing missed ×7 and the power number inherits Finding 2.

## Finding 11 — Minor hygiene

(a) `analyze.py:16` docstring says "alpha(T)=dk/dT/k^2" while the code (correctly) computes (1/k)dk/dT — stale comment from the bug PROGRESS.md documents fixing. (b) The kin "full" k at 900 K equals the main-run k to 12 significant digits (same RNG seed reused), so the β_eff runs were not independent; σ_β is slightly overestimated (conservative, benign). (c) `sources.md` cites the Takizuka PDF for flow rates, but no fetch of that URL appears in the transcript — the numbers evidently came from search snippets; logging is slightly loose relative to TASK's "log every source consulted."

---

## Summary for publication

- **Keep, verified:** compliance (strongest check passes), the from-scratch OpenMC computation and all its quoted statistics, the 3.4 GB / 15,235 TRISO / 3.3 h / 01:44 compute story, the pre-registration of the conductance dependency, and the honest disclosure that the timing band excluded the truth.
- **Retract/reframe:** "beat the professional code" (Finding 2 — quantity mismatch, nominal-vs-median, input echo); "right mechanism / graphite governs everything" (Finding 3 — no xenon, contradicted by owner's own refs); "measured: five orders in minutes" (Finding 5); "$23" and "~340 turns" (Finding 7 — actual $16.08, 144 harness turns).
- **Add caveats:** measured "~300 kW" is an inference from a secondary source about a *peak*; the 13-min collapse figure is from the 2024 30 MW test; the vessel worst case was 605 °C; GOAL.txt presupposed recriticality-in-hours and stabilization.

The experiment survives the audit as an integrity artifact; the scoreboard rhetoric does not survive at full strength. The single most defensible headline the data supports is: *"a $16 agent computed HTTR's feedback physics from scratch under verified test-result blindness, got every qualitative safety call right, landed its low-end stabilized-power estimate on the measured peak value, and missed recriticality timing seven-fold for a reason it half-named in advance — the half it didn't name was xenon."*
