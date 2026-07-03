# The nuclear reactor that cools itself — with help from the weather

**TL;DR.** Modern high-temperature reactor designs can survive a total power blackout with a
safety system that has no pumps, no valves, no software, and no moving parts. It is, essentially,
a chimney. Argonne built a half-scale one to prove it — and discovered its performance changes
with the weather outside the building. Here's the physics, from scratch.

## The problem: heat that won't turn off

When a reactor shuts down, fission stops instantly — but the fuel keeps making heat, because the
radioactive fission products keep decaying. It starts around 6–7% of full power and fades over
days. You can't switch it off; you can only carry it away. Fukushima happened because the pumps
that carried it away lost power.

So the question every advanced-reactor design must answer: **where does the decay heat go when
everything electrical is dead?**

## The answer: a wall, a gap, and a chimney

The high-temperature gas reactor answer is the Reactor Cavity Cooling System, and it's almost
insultingly simple. The hot steel reactor vessel sits in a concrete cavity. Facing it, a few
feet away, stands a wall of hollow steel ducts, open to outside air at the bottom and connected
to a tall chimney at the top.

Two pieces of physics do all the work:

**1. Hot things glow.** Everything radiates heat as electromagnetic waves, at a rate that grows
as the *fourth power* of absolute temperature (Stefan–Boltzmann: q ∝ T⁴). At room temperature
it's negligible. But a vessel wall at 300–400 °C beams heat across the air gap like an open oven
door. No contact, no fluid, no fan — at these temperatures **radiation carries roughly 80–90% of
the heat** to the duct wall. The gap is doing almost nothing; the *glow* is the transport.

The fourth power is also the safety feature. If the vessel gets 10% hotter (in absolute
temperature), it radiates ~46% more heat. Heat removal accelerates *faster* than temperature
rises. That's a built-in negative feedback loop — a thermostat made of geometry.

**2. Hot air rises.** The air inside the ducts absorbs that radiated heat, warms by ~80–100 °C,
becomes lighter than the outside air, and floats up the chimney — pulling fresh cold air in
behind it. A 20-metre chimney with ~90 °C of warming generates a driving pressure of about
60 pascals. That's 0.06% of atmospheric pressure — yet it silently pumps roughly half a kilogram of air per second through the system,
day and night, for free, forever. (For scale: that's about the pressure your lungs make in
quiet breathing — driving the safety system of a nuclear plant.)

Chain them together and you get a machine with no parts: **glow across the gap, float up the
chimney.** The hotter the accident, the harder both mechanisms work.

**Don't take my word for it — [play with the physics yourself](rccs_calculator.html).** Drag the
heat load, the outdoor temperature, and the wind, and watch the airflow and wall temperatures
respond. The sliders drive a JavaScript port of the physics model the AI agents built and
validated against the measurements; it runs entirely in your browser.

## Proving it: a 26-metre rig in a building near Chicago

You don't license a nuclear plant on "trust me, hot air rises." Argonne National Laboratory
built NSTF — a half-scale slice of the real thing: a 220 kW electrically heated steel wall
playing the role of the hot vessel, twelve steel ducts, two chimneys through the roof, and
~400 sensors, run to nuclear QA standards for 33 months.

The centerpiece test: drive the heated wall with the exact decay-heat curve of a simulated
depressurization accident — 3.5 days of slowly climbing then fading heat — and watch. The wall
climbed to about 409 °C, flattened out *below* the steel limit, and came back down, tracking
the decay curve the whole way. The reactor mock-up saved itself, on camera, with no moving
parts.

![Decay-heat transient: the heat load rises for 3.5 days; the wall temperature follows, flattens below the limit, and turns over](figures/fig_accident_transient.png)
*(This particular plot was produced by an AI agent predicting the test — the companion article's story. The measured curve does the same thing, peaking at 408.7 °C.)*

## The surprise: the weather got a vote

Then the odd part. Argonne ran the *same* baseline test eight times over two years, and the
answers kept shifting: airflow varied by ~25%, duct temperatures by 30 °C. Identical rig,
identical power. The only thing that changed was the sky.

It makes perfect sense once you see it: the "pump" of this system is the density difference
between the hot air inside the chimney and the cold air outside the building. **In January,
outside air near Chicago is dense; the draft is strong. In July, it's light; the draft sags.**
The safety system literally runs better in winter. Wind matters too — gusts over the chimney
outlets add suction (growing as wind speed squared), and one windy start-up attempt actually
drove the flow *backwards*; the lab aborted that test and repeated it on a calmer day.

![Airflow and temperatures across the outdoor-temperature range — an AI agent's own weather sweep of this facility](figures/fig_weather_sweep.png)

None of this breaks the safety case — the vessel temperature barely notices, because the T⁴
radiation clamp dominates — but it means a passive system's performance envelope includes the
weather report. The lab ended up fitting a little formula for the no-power airflow:
ṁ = (5.53·ΔT + 3.75·V²)^(1/1.8) — temperature difference and wind speed in, kilograms of air
per minute out.

(A coda from the companion experiment: asked to *derive* such a formula blind from the geometry,
the AI produced ṁ = (20.5·ΔT + 6.25·V²)^(1/2) — the same structure, a wind term within ~10% of
the lab's fit, and a temperature term about 45% hot, having itself flagged the exact assumption
responsible. Six minutes, $1.37.)

## Why I'm telling you this

Two reasons. First, it's the most elegant piece of engineering I know of: a nuclear safety
system whose parts list is *a wall, a gap, and a chimney*, whose failure mode analysis is
"physics stops working."

Second: this experiment has something almost nothing else has — years of public, nuclear-grade
measured data of a system doing pure physics. Which made it the perfect exam question for a
different kind of test: whether an AI, given only the blueprints, could predict these
measurements from first principles. That's the companion article: [link to article 1].
