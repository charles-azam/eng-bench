# I ran an AI engineering department for a week

**TL;DR.** Over one week, on a €30/month server, I gave autonomous AI agents three nuclear
engineering problems of increasing cruelty: a passive cooling rig a national lab spent 33
months measuring, a statistical fuel-failure benchmark the IAEA designed to be hard, and a
real reactor's most famous self-rescue test — for which an agent installed a Monte Carlo
neutronics code, downloaded 3.4 GB of nuclear data, and computed its own physics constants
through the night before predicting. Total spend: about $125 of API. The agents matched the
lab's measurements to a few percent where the physics was complete, reproduced the nuclear
industry's own systematic errors with eerie fidelity where they used its correlations,
invented missing physics when the spec sheet was incomplete — and the biggest miss in each
campaign traced to a nameable cause, most of them flagged by an agent in advance. Three
adversarial AI audits of my own claims caught me overselling, repeatedly; their unedited
reports and my corrections are published. Everything — transcripts, models, scoring — is
public: https://github.com/charles-azam/ai-eng-bench.

## The setup, once

Each problem got the same treatment. I curated an input pack — geometry, materials, operating
conditions, the things a design engineer would actually receive — with every measured outcome
surgically removed and held out for grading. One plain-language task ("you are an engineer;
produce a calculation note; here's what I want"). No method hints. A hard rule against looking
up the experiments' published results, enforced by publishing every transcript (you can grep
them yourself: zero web calls in the offline runs). Then I let Claude agents run unattended on
a small VPS, a few dollars a run, and graded whatever came back against reality.

Each campaign was then reviewed by an independent AI auditor with an adversarial charter and
fresh context. They found real problems — including, on the third campaign, a headline claim I
had to retract entirely. All three unedited reports and my corrections are in the repo.

## Problem 1: the reactor cooling system with no moving parts

*(Covered in depth in [the deep-dive article](https://charles-azam.github.io/blog/ai-predicts-nuclear-experiment) — summary here.)*

Argonne built a half-scale mock-up of a passive reactor cooling system: a 220 kW heated wall
radiating across an air gap to steel ducts, air rising by buoyancy alone up a 20-metre chimney.
Given the blueprints, agents predicted the lab's measured airflow within ~4% in six of seven
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
(~15,000 particles each) were held at 1600–1800 °C while a detector watched for each particle
failure via krypton release. The measured drama: one sphere spent **500 hours at 1600 °C: zero
failures out of 16,400**. Its sister sphere at **1800 °C: ten to twelve failures within a
hundred hours**. A cliff, between twins.

I gave agents the conditions and the benchmark's own material-property annex — offline, no web
— and asked for predictions. Five runs (three Opus, one Sonnet, one Fable 5). What came back:

- **Every run correctly called the zero-failure cases** (the 1600 °C sphere and the
  lower-burnup compact): ten verdicts, ten correct.
- **Every run under-predicted the 1800 °C sister sphere** — by factors of 8 to 450. And this
  miss is the most instructive result of the week: the annex supplies pressure-vessel mechanics
  only, and at these stresses (14–38% of the shell's strength) pressure alone bursts nothing.
  That is the *correct* pressure-vessel answer — the real 1800 °C killer is slow thermal
  degradation of the SiC itself, which wasn't in the provided property set. The agents
  faithfully computed the physics they were given.
- **What separated the models is what they did about the gap.** The Fable 5 run *coded* a
  degradation mechanism it reasoned should exist — and overshot the staged test ×60 while
  placing the failures in exactly the right phase ("~95% in the final 300-hour 1800 °C hold";
  measured: all five there). One Opus run declined to code anything but attached a
  self-described low-confidence "0–5 failures" judgment band whose upper edge touched the
  measured 5 — and whiffed the other two nonzero cases. The other three reported the
  pressure-vessel answer as-is. Code it, band it, or decline: three engineering temperaments,
  all visible, none of them right.
- **The caesium predictions tended to reproduce the nuclear industry's own biases.** The
  benchmark report notes that professional fuel-performance codes are decent on hot
  high-release tests but overpredict caesium on 1600 °C tests by an order of magnitude. The
  agents — using the community's own diffusion correlations — landed within ×2 on the pure
  1800 °C sphere, ×3–12 on the staged case (where the professional codes were also specifically
  bad), and one to three orders high at 1600 °C — in four runs of five; the Sonnet run
  under-predicted instead. A tendency, not a law. An agent is a mirror: give it the field's
  data and it mostly returns the field's blind spots.
- And a limit no model could cross: the measured data shows the 1800 °C sister sphere failing
  *more* in 100 hours than the staged sphere did in 400 — plausibly a fuel-batch difference
  that identical-particles physics cannot express. Reality keeps information off the spec sheet.

Cost: $1.7–5.4 and 8–23 minutes per metered run.

## Problem 3: the reactor that wakes itself back up

Japan's HTTR is a real 30 MW high-temperature reactor. In 2010 its operators did something
wonderful: they tripped every cooling circulator at 9 MW and froze the control rods — no
scram — and watched. Fission power collapsed within minutes (the core heats up; negative
temperature feedback kills the chain reaction). Then, hours later, as the graphite slowly
cooled, **the reactor spontaneously went critical again** — woke itself up — and settled into
a low simmer that the passive vessel cooling could carry away indefinitely.

This problem is different in kind: there is no spec sheet with a property annex. To predict
the transient you need the core's temperature-feedback coefficients, and I refused to supply
them — the agent had to *compute* them. So it did. It installed OpenMC (the Monte Carlo
neutron-transport code), pulled 3.4 GB of nuclear data, built an HTTR fuel-lattice model with
fifteen thousand explicitly placed TRISO particles from public design documents (design
sources were allowed and every one is logged; test results were forbidden — and when LOFC
test papers surfaced in its searches, it logged the incident and declined to open them). It
argued, correctly, that with the rods frozen only the *shape* of reactivity-vs-temperature
matters, ran its temperature sweep two ways to bracket the burnable-poison uncertainty, and
left the Monte Carlo grinding through the night on its own orchestrator script — about three
and a half hours of compute, the week's one genuinely long calculation. Out the other end: a
temperature coefficient of −7 pcm/K with error bars, a delayed-neutron fraction of
0.0073 ± 0.0009 — consistent with the design literature, derived from geometry and cross
sections on a rented box. (An adversarial audit of this campaign later re-derived every one of
these numbers from the raw Monte Carlo outputs. They reproduce.)

Then it coupled those constants to reactor kinetics and a thermal model and predicted the
test. Scorecard — with the corrections that audit forced on my first draft baked in:

- **Self-shutdown**: predicted — power collapses below decay heat in minutes, no rods, no
  operator. Measured: yes — the power fell away without a scram. ✓
- **Spontaneous recriticality**: predicted. (Honesty note: my task prompt asked for "the
  recriticality time in hours," which presupposes the famous result — the real prediction
  content here is the mechanism and the numbers, not the "whether.")
- **The stabilized power**: its low-end estimate, **287 kW**, coincided with the measured
  power peak (**~0.3 MW**, versus a national lab's post-hoc 0.65 MW). I originally wrote "the
  agent beat the professional code" here. The audit killed that framing, correctly: the agent's
  own uncertainty band had a median of 575 kW — a ~2× miss statistically indistinguishable
  from the professionals' — and its winning low end traces to an input assumption it never
  verified. What honestly survives: the band brackets the measurement; the single number
  doesn't deserve the trophy.
- **The clock**: predicted recriticality within ~1 hour. Measured: **7–8 hours**. Off by
  seven-fold — the week's biggest miss, and its most instructive, in two layers. The agent
  *pre-registered*, in writing, before any comparison existed, that the timing hinged on one
  unpublished number — how well the core couples thermally to its surroundings. True, and
  verified in the transcript. But the audit found the half it *didn't* flag: the published
  analyses attribute much of the 7-hour delay to xenon poisoning decaying away — a neutronics
  effect that appears exactly zero times in the agent's model. Half the miss was pre-registered;
  the other half was a blind spot. (Its stated uncertainty band didn't reach 7 hours either:
  a genuine calibration failure, reported as such.)
- **Bounded, no runaway**: predicted (peak fuel ~583 °C against a 1600 °C limit); measured:
  bounded, everything far below limits. ✓

And then the part I care about most. If these errors are really *structured* — debuggable —
then naming the missing physics should fix the clock. So I ran the diagnosis: a follow-up
agent run ($3.87, fifteen minutes, offline) was told only that its original answer was
seven-fold short and that the review suspected xenon, and was asked to extend its own model —
standard nuclear data, no tuning, measured value withheld. One xenon term later, the 1-hour
clock became **12.5 hours, with an uncertainty band of 1.8–21 h** — the measured 7–8 sits
inside it. (Being honest about what this is: a mechanism-sufficiency test, not a fresh
prediction — the agent knew the size of the gap it was trying to explain. What it demonstrates
is that the named mechanism, at standard nuclear-data values, produces a delay of exactly the
required scale — and, tellingly, the corrected model's stabilized power moved *toward* the
professional code's answer, reinforcing the audit's retraction rather than my original trophy.)
An error you can name is an error you can fix, for four dollars, before lunch.

## What three problems in one week actually taught me

**Accuracy tracked the completeness of the physics I handed over, not the difficulty of the
question.** Complete first-principles physics (the chimney): a few percent. Community
correlations (TRISO caesium): the community's errors, faithfully reproduced. Missing physics
(1800 °C SiC): under-prediction — unless the agent noticed and invented, at which point results
depended on calibration judgment, exactly like human engineers.

**The failures were never random.** Every miss of the week traces to a nameable cause — a
supplied duty input, an absent degradation mechanism, a missing xenon term, a fuel-batch
difference invisible to physics. Agents that derive rather than memorize produce *structured*
errors, and structured errors are debuggable. That's what makes this engineering rather than
oracle-consulting.

**Qualitative safety verdicts were bulletproof; quantitative precision was model-tier
dependent.** Every run of every model on every problem got the "does it save itself?" question
right, with correct mechanisms. The numbers separated the generations: Sonnet made a
structural radiation error worth +49% on a vessel temperature and executed supplied physics
without questioning it; Opus ensembles landed in the single digits and one Opus run flagged
the missing TRISO mechanism with an honest judgment band. Fable 5, the newest tier, showed
something different: judgment. On the cooling rig, both of its transcript-backed runs
independently *rejected my supplied heat duty* — the input my own audit had flagged as encoding
the answer — trading the campaign's best flow numbers for its widest air-ΔT misses,
self-consistently; only one of seven Opus runs had dared that. On TRISO, one Fable run was the
only agent of the week bold enough to *code* the missing degradation mechanism, wearing the
widest error bars of the week for it — and a rerun of the same model on the same pack chose a
cautious judgment band instead. Temperaments are sampled, not fixed. Capability, at the
frontier, looks less like arithmetic and more like nerve — nerve you have to sample, which is
why the unit of AI engineering analysis is the ensemble, not the run.

**The misses were the best part.** The cooling rig's air-temperature bias: pre-flagged
(supplied heat duty). The TRISO undercount: the textbook-correct mistake (missing degradation
physics). The HTTR clock: half pre-registered (an unpublished conductance), half blind spot
(the xenon the audit caught). Three problems, three different physics domains, one signature —
agents that derive rather than retrieve make errors you can *name*, and errors you can name
are errors you can fix.

**And the meta-lesson: the harness mattered more than the model.** Held-out answers, frozen
prompts, published transcripts, independent input curation, adversarial audits that made
every claim in this post more modest and more true — that machinery is what turns "an AI said
a number" into something an engineer can defend. The models will keep improving on their own.
The trust machinery is the part you have to build.

*Everything is public: inputs, prompts, the transcripts, the agents' models, the measured
values with citations, all three adversarial audits. https://github.com/charles-azam/ai-eng-bench. The deep-dives: [the cooling rig](https://charles-azam.github.io/blog/ai-predicts-nuclear-experiment), [the physics of the chimney, with an interactive calculator](https://charles-azam.github.io/blog/reactor-cools-itself),
[a billion tiny pressure vessels](https://charles-azam.github.io/blog/billion-tiny-pressure-vessels).*
