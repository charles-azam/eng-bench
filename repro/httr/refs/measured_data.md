# HTTR LOFC Test — Measured Outcomes (Data Diligence for Prediction Scoring)

Compiled 2026-07-03. Purpose: extract MEASURED outcomes of the HTTR loss-of-forced-cooling (LOFC)
tests so a physics prediction (made on an isolated machine) can be graded.

## CRITICAL SCOPING NOTE — which test is the prediction targeting?

There are **two** distinct HTTR all-gas-circulator-trip / no-scram LOFC tests, and they have
**different measured numbers**. Do not mix them.

| Test | Power | Date | VCS | Recriticality | Best documentation |
|---|---|---|---|---|---|
| **LOFC "30%" / 9 MW** (the one in the prompt) | 9 MWt (30%) | **Dec 2010** (test succeeded; ~Dec 22 2010) | ON | Yes | Takamatsu 2014 JNST (paywalled); analysis papers give 6–8 h |
| LOFC 100% / 30 MW (newer, full power) | 30 MWt | **2024-03-28/29** | ON | Yes, **~14 h**, peak ~2.5%, stabilized ~1.2% (0.36 MW) | JAEA-Research 2025-005 (OPEN, detailed measured numbers) |
| LOFC#3 / 9 MW, VCS-OFF (NEA benchmark) | 9 MWt | ~2021 (FY2021) | OFF | **No** — shut down early due to overheating of upper core components | NEA LOFC project / OSTI 2475055 |

The prompt describes: 9 MWt, 30% power, all circulators tripped, no scram, rods frozen,
**vessel cooling system ON**, ~2010. => **This is the Dec 2010 LOFC test, the subject of Takamatsu et al. 2014.**

WARNING for scoring: The detailed *measured* numbers for the 2010 9 MW test are only fully in the
paywalled Takamatsu 2014 JNST paper, and JAEA/NEA data-sharing restrictions apply (explicitly noted
in the INL RELAP5-3D report). The 30 MW 2024 test (JAEA-Research 2025-005) is the one with rich,
openly published measured numbers. Numbers below are labeled by test and by confidence.

---

## 1. Fission-power trajectory after the trip (how fast, to what level)

### 9 MW / 2010 test (the target test)
- Reactor power **decreased from 9 MW toward ~0 MW** due to negative reactivity feedback (fuel +
  moderator temperature coefficients) as core heated once forced convection stopped, WITHOUT scram.
  - Source (analysis/abstract, text-quoted): "the reactor power decreases from 9 MW to 0 MW owing to
    the negative reactivity feedback effect of the core, even if the reactor shutdown system is not
    activated." — INIS record / ResearchGate abstracts of Takamatsu 2014 & Fujimoto 2013.
    Confidence: HIGH that it dropped to ~0/decay-heat level; exact *time-to-collapse* for the 9 MW
    test not text-quoted in open sources.
- Primary coolant flow: **rated 45 t/h → 0 t/h** essentially immediately on circulator trip.
  - Source: INIS record 2jb1r-jyc05 (text-quoted "from the rated 45 t/h to 0 t/h").
    NOTE: the 2025 report gives rated flow at 9 MW rod-withdrawal test as 44.6 t/h — same ~45 t/h.

### 30 MW / 2024 test (analogous, MEASURED, open) — useful as a proxy for collapse speed
- "同循環機の停止操作後 **13 分程度**で原子炉出力は、**1％以下**まで低下した" =
  **power fell below 1% within ~13 minutes** of the circulator stop, then stayed <1% for hours.
  - Source: JAEA-Research 2025-005, p.16 (text-quoted, MEASURED). Confidence: HIGH (for 30 MW test).
  - Inference for 9 MW test: collapse is expected to be similarly fast (order ~10 min), but this exact
    number is the 30 MW test, not the 2010 9 MW test. Label accordingly if used.

---

## 2. Recriticality time (headline number)

### 9 MW / 2010 test (TARGET) — sources disagree slightly; note measured vs analysis
- **"Re-criticality was shown after about 8 h."** — Fujimoto, "Reactor Kinetics in a LOFC Test of
  HTGRs" (abstract, describing the 9 MW test). Text-quoted. This reads as the **measured** result.
  Confidence: MEDIUM-HIGH (abstract-quoted, but ambiguous measured-vs-calc).
- **"the HTTR achieves recritical after an elapsed time of 6–7 h"** — Takamatsu 2014 / thermal-hydraulic
  analysis abstract. This is stated in the context of the analytical model. Text-quoted.
  Confidence: HIGH that this is the **analysis** value.
- INL RELAP5-3D report (Ougouag/Lu modeling, text-quoted): "The LOFC test showed a **power peak
  approximately 8 hours** after the onset of the LOFC" (attributed to the experiment), while the
  RELAP5-3D/PHISICS **prediction** put recriticality at **7 h**.
- **Best estimate of MEASURED recriticality time for the 9 MW test: ~7–8 h after the trip**
  (headline ≈ "about 8 hours"). Treat 6–8 h as the credible band. Confidence: MEDIUM
  (exact measured value is in the paywalled Takamatsu 2014 figure/text, not directly extracted here).

### 30 MW / 2024 test (MEASURED, open, for contrast)
- **"循環機停止操作の約 14 時間後に再臨界となり" = recriticality ~14 h after circulator stop.**
  - Source: JAEA-Research 2025-005, p.16 (text-quoted, MEASURED). Confidence: HIGH.
  - Longer than the 9 MW case, as expected (more stored energy / xenon dynamics at full power).

### 9 MW VCS-OFF (LOFC#3, NEA benchmark)
- **No recriticality** — reactor was shut down prematurely due to overheating of upper reactor
  components. Source: NEA LOFC Test#3 benchmark / OSTI 2475055 (text-quoted). Confidence: HIGH.

---

## 3. Power level after recriticality + oscillation behavior

### 9 MW / 2010 test (TARGET)
- Peak power at recriticality is **small / negligible vs nominal**.
  - INL RELAP5-3D report (text-quoted): measured "magnitude of the peak was **less than 0.5 MW**"
    (i.e. <~5.5% of 9 MW). The RELAP5-3D/PHISICS prediction gave ~0.65 MW, which Lu reported as
    "about **0.35 MW higher than the measured value**" => implied **MEASURED peak ≈ 0.30 MW (~3.3%)**.
    Confidence: MEDIUM-HIGH (arithmetic from two text-quoted statements in the INL report).
- Oscillation: "After the reactor power peak occurs, the total reactivity **oscillates several times**
  because of the negative reactivity feedback effect and gradually decreases to zero." — Fujimoto/
  Takamatsu (text-quoted). So expect a **damped oscillation** settling to a low steady power.
  Confidence: HIGH (qualitative), MEDIUM (magnitude).
- Reactor then **stabilizes spontaneously at a low power** matched to VCS heat removal (decay heat
  level). Exact stabilized % for the 9 MW test not text-quoted in open sources (in Takamatsu 2014 fig).

### 30 MW / 2024 test (MEASURED, open) — the clean analog
- **Peak ~2.5%** of rated at recriticality, then settled to **stable ~1.2% (= 0.36 MW)**.
  - Source: JAEA-Research 2025-005, p.16 ("出力は約 **2.5％のピーク**に達した後低下し、出力約 **1.2%**
    の低出力の安定状態"; and "再臨界後の原子炉出力 **1.2% (0.36 MW)**"). Text-quoted, MEASURED.
    Confidence: HIGH.

---

## 4. Peak/trend fuel, core, vessel temperatures (bounded? values?)

### General bounding statement (both tests) — inherent safety
- Fuel temperature did NOT rise much: "the fuel temperature did not show a large increase because the
  large heat capacity of the graphite core could absorb heat from the fuel in a short period."
  (text-quoted, JAEA/search). Core never approached melt; well below limits. Confidence: HIGH.
- Fuel design/limit references: normal-operation fuel thermal limit **1495 °C**; fuel design
  temperature limit **1600 °C** (never exceeded). RPV normal-operation limit **440 °C**.
  - Source: JAEA-Research 2025-005 p.15 (text-quoted). Confidence: HIGH (these are limits, not peaks).

### 30 MW / 2024 test (MEASURED, open) — actual vessel-side numbers
- Fuel temperature rose only **"数十℃" (a few tens of °C)** above the 30 MW steady value after
  circulator stop and stayed below the 1495 °C limit (pre-test analysis; measured trend consistent).
- **RPV surface temperature: ~350 °C steady → DECREASED after trip; never exceeded 440 °C limit.**
  Measured RPV surface band **300–350 °C**; VCS water-cooled panel surface **20–40 °C**.
  - Source: JAEA-Research 2025-005 p.16 (text-quoted, MEASURED): "300〜350℃の圧力容器表面温度と
    20〜40℃の水冷パネル表面", "使用最高温度である 440℃を超えることはなかった". Confidence: HIGH.
- Note: RPV temperature FALLS during the transient (core heat leaks slowly through graphite; VCS
  keeps removing heat) — counterintuitive but measured.

### 9 MW / 2014 R&D Review preparatory VCS test (MEASURED, open) — vessel-side structure temps
- JAEA R&D Review 2014, 6-4 (Fig.6-8), ~7 h test. Measured internal/vessel structure temperatures,
  all far below limits and nearly flat:
  - Permanent reflector block: ~**140–160 °C** (read from figure axis).
  - Hot plenum block, reactor pressure vessel, primary biological shielding: all monitored, changes
    "**negligibly small**"; only an uncovered water-cooling *tube* rose locally (still below max
    allowable), mitigated by briefly restarting the VCS circulation pump (5 min).
  - Source: rdreview.jaea.go.jp/review_en/2014/pdf/e2014_6-4.pdf. Confidence: HIGH (text) / MEDIUM
    (exact numbers figure-read). NOTE: this is a VCS-focused preparatory test, not the full power
    trajectory test — use for vessel/structure temperature bounding only.

### VCS heat removal (30 MW test, MEASURED)
- Natural convection + radiation from RPV to water panels removed **~0.7 MW**, larger than the
  post-recriticality reactor power (0.36 MW), so core temperature stays flat/stable.
  - Source: JAEA-Research 2025-005 p.16 (text-quoted). Confidence: HIGH (30 MW test).

---

## 5. 9 MW test vs other LOFC tests — which is best documented with extractable numbers

- **Most extractable OPEN measured numbers: the 30 MW / 2024 test (JAEA-Research 2025-005).**
  Full free PDF with: <1% in ~13 min, recriticality ~14 h, peak 2.5%, stable 1.2%=0.36 MW,
  RPV 300–350 °C (<440 °C limit), VCS ~0.7 MW. This is the gold-standard extractable dataset — but it
  is a DIFFERENT test (full power) than the 2010 9 MW test in the prompt.
- **The 2010 9 MW test** (prompt's target): primary source is Takamatsu et al. 2014 JNST
  (doi 10.1080/00223131.2014.967324). Paywalled; tandfonline blocks automated fetch (403 + JS wall).
  Open secondary sources give: power 9→0 MW, flow 45→0 t/h, recriticality ~6–8 h, peak <0.5 MW
  (measured, ~0.3 MW inferred), oscillates and settles low. Detailed measured temperature/time curves
  are inside that paper's figures (not text-extracted here).
- **9 MW VCS-OFF (LOFC#3, NEA benchmark, ~2021):** NO recriticality (shut down early on upper-core
  overheating); it is a thermal-hydraulics benchmark. Data is under NEA LOFC-project sharing
  restrictions (explicitly stated in INL RELAP5-3D report: "Restrictions on data sharing ... prevent
  us from sharing HTTR data").

---

## 6. Pre-test code predictions (what the professionals predicted)

### For the 9 MW / 2010 test
- Pre-test safety analysis used **TAC/BLOOST** (JAEA core dynamics code, validated on earlier
  flow-reduction tests). Predicted: power drops to ~0%, recriticality after "十数時間" (ten-plus
  hours) in the generic description, fuel temp rise small, all limits respected.
- JAEA-Technology 2007-056 (pre-test planning report, OPEN PDF) confirmed the three-gas-circulator
  trip test and VCS-stop test could be performed within normal-operation limits and reactor safety is
  ensured; test to be done at ≤9 MW (30%), reactor-outlet coolant temp ≤320 °C at start.
  - Source (text-quoted English abstract): jopss.jaea.go.jp/pdfdata/JAEA-Technology-2007-056.pdf.
    Confidence: HIGH (that it's a pre-test analysis); specific predicted curves are in JP figures.
- Independent modeling (INL, RELAP5-3D + PHISICS, post-hoc benchmark): predicted recriticality **7 h**,
  peak **~0.65 MW** — vs measured peak "<0.5 MW" (over-predicted peak by ~0.35 MW). The professionals'
  neutronic model "demonstrated accuracy in predicting power evolution and core re-criticality" per NEA.
- Analytical band from Takamatsu 2014/Fujimoto: reactivity falls for **2–3 h** (Doppler + moderator),
  then rises with **Xe-135 decay**, giving recriticality at **6–7 h** (analysis) / **~8 h** (test).

### For the 30 MW / 2024 test
- Pre-test TAC/BLOOST analysis predicted power→0%, recriticality after "十数時間" (~ten-plus hours;
  measured ~14 h), fuel temp rise of a few tens of °C (<1495 °C), RPV falling from ~350 °C (<440 °C),
  and even beyond the 17 h test window fuel stays <1600 °C. Measured results matched. Confidence: HIGH.

---

## HEADLINE MEASURED NUMBERS (for the scorer)

**Target = HTTR LOFC, 9 MWt (30%), all circulators tripped, no scram, VCS ON, Dec 2010:**
1. Recriticality time: **~7–8 h after the trip** (measured ≈ "about 8 h"; analysis 6–7 h). [MED conf]
2. Power collapse: **9 MW → ~0 (decay-heat/<1% level)**, rapidly (order ~10 min; 30 MW analog = <1% in ~13 min). Flow 45→0 t/h. [HIGH that it collapsed; MED on exact time]
3. Peak power at recriticality: **< 0.5 MW measured (≈0.3 MW, a few % of 9 MW)**, then damped oscillations settling to a low steady power tracking VCS heat removal. [MED-HIGH]
4. Temperatures BOUNDED, no core damage: fuel stayed far below 1495 °C limit (rose only tens of °C); RPV stayed below 440 °C (falls during test); core never near melt. [HIGH qualitative]

**Clean open analog (30 MW / 2024, JAEA-Research 2025-005, all MEASURED):** <1% in ~13 min;
recriticality ~14 h; peak 2.5%; stable 1.2% = 0.36 MW; RPV 300–350 °C (<440 °C); VCS removes ~0.7 MW.

---

## SOURCES / URLs

- Takamatsu et al. (2014), "Experiments and validation analyses of HTTR on loss of forced cooling
  under 30% reactor power," J. Nucl. Sci. Technol. 51(11-12). doi 10.1080/00223131.2014.967324.
  https://www.tandfonline.com/doi/full/10.1080/00223131.2014.967324  [PAYWALLED to automated fetch:
  403 + JS/cookie wall; primary source for the 2010 9 MW measured curves]
- Fujimoto/Takamatsu, "Spontaneous stabilization of HTGRs without reactor scram and core cooling —
  Safety demonstration tests using the HTTR," Nucl. Eng. Des. (2013).
  https://www.sciencedirect.com/science/article/abs/pii/S0029549313006808  [abstract-quoted]
- Fujimoto et al., "Reactor Kinetics in a Loss-of-Forced-Cooling (LOFC) Test of HTGRs."
  https://www.researchgate.net/publication/267581090  ["Re-criticality was shown after about 8 h"]
- "Thermal-hydraulic analyses of the HTTR for loss of forced cooling at 30% reactor power," Ann. Nucl.
  Energy. https://www.sciencedirect.com/science/article/abs/pii/S0306454916311914  [abstract]
- INIS record (analysis of the LOFC test): https://inis.iaea.org/records/2jb1r-jyc05
  [flow 45→0 t/h, outlet ≤950 °C, power→decay level]
- JAEA-Research 2025-005, "HTTRを用いた安全性実証試験の完遂" (Completion of safety demonstration tests
  using HTTR), May 2025. https://jopss.jaea.go.jp/pdfdata/JAEA-Research-2025-005.pdf  [OPEN, FULL —
  the 30 MW 2024 test measured numbers: recrit ~14 h, peak 2.5%, stable 1.2%/0.36 MW, RPV 300–350 °C,
  VCS ~0.7 MW; also describes pre-test TAC/BLOOST predictions]
- JAEA-Review 2025-032, HTTR tests/operation & tech development (FY2023).
  https://jopss.jaea.go.jp/pdfdata/JAEA-Review-2025-032.pdf  [context: LOFC 30% (9 MW) circulator-trip
  test in NEA LOFC project framework]
- JAEA-Technology 2007-056, "Investigation of the loss of forced cooling test by using the HTTR"
  (pre-test planning/analysis). https://jopss.jaea.go.jp/pdfdata/JAEA-Technology-2007-056.pdf
  [OPEN; confirms test bounded within normal operation; ≤9 MW, outlet ≤320 °C at start]
- JAEA R&D Review 2014, 6-4 (VCS effectiveness / test-procedure establishment).
  https://rdreview.jaea.go.jp/review_en/2014/pdf/e2014_6-4.pdf  [OPEN; measured vessel/structure temps
  over ~7 h: permanent reflector ~140–160 °C, RPV/hot-plenum/shielding changes negligible]
- INL, "RELAP5-3D Capabilities for High-Temperature Gas-Cooled Reactor Analysis" (OSTI 3013713).
  https://www.osti.gov/servlets/purl/3013713  [text-quoted: measured power peak ~8 h, peak <0.5 MW;
  RELAP5-3D/PHISICS predicted recrit 7 h, peak ~0.65 MW = ~0.35 MW above measured; notes NEA
  data-sharing restrictions on HTTR data]
- NEA HTTR LOFC Project Test#3 Benchmark Results (OSTI 2475055).
  https://www.osti.gov/biblio/2475055  [9 MW VCS-OFF: NO recriticality, shut down on upper-core
  overheating]
- OECD-NEA LOFC Project pages: https://www.oecd-nea.org/jcms/pl_25168/loss-of-forced-coolant-lofc-project
  and https://www.oecd-nea.org/jcms/pl_103885/ (extended to 2027).
- JAEA HTTR research pages: https://www.jaea.go.jp/04/o-arai/nhc/en/research/httr/index.html and
  .../httr_research02.html  [test date: LOFC 9 MW "successfully conducted in December 2010"]

## Confidence legend
- Text-quoted = the exact number appears in prose I read (HIGH confidence).
- Figure-read = number read off a plotted axis (MEDIUM).
- Inferred = arithmetic from two quoted statements (MEDIUM-HIGH, stated as such).
- The single biggest gap: the *exact measured* recriticality time and stabilized power for the 2010
  9 MW test live in Takamatsu 2014's figures, behind a hard paywall. Open sources bracket recrit at
  6–8 h and peak <0.5 MW. If exact grading of the 9 MW test is required, obtain Takamatsu 2014 via
  institutional access.
