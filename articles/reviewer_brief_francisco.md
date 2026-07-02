# Reviewer brief — Francisco (domain review before publication)

Salut Francisco — before this goes on HN I need your nuclear-engineer eyes on three specific
things. Time budget: ~45 min. Everything is in the repo (`repro/`) and two short articles.

## What happened (30 s)
Claude, running autonomously on a VPS, was given the geometry/materials/BCs of Argonne's NSTF
(½-scale air-cooled RCCS) and asked for a calculation note. Across 6 archived Opus runs it
predicted the measured baseline within: flow ±4% (5/6), plate −8…+8%, wall −17…+20%, ΔT
+14…+31% (systematic, duty-input-driven). All runs called the DCC accident transient "bounded,
levels off" (measured: peaked 409 °C, turned over). One run installed OpenFOAM and cross-checked
with fvDOM radiation, temperatures solved as outputs. An adversarial AI audit of my claims is
published unedited in `repro/AUDIT.md`.

## The three things I need from you

1. **Physical legitimacy.** Read one calculation note — `repro/runs/run_cht/calculation_note.md`
   (the best one). Is the modeling defensible to a nuclear thermal-hydraulics reviewer? Any
   embarrassing error I've missed? Would *you* sign this as a first-pass scoping calc?
2. **The ΔT story.** The agents put the stated 56 kWt duty into the air; measured ṁ·c_p·ΔT is
   ~48.6 kW while the report's Table 32 lists 56.12 kWt removed. Is my framing right that this
   is a known energy-accounting ambiguity in such facilities, or am I miscounting something?
   (`repro/scoring/scorecard.md`, first section.)
3. **Overselling check.** Read `articles/article1_final.md` (~2,000 words). As someone who does
   this for a living: where would you wince? What claim would you weaken or kill?

## Known limitations already disclosed (don't burn time re-finding these)
Duty input encodes the measured heater efficiency; best-run 0.2% hits are luck within ±5–10%
bands; radiative fraction over-predicted in all runs (0.89–0.97 vs ~0.80); one early run's
artifacts lost; models recognize the facility (though they can't recall its data); wind coupling
low-confidence everywhere.

Merci! — Charles
