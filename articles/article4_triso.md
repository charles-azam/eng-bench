# A billion tiny pressure vessels: AI vs. the fuel that cannot melt

**TL;DR.** TRISO nuclear fuel puts every uranium kernel inside its own poppy-seed-sized
containment vessel — a reactor holds billions, and safety is a *statistical* property. The
IAEA's fuel benchmark collects furnace tests where irradiated fuel spheres were held at
1600–1800 °C while a detector counted individual particle failures. I gave five AI agents the
test conditions and a materials annex — fully offline, answers held out — and asked them to
predict the failures. They called every zero-failure case correctly, under-predicted the
1800 °C carnage for a reason the annex itself explains, and reproduced the nuclear industry's
own documented prediction biases with unsettling fidelity. An adversarial AI audit then caught
me overselling several findings; its corrections are applied here and its report is published.
Everything: https://github.com/charles-azam/ai-eng-bench.

## The most paranoid fuel ever designed

A TRISO particle is a 0.5 mm uranium-oxide kernel wrapped in four layers: a porous carbon
buffer (crush space for fission gases), a dense inner carbon shell, a **silicon-carbide
pressure vessel** ~35 microns thick, and an outer carbon jacket. The kernel splits atoms; the
gases those fissions produce build pressure — hundreds of atmospheres at accident temperatures
— and the SiC shell holds it. Forever, ideally.

The design's elegant trick: under neutron irradiation the carbon layers *shrink*, squeezing
the SiC into compression like a shrink-wrapped barrel hoop. The gas pressure must first undo
that squeeze before the shell even feels tension. And because a reactor contains ~10⁹
particles, the safety question is never "does it fail?" but "what *fraction* fails?" — answered
in Weibull statistics, the mathematics of the weakest link.

To license this fuel, labs did the brutal thing: irradiate spheres containing ~15,000 particles
each for years, then bake them in a furnace at accident temperatures for weeks, watching for
each particle failure via its krypton-85 puff. The measured drama, from the IAEA's
benchmark archive: one sphere spent **500 hours at 1600 °C — zero failures out of 16,400.**
Its sister sphere went to **1800 °C: ten to twelve failures within a hundred hours** — the
benchmark's own analysis places ten of them at hours 50, 55, 65, 70, 75... of the exposure,
read off the krypton release curve. A cliff, between twins.

## The experiment

I gave the conditions of five such furnace tests — the two sister spheres, a staged
1600→1700→1800 °C test, and a pair of compacts differing mainly in burnup — to five autonomous
AI agents (three Claude Opus runs, one Sonnet, one Fable 5), along with the benchmark's own
material-property annex: layer geometries with manufacturing scatter, Weibull strength
parameters, creep and swelling correlations, diffusion coefficients. Everything a fuel
modeler gets. **Not** included: any measured outcome. The runs were fully offline — web tools
kept off the launch allowlist (a headless run can't grant itself permissions), and the
published transcripts confirm zero web calls.

Each agent built its model from scratch (Booth diffusion for gas release, thin-shell stress,
Weibull failure statistics, some with full time-marching), in 8–23 minutes, for $1.7–5.4 per
metered run (that range includes the transcript-backed rerun described below).

## What they got right, and the beautiful way they got it wrong

**All five agents called the zero-failure cases correctly** — the 1600 °C sphere and the
low-burnup compact: ten zero-verdicts, ten correct. All five got the temperature ranking
(1800 ≫ 1600 °C) right, and every run that predicted nonzero compact failures got the burnup
ordering right (one, predicting zero for both compacts, expressed no ordering). The ones asked
about timing placed the failures in the right phase of the staged test — "mostly in the final
300-hour 1800 °C hold" — which is exactly where all five measured failures occurred.

**And every single agent under-predicted the 1800 °C sister sphere** — by factors of 8 to
450. This is the most instructive result, because the *reason* is visible in their
calculation notes: given a pressure-vessel property annex, they computed pressure-vessel
physics, correctly — SiC stresses come out at 14–38% of the shell's strength, and on a
Weibull curve that means essentially nothing bursts. Which is true! The real killer at
1800 °C is something else: slow thermal degradation of the silicon carbide itself — a
mechanism that simply *was not in the annex*. Handed incomplete physics, the agents faithfully
produced the incomplete answer. (A disclosure that flatters them: the benchmark's own reference
codes never predicted these failure counts at all — the counts were imposed as boundary
conditions in their post-test calculations. The agents attempted a strictly harder task.)

What separates the models is what they did about the gap (wording here audited and
corrected): the **Fable 5** run *coded* a decomposition mechanism it reasoned should exist —
anchoring it, admittedly, on general TRISO knowledge beyond the annex — and overshot the
staged case ×60 while nailing its phase placement. One **Opus** run declined to code anything
but attached a self-described low-confidence "0–5 failures" judgment band whose upper edge
happened to touch the measured 5 — and whiffed the other two nonzero cases. The rest reported
the pressure-vessel answer as-is. Code the missing physics, band it, or decline: three
engineering temperaments, all visible, none of them right.

A coda that keeps me honest about "temperaments": when I later reran Fable 5 on the same frozen
pack (on the VPS this time, with a full published transcript), it *didn't* code a mechanism —
it took the banding path instead, and its "0–5, most likely the final phase" call on the staged
test landed like the Opus one — while its 1800 °C caesium swung the other way entirely (×150
*under* the measurement, a second counter-example to the "accurate when hot" pattern below).
Same model, same inputs, different engineering personality. These are sampled behaviors, not
fixed model properties — one more reason to run ensembles and judge distributions, not single
runs.

## The mirror

The strangest finding is in the caesium numbers. Cs-137 seeps by solid-state diffusion through
even *intact* SiC — that's why it matters for contamination — and the benchmark's own report
records that the professional fuel-performance codes are decent on hot 1800 °C tests but
**overpredict caesium release on 1600 °C tests by an order of magnitude or more**.

The agents, using the community's own diffusion correlations from the annex: the three runs
reporting the 1800 °C sphere landed within ×1.2–1.9 of measurement; the staged case came out
×3–12 high (where the professional codes were also specifically bad); and the 500-hour 1600 °C
sphere came out one to three **orders of magnitude high** — four runs out of five, with one
contrarian (Sonnet) that under-predicted instead.

An agent is a mirror. Give it a field's data and correlations, and it returns the field's
blind spots — a tendency, not a law, but a striking one. If you want AI to beat the
state of the art in fuel performance, the bottleneck isn't intelligence; it's that the
published correlations *are* the state of the art, biases included.

## What no model could see

The measured data holds one more lesson. The 1800 °C sister sphere failed more particles in
100 hours than the staged sphere did in 400 hours at the same final temperature. Same particle
design family — the pack even lists them as different production batches with slightly
different geometry. The plausible explanation (a hypothesis, not an established cause) is that
the batches *behaved* differently — and how a batch behaves is information that exists in no
spec sheet and no property annex. Physics models, human or AI, predict the *design*; reality
tests the *product*. That gap is why the furnaces will stay busy no matter how good the models
get.

## The trust part

Same machinery as the previous experiments: answers held out, transcripts published (zero web
calls — grep them; one evidence gap disclosed: the *original* Fable 5 run executed as a local
subagent without a transcript, which is why the VPS rerun above exists — that one's transcript
is in the set), recall probes showing the models *cannot* retrieve these measured values from
memory (0/4 on forced-choice questions with the truth deliberately off-center; both probed
models refuse the open question), and a fresh-context adversarial AI audit of my claims. The
audit re-ran all five agents' models itself, verified nothing was hardcoded and no input
leaked — and then caught me overselling the "invented mechanism" story, mislabeling a judgment
band as a calibrated bracket, and quietly omitting the one run that contradicted my bias
narrative. All corrected above; the unedited audit is in the repo. My claims got more modest
and more true. That's the process working.

## The bill

Six runs in the end: **$15.8 across the five metered ones** (the original Fable run executed
as an unmetered local subagent; its VPS rerun cost $5.44), 8–23 minutes each, on a €30/month
VPS, fully offline.

*Part of a series: [the passive cooling rig a national lab measured for 33 months](https://charles-azam.github.io/blog/ai-predicts-nuclear-experiment),
[the physics of reactors that cool themselves](https://charles-azam.github.io/blog/reactor-cools-itself),
and [the whole week — including a real reactor's self-rescue, predicted from computed
neutronics](https://charles-azam.github.io/blog/ai-engineering-department). Everything public:
https://github.com/charles-azam/ai-eng-bench.*
