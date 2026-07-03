# Anticipated HN objections — prepared answers (comment-section kit)

**"It's in the training data."**
Addressed head-on in the article. Short version: the models *recognize* the facility but
demonstrably can't *recall* its measured values (refusal probes + forced-choice probes in
`repro/probes/`); the de-identified rerun scored equally well; all transcripts show zero web
access; and seven independent runs miss the same quantities in the same self-explained directions
— memorization doesn't produce consistent, physically-caused errors. Can I prove latent memory
never steered an assumption? No, and neither can anyone; that's why everything is published.

**"You gave it the answer via the 56 kWt duty."**
Partially true and disclosed prominently — our own adversarial audit found it. The duty pairing
encodes the facility's measured heater efficiency. Counterpoints: it's a legitimate design input
any engineer would receive; one run rejected it in favor of its own loss physics (and its numbers
moved exactly as predicted); and the temperatures/flow still require the whole radiation-network
+ buoyant-loop machinery to be right.

**"n=7 is not statistics."**
Correct. It's replication evidence, not a distribution: 7/7 runs produced working physics models,
7/7 called the accident transient right, 6/7 landed flow within ~4%. Run it yourself — the repo
reproduces the experiment for ~$3.

**"The best-run 0.2% hits are cherry-picked."**
They're luck, and the article says so explicitly ("judge the ensemble"). The audit forced this
framing and it's the honest one.

**"A grad student could do this."**
Yes — in a week or three, for a lot more than $3, and they'd be *checking* the same textbook
physics. The claim isn't superhuman insight; it's that competent, self-checking, from-scratch
engineering analysis became a 15-minute commodity. That's the story.

**"Why should I trust an AI audit of an AI?"**
You shouldn't, blindly — it's adversarial context-isolation, not divinity. The audit found 8
real problems including ones embarrassing to the author, which is the behavior you'd want. All
artifacts are public so the audit itself is checkable.

**"OpenFOAM in Docker isn't 'installing complex software'."**
The agent chose the pragmatic path an engineer would (and was told not to compile on a small
box). The CHT run then configured fvDOM radiation, k-ω SST, and invented a flux-ramping
continuation to converge a stiff coupled problem — that's the part that requires knowing what
you're doing, and it's in the case files.

**"This is just a wall and a chimney — try it on a real engineering problem."**
Fair. This was chosen precisely because a national lab published measured truth to grade
against. The harder claim (design, not analysis) is the next post.

**"What about [other vendor]'s model?"**
Not tested — this ran Claude only (Opus vs Sonnet ladder included). The repo prompt is
model-agnostic; PRs with other-model runs welcome.

**"You claimed the agent beat the national lab's code, then retracted it. Why should I trust
the rest?"**
Because the retraction is the system working as designed: a fresh-context adversarial audit
(published unedited, `httr/AUDIT.md`) caught the quantity mismatch and the nominal-vs-median
cherry-pick, and the claim died before publication. Every other number in the posts survived
the same treatment. Trust the process that killed the claim, not my first draft.

**"The xenon rerun knew it was ×7 off — that's the answer leaking in."**
Correct, and the addendum says so itself: it's a *mechanism-sufficiency test*, not a fresh
prediction. Knowing the gap is ×7 doesn't make xenon physics produce a ×10–13 delay at
standard nuclear-data values — that either falls out of the yields, half-lives, and flux, or
it doesn't. It did (band 1.8–21 h). The claim is "the audit's diagnosis is quantitatively
sufficient," never "the agent blindly predicted 7 hours."

**"Fable rejected your heat duty and got the worst ΔT of the campaign — so the newest model
is worse?"**
It made the *defensible* engineering call (trust your own loss physics over an unexplained
spec pairing) and paid for it against a rig whose real losses are larger than textbook
estimates suggest. One of seven Opus runs made the same call with the same result. That's a
judgment distribution, not a capability ranking — and it's exactly why the unit of analysis
is the ensemble.
