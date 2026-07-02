# I ran an AI engineering department for a week

<!-- CAPSTONE — spans all three experiments. ~2,000 words target. HTTR slots marked [HTTR].
     Fill from httr harvest, then final polish pass. -->

**TL;DR.** Over one week, on a €30/month server, I gave autonomous AI agents three nuclear
engineering problems of increasing cruelty: a passive cooling rig a national lab spent 33 months
measuring, a statistical fuel-failure benchmark the IAEA designed to be hard, and a real
reactor's most famous self-rescue test — which required the agent to install a Monte Carlo
neutronics code, download 3.4 GB of nuclear data, and compute its own physics constants for
hours before it could even start predicting. Total spend: roughly $120 of API. The agents
matched a national lab's measurements to a few percent, reproduced the nuclear industry's own
systematic errors with eerie fidelity, invented missing physics when the spec sheet was
incomplete — and got things wrong in ways that taught me more than the successes. Everything —
transcripts, models, scoring, an adversarial AI audit of my own claims — is public: [REPO].

## The setup, once

Each problem got the same treatment. I curated an input pack — geometry, materials, operating
conditions, the things a design engineer would actually receive — with every measured outcome
surgically removed and held out for grading. One plain-language task ("you are an engineer;
produce a calculation note; here's what I want"). No method hints. A hard rule against looking
up the experiments' published results, enforced by publishing every transcript (you can grep
them yourself: zero web calls in the offline runs). Then I let Claude agents run unattended on
a small VPS, a few dollars a run, and graded whatever came back against reality.

An independent AI auditor with an adversarial charter reviewed the claims and found real
problems — its unedited report and my corrections are in the repo. Two of the biggest honesty
upgrades in what follows came from it.

## Problem 1: the reactor cooling system with no moving parts

*(Covered in depth in [ARTICLE 1] — summary here.)*

Argonne built a half-scale mock-up of a passive reactor cooling system: a 220 kW heated wall
radiating across an air gap to steel ducts, air rising by buoyancy alone up a 20-metre chimney.
Given the blueprints, agents predicted the lab's measured airflow within ±4% in six of seven
runs, the vessel-wall temperature within −8…+8%, correctly called the marquee accident test
("temperature rises 3.5 days, levels off below the limit, comes back down — no runaway") in
every single run, and nailed a blind argon-flood scenario's restart threshold to 5 °C. One run
installed OpenFOAM unaided and cross-checked itself with view-factor radiation CFD. The
systematic miss — air temperature rise +14–31% everywhere — traced to one supplied input every
agent had flagged as its riskiest assumption before any comparison existed.

Score: the kind of agreement engineering consultancies would happily invoice a month for,
at $3–16 per run. But it's one physics domain. The obvious objection: maybe thermal-hydraulics
of a big chimney is just... forgiving. So, problem 2.

## Problem 2: a billion tiny pressure vessels

TRISO fuel is the "fuel that cannot melt": each particle — poppy-seed sized — is a uranium
kernel inside its own four-layer containment, the crucial layer being a silicon-carbide shell
~35 microns thick. A reactor holds billions; safety is a *statistical* property. The design's
elegant trick: under irradiation the carbon layers shrink and squeeze the SiC into compression,
pre-stressing the vessel against the fission-gas pressure building inside.

The IAEA ran a benchmark on exactly this — accident furnace tests where irradiated fuel spheres
(16,400 particles each) were held at 1600–1800 °C while a detector counted each particle
failure via krypton release. The measured drama: one sphere spent **500 hours at 1600 °C: zero
failures**. Its sister sphere at **1800 °C: ten failures in the first hundred hours**, each
individually timestamped. A cliff, between twins.

I gave agents the conditions and the benchmark's own material-property annex — offline, no web
— and asked for predictions. Four runs (three Opus, one Fable 5). What came back:

- **Every run correctly called the zero-failure cases** (the 1600 °C sphere and the
  lower-burnup compact): 8 verdicts, 8 correct.
- **Every run under-predicted the 1800 °C failure counts** — by factors of 8 to 170. And this
  miss is the most instructive result of the week: the annex supplies pressure-vessel mechanics
  only, and at these stresses (a third of the shell's strength) pressure alone bursts nothing.
  That is the *historically correct* pressure-vessel answer — the real 1800 °C killer is
  slow thermal degradation of the SiC itself, which wasn't in the provided property set. The
  agents faithfully computed the physics they were given.
- **Two runs noticed the gap and invented the missing mechanism.** One calibrated its
  degradation model cautiously and bracketed the staged test exactly (predicted 0–5 failures;
  measured 5 — and placed them "mostly in the final 300-hour 1800 °C phase"; measured: all five
  there). The other calibrated aggressively and overshot that same case ×60 while getting the
  phase placement dead-on. Same insight, opposite error bars: judgment under incomplete physics,
  visible in both directions.
- **The caesium predictions reproduced the nuclear industry's own biases almost exactly.** The
  benchmark report notes that professional fuel-performance codes are accurate on hot
  high-release tests but overpredict caesium on 1600 °C tests by an order of magnitude. The
  agents — using the community's own diffusion correlations — were accurate within ×2 at
  1800 °C and one to three orders high at 1600 °C. Inherited correlations, inherited errors.
  An agent is a mirror: give it the field's data and it returns the field's blind spots.
- And a limit no model could cross: the measured data shows the 1800 °C sister sphere failing
  *more* in 100 hours than the staged sphere did in 400 — a fuel-manufacturing-batch difference
  that identical-particles physics cannot express. Reality keeps information off the spec sheet.

Cost: ~$2 and ~12 minutes per run.

## Problem 3: the reactor that wakes itself back up

[HTTR — FILL FROM HARVEST. Structure:]
Japan's HTTR is a real 30 MW high-temperature reactor. In 2010 they did something wonderful:
tripped every cooling circulator at 9 MW and froze the control rods — no scram — and watched.
Fission power collapsed within minutes (the core heats up, negative temperature feedback kills
the chain reaction). Then, about [~7–8] hours later, as the graphite slowly cooled, **the
reactor spontaneously went critical again** — waking itself up — and settled at a low simmer
(~0.3 MW) where the passive vessel cooling could carry the heat away indefinitely.

This problem is different in kind: there's no spec sheet with a property annex. To predict the
transient you need the core's temperature-feedback coefficients, and I refused to supply them —
the agent had to *compute* them. [DESCRIBE: it installed OpenMC, pulled 3.4 GB of ENDF/B-VIII.0
nuclear data, built a pin-in-block lattice model with explicit TRISO double heterogeneity from
public design data (design sources allowed and logged; test results forbidden), argued —
correctly — that the transient needs the *shape* of α(T) since the frozen rods set absolute
criticality, and ran Monte Carlo for [N hours] to get coefficients with statistical error bars.
This was the week's long computation: [X] hours wall-clock, [турns/cost].]

[RESULTS: predicted power-collapse timescale [..] vs measured ~minutes; recriticality at [..] h
vs measured ~7–8 h; stabilized power [..] vs measured ~0.3 MW; bounded verdict [..]. Context
that must be included honestly: a US national lab's post-hoc analysis with RELAP5-3D predicted
recriticality at 7 h but overpredicted the power peak by roughly 2× (0.65 vs ~0.3 MW) — so the
professional bar is itself approximate. Whatever the agent got, compare against BOTH the
measurement and the professional code.]

[If the run fails or stalls: report that honestly as the week's boundary — "here is where
autonomous engineering currently stops."]

## What three problems in one week actually taught me

**Accuracy tracked the completeness of the physics I handed over, not the difficulty of the
question.** Complete first-principles physics (the chimney): a few percent. Community
correlations (TRISO caesium): the community's errors, faithfully reproduced. Missing physics
(1800 °C SiC): under-prediction — unless the agent noticed and invented, at which point results
depended on calibration judgment, exactly like human engineers.

**The failures were never random.** Every miss of the week traces to a nameable cause — a
supplied duty input, an absent degradation mechanism, a fuel-batch difference invisible to
physics. Agents that derive rather than memorize produce *structured* errors, and structured
errors are debuggable. That's what makes this engineering rather than oracle-consulting.

**Qualitative safety verdicts were bulletproof; quantitative precision was model-tier
dependent.** Every run of every model on every problem got the "does it save itself?" question
right, with correct mechanisms. The numbers separated the model generations — [one line on
Sonnet vs Opus vs Fable 5 across the week: Sonnet's structural radiation error at +49%; Opus
ensembles within single digits; Fable 5 hitting the vessel wall within 1.2% twice and producing
the campaign's best radiative fraction — and, on TRISO, the boldest invented mechanism with the
widest error bars].

**And the meta-lesson: the harness mattered more than the model.** Held-out answers, frozen
prompts, published transcripts, independent input curation, an adversarial audit that made every
claim in this post more honest — that machinery is what turns "an AI said a number" into
something an engineer can defend. The models will keep improving on their own. The trust
machinery is the part you have to build.

*Everything is public: inputs, prompts, every transcript, the agents' models, the measured
values with citations, the audit. [REPO]. The two deep-dives: [ARTICLE 1 — the cooling rig],
[ARTICLE 2 — the physics of the chimney, with an interactive calculator].*

<!-- Title candidates:
"I ran an AI engineering department for a week"
"Three nuclear problems, one week, $120 of AI"
"What an AI engineering department gets right (and wrong): a week of validated experiments" -->
