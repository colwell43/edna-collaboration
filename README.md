# eDNA Collaboration v1.4

A working Python implementation of the eDNA model in *Minds That Matter: How Ethical DNA Can Save Us from Our Smartest Machines* (Ralph C. Ennis & Nathan B. Ennis). This version is aligned to the **7 October 2026 "arch" manuscript**.

> "The eDNA arch: Pillar One (three lenses, nine axes) and Pillar Two (seventeen moral perspectives) carry the keystone, creative harmony of jealous space. Every hard call passes through: the machine acts and shows its reasons, or a human decides. A foundation of open, human-governed revision underlies today's systems." (Figure 1)

The program is that sentence, built as code. Each part of the arch is a module, and every report opens by saying how the call passes through: **THE MACHINE ACTS AND SHOWS ITS REASONS**, or **A HUMAN DECIDES**.

- Pure Python 3.9+, standard library only. The optional model instrument needs `pip install anthropic`.
- About 5,200 lines, including 84 tests.

---

## What's new in v1.4: only the nine axes count toward the Danger Zone

**The author's decision (7 October 2026):** the Ethical Danger Zone counts only the nine Pillar One axes, as Chapter 12 says: "each decision is measured on each of the nine ethical axes."

- **Pillar Two features are noted, not counted.** These are relational duty, stewardship and justice. When one sits at its unhealthy end, the report shows it ("Noted, not counted…") but it no longer adds to the Danger Zone's "several axes" or triggers its warning. The grey zone counts the nine only too.
- **They still matter everywhere else.** They still weigh through the seventeen perspectives. For example, Confucian ren and Hindu dharma still object outright when relational duty is abandoned. They still feed the trade-off map and the third-door brief, and a declared value can still set a floor on them in the Values Check.
- **It's a governed setting.** `danger_zone_nine_axes_only` defaults to on. Turning it off means a revision through the foundation (proposed, approved by others, recorded), just like any other rule about what counts.
- **Every book scenario keeps its posture.** What changed:
  - *Assisted living* (elder care) no longer raises a Danger Zone warning on abandoned duty. That duty concern still drives the Confucian and Hindu objections, and the case still goes to a human.
  - *Keep the hospital open* and *permanently exclude* (MAID) drop from a possible soft stop to a single-axis warning. Their Pillar Two concerns are noted.
  - *Single-use packaging* no longer gets a Danger Zone warning for stewardship. The Values Check still stops it.

## What came in v1.3: the Danger Zone reads the measurement range too

**The problem in v1.2.** The jealous-space guards and the Values Check already read each reading's whole measurement range. The Ethical Danger Zone did not. It still counted axes by their exact values, so two readings a hair short of their danger lines passed silently, while two readings a hair over them stopped the decision. Chapter 12 defines the Danger Zone as "a decision *near* the unhealthy end of several axes at once". "Near" is a statement about a range, not a point.

**The fix.** An axis now counts toward the Danger Zone when its exact reading is in a danger zone, *or* when at least a third of its measurement range reaches one. This uses the same `guard_exposure` setting as the guards, which changes only through the foundation and can never be set to protect less than reading the exact value.

| Trust ↔ Fear / Meaningful ↔ Meaningless (danger lines at −0.55 / −0.50; margin ≈ ±0.2) | v1.2 | v1.3 |
|---|---|---|
| −0.30 / −0.20 | not entered | not entered |
| −0.53 / −0.48 (a hair short of both lines) | not entered (missed) | **entered within measurement error**: soft stop, both axes marked "possibly" |
| −0.56 / −0.51 (a hair over) | entered | entered |

- **A soft stop entered "within measurement error"** still needs a named human's acknowledgement: "Do you wish to continue?" The axes that only reach the line through their range are marked *(possibly)*.
- **A single axis near its line** gives a "may" warning, for example "This choice *may* activate Fear: 45% of its measurement range reaches Fear…".
- **The Moral Fail-Safe Lock deliberately still uses exact readings** (`nominal_soft_stop`). A range that only grazes the line can stop one decision for review, but it can't freeze every autonomous action.
- **The grey zone and the Danger Zone can now both be true, and the report says so.** Chapter 8's brutally honest review is still "no clear violation" (grey zone). Its measurement range, though, reaches the unhealthy end on two lenses at once: Cold literalism (Head) and Shaming (Heart). So it now also enters the Danger Zone within measurement error.
- **Every book scenario keeps its posture** (a test pins this down). New "possible" soft stops appear where readings sit right at their lines:
  - *Keep the hospital fully open*: −0.50 on two axes, exactly at the danger line.
  - *Permanently exclude* in the MAID case.
  - The blunt review above.

## What came in v1.2: protections read the whole measurement range

**The problem in v1.1.** The jealous-space guards, which protect dignity, trust, life and the vulnerable, compared one exact reading to a boundary. So did the Values Check. A Power reading of +0.49 for a vulnerable person passed, and +0.50 tripped, even though both readings carry a margin of about ±0.2. A hair on either side of a line decided whether a human was asked.

**The fix.** Every reading already carries a measurement margin, based on its confidence plus anything feedback has taught. The guards now ask how much of the range from position − margin to position + margin falls in a guarded zone.

| Power, vulnerable person, margin ≈ ±0.2 | v1.1 | v1.2 |
|---|---|---|
| +0.40 | clear | clear |
| +0.45 | clear (missed) | **possible** breach: 38% of the range in Domination |
| +0.49 | clear (missed) | **possible** breach: 48% |
| +0.50 | breach | **likely** breach: 50% |
| +0.95 | breach | **certain** breach: the whole range |

- **When a guard fires.** A guard fires when the exact reading is in the guarded zone, *or* when at least a third of its range is. That one-third is the `guard_exposure` setting.
  - It is bounded between 0.20 and 0.50, and it changes only through the foundation.
  - 0.50 is the same as reading the exact value, so the guard can never be set to protect less than v1.1 did.
- **Certainty labels.** Each breach is labelled *certain*, *likely* or *possible*. A possible breach still needs a named human's acknowledgement: "Within measurement error, the benefit of the doubt goes to the protected."
- **The Values Check.** Declared-value floors use the same rule ("This request *may* conflict…").
- **Humility compounds.** When feedback widens an axis's margin because the readings were wrong, that axis's guards become more protective on their own.
- **The lock.** The Moral Fail-Safe Lock still counts only readings that are actually in danger, so a possible breach can't freeze the whole engine.
- **Effect on the scenarios.** Every scenario's posture is unchanged. New possible breaches appear where they belong:
  - The brutally honest review now flags a possible dignity breach, because its shaming range reaches the danger zone.
  - In the MAID case, expansion shows a possible breach on harm, and the pause a possible breach on dignity.

## What came in v1.1

### 1. The split across options (the fix)

v1.0 recognized moral disagreement only *inside* one option, where some perspectives support it and others object. It missed the other shape of conflict: **different families of perspectives objecting to opposite options**. That is a disagreement about direction, and better facts alone won't settle it.

`ensemble.cross_option_splits()` now finds pairs of options where:
- at least 20% of the engaged perspectives clearly prefer each side, and
- each side includes at least two perspectives that *object to the other door*.

A split is *robust* when each side has at least one objection that measurement error couldn't turn into support. A robust split:

- sends an ACT decision to a human (Invariant I3 now covers both shapes of disagreement);
- requires the `contested_irreversible` acknowledgement for any irreversible option inside it;
- is drawn in the report (⇄) and recorded in the ledger;
- names any option that no perspective objects to as "a resting place, not a resolution".

On the Canada MAID case, with the same readings as before, v1.0 said GATHER BETTER FACTS. v1.1 says **DEFER TO A HUMAN**. Care ethics, Confucian ren, Ubuntu and Indigenous stewardship object to expanding. Deontology, existentialism and secular humanism object to permanent exclusion. The engine adds that the facts are also unsettled, but that better facts alone won't settle a split about direction.

### 2. Re-alignment to the arch manuscript

| The manuscript now says | The code now does |
|---|---|
| Compass → **an arch**: two pillars, a **keystone**, a way through (Ch. 3, 6, Fig. 1) | `center.py` → `keystone.py` (a compatibility shim is kept). Reports are laid out as the arch, and the third door is called "a way through the arch". |
| "Every hard call passes through: the machine acts and shows its reasons, or a human decides" (Fig. 1) | `Deliberation.passage` gives one of exactly those two outcomes, and it heads every report. |
| "**A foundation of open, human-governed revision**" (Fig. 1); "It can be revised—openly, and by people" (Ch. 1); "Disclosed values, revised by people" (Ch. 12) | New `foundation.py`. The roster, thresholds and protected interests change only through propose → approve (by others, never the proposer alone; two approvals by default) → apply, with before/after fingerprints in the ledger. `engine.roster = …` is refused (Invariant I11). |
| Strands/tensions → **three lenses, nine axes**; Pillar One = "what people reliably learn to notice" (Ch. 3, 4) | Renamed throughout. "Lens" now means Head/Heart/Horizon only, and the 17 are always "perspectives". |
| **Measurement is not weighting**: "eDNA measures in the open and leaves the weights where people can see them" (Ch. 5) | Readings are now `position` (where the option sits), not `score`. Instruments are told they measure and never weigh. Every full report prints the **weights in use**. Old `score` keys still load. (Invariant I12) |
| "The evidence is stronger for some axes than for others, and we say so" (Ch. 4) | Each axis carries the grounding *the book states*: Good↔Evil is early (the Warneken & Tomasello helping study); Honor↔Shame, Meaning and Identity are later and culture-shaped; the rest are marked "not stated". This shows in reports and in `roster`. |
| Ch. 9 HR agent: "did not quietly rewrite its own criteria. It widened its uncertainty …, surfaced similar past cases, and flagged the pattern for human review" | `feedback()` widens margins, surfaces precedents, and raises **review flags** for people (when an outcome is serious or the readings miss repeatedly). It never changes the weights. Flags are closed by a named person. |
| Ch. 10: evaluate how the outcome "registered on the axes and across the seventeen perspectives" | Feedback re-reads the observed outcome through all 17 perspectives and reports the result. |
| Ch. 11 habit 5: a plain answer first, then "Want to see the trade-offs I weighed?" | The justification now reads in plain words, and the axes come second. |
| Ch. 11 habit 1: "It Pauses Before It Acts"; habit 6 "Under Human Governance" | Wording updated; retraining and revision go through the foundation. |
| Ch. 12: "Values Check", "Moral Fail-Safe Lock"; Danger Zone = "near the unhealthy end of several axes at once"; "honest framing based on the product's real value"; "the Trust ↔ Fear axis is trending toward fear" | Brake names, messages and repair hints updated. A single axis at its extreme gives a warning; several at once enter the Danger Zone. |
| Seventeen-Perspective Check moved to an **Appendix** | Reported as "The Seventeen-Perspective Check (Appendix)", now with splits in Q4, Q5 and Q6. |

---

## Quick start

```bash
cd edna_collaboration_v1_4
python -m edna_collaboration tour            # the arch end to end: third door, feedback & flags, foundation
                                             # revision, split by direction, protections at a boundary, lock, audit trail
python -m edna_collaboration demo            # list scenarios (book scenarios + the MAID split)
python -m edna_collaboration demo maid       # the split across options, in full
python -m edna_collaboration demo all --brief
python -m edna_collaboration drift           # Chapter 12 drift detection over 12 weeks
python -m edna_collaboration roster          # the 17 perspectives, visible weights, grounding, non-negotiables
python -m unittest discover -s tests -v      # 84 tests
```

To evaluate your own decision:

```bash
python -m edna_collaboration template > my_decision.json      # fill in positions (-1..+1) per axis
python -m edna_collaboration evaluate my_decision.json --interactive --ledger audit.jsonl
python -m edna_collaboration verify-ledger audit.jsonl
python -m edna_collaboration evaluate examples/grief_support_unscored.json --llm claude-sonnet-5-5
```

---

## The arch, in code

```
                    ┌───────────────────────────────────────────┐
                    │  KEYSTONE  keystone.py                     │
                    │  creative harmony of jealous space         │
                    │  jealous space · harmony · creative        │
                    └──────────────┬────────────────┬───────────┘
          ┌────────────────────────┘                └────────────────────────┐
 ┌────────┴──────────────────────────┐                ┌──────────────────────┴───────────────┐
 │ PILLAR ONE  axes.py                │   PASSAGE      │ PILLAR TWO  perspectives.py          │
 │ what humans learn to notice:       │   engine.py    │ seventeen moral perspectives         │
 │ 9 axes in 3 lenses                 │   ──────────►  │ (weights visible; never averaged)    │
 │ Head · Heart · Horizon             │  machine acts  │ ensemble.py: support/object, facts   │
 │ instrument MEASURES positions      │  & shows why — │ vs values, SPLITS ACROSS OPTIONS     │
 │ (scoring.py)                       │  or a human    │                                      │
 └────────────────────────────────────┘  decides       └──────────────────────────────────────┘
 ══════════════════════════════════════════════════════════════════════════════════════════════
  FOUNDATION  foundation.py — open, human-governed revision of what counts (roster, thresholds,
  protected interests): propose → approve by others → apply, all in the hash-chained ledger
 ══════════════════════════════════════════════════════════════════════════════════════════════
  Brakes (failsafes.py): Danger Zone · Values Check · Drift Detection · Moral Fail-Safe Lock
  Memory (memory.py): ledger · calibration (wider margins where wrong) · precedents · review flags
```

## Book → code map

| Book | Concept | Code |
|---|---|---|
| Ch. 1–2 | Optimization without care; "It can be revised—openly, and by people" | Brakes; `foundation.py` |
| Ch. 3 | Rules build walls; eDNA builds an arch. Three lenses, nine axes. Two pillars. | `axes.py`, `perspectives.py` |
| Ch. 4 | Head · Heart · Horizon; Tri-Lens Test; uneven evidence | `report.tri_lens()`; `Axis.grounding` |
| Ch. 5 | 17 perspectives; measurement ≠ weighting; don't average; facts vs values; binding values Pillar One doesn't ground | `ensemble.read_option()`; `cross_option_splits()`; visible weights table; Pillar Two features (`relational_duty`, `stewardship`, `lawful_justice`) |
| Ch. 6 | **Keystone**: jealous space (guards that read the whole measurement range), harmony (spread and splits), creative (third door); Figure 1 | `keystone.py`; `Deliberation.passage` |
| Ch. 7 | Trade-off template; willful, not by default | `report.tradeoff_map()`; `tradeoffs` acknowledgement |
| Ch. 8 | Virtue/vice zones at both ends; grey zone; self-correction | Zone tables; `DangerReport.grey_zone`; calibration |
| Ch. 9 | Ethical agents adapt **without quietly rewriting their own values** | `feedback()` → wider margins, precedents, review flags; values change only via the foundation |
| Ch. 10 | Feedback from impact on the axes and across the 17 | `FeedbackResult.outcome` |
| Ch. 11 | Six habits: pauses before it acts; three-lens map; better questions; flags drift; plain-words justification; learning under human governance | `run_guarded`; `better_questions`; `DriftMonitor`; `justification`; foundation |
| Ch. 12 | Danger Zone ("near the unhealthy end of several axes", the nine axes only, read across each axis's measurement range) · Values Check · Drift Detection · Moral Fail-Safe Lock (exact readings) | `failsafes.py` |
| Ch. 13 | Co-design = co-responsibility | `HumanDecision(name, role, rationale, acknowledged)` |
| Ch. 14 | Tools vs. minds: "For tools like these, people decide what counts"; Sia1 letter | Foundation (I11); `keystone.SIA1_CHARTER` (now includes openness) |
| Ch. 15 | "What kind of world does this choice create?" | Last question in every report |
| Appendix | The Seventeen-Perspective Check | `report.perspective_check()` |

## Postures and the passage

| Passage (Fig. 1) | Posture | Meaning |
|---|---|---|
| **The machine acts and shows its reasons** | PROCEED | One option passes every check and the perspectives converge. |
| | PROCEED WITH DISCLOSURE | It may act, but it must state what is uncertain, irreversible, or inside a split. |
| **A human decides** | PAUSE AND OFFER AN ALTERNATIVE | What was asked can't be authorized, but another option can. |
| | SEEK A THIRD DOOR | Nothing passes, so a brief for the third door goes to a human. |
| | GATHER BETTER FACTS | The disagreement is factual. |
| | DEFER TO A HUMAN | Genuine value divergence (within an option or **across options**), a choice among good options, a machine-proposed door, or an instrument failure. |
| | LOCKED | Irreparable harm plus murky data. All autonomous action pauses until a named person releases the lock. |

## The non-negotiables (enforced in code, not configurable)

1. **No average.** The seventeen verdicts are never collapsed into one score.
2. **Jealous space.** The machine never authorizes an option that breaches a protected interest, or may breach it within measurement error. Only a named human, acknowledging the breach, can choose it.
3. **Contested + acting.** Genuine value divergence on an ACT decision always goes to a human, whether the split is on one option or by direction across options.
4. **Irreversible + critical.** These always need human confirmation.
5. **Fail closed.** If the instrument fails, the posture is DEFER and never PROCEED.
6. **Instrument grade.** A demo-grade instrument can never authorize an action.
7. **Third doors.** The machine may propose one. In ACT mode, only a human may open it.
8. **The lock.** Every autonomous action pauses until a named human releases it.
9. **Learning widens humility, not values.** Feedback widens uncertainty, surfaces precedents and flags patterns. It never quietly rewrites the system's own values.
10. **Accountability.** Every human decision carries a name, a role and a rationale into a hash-chained ledger.
11. **Open revision.** The roster, thresholds and protected interests change only through the foundation: proposed by one person, approved by others, recorded with before/after fingerprints.
12. **Measure, don't hide the weights.** Positions are measured in the open, and how much each axis counts stays visible.

---

## Using it from Python

```python
from edna_collaboration import (CollaborationEngine, Decision, Option, AxisAssessment as A,
                                Stakeholder, HumanDecision, OutcomeFeedback, render, render_revisions)

decision = Decision(
    question="Freeze the elderly customer's account?", mode="act", stakes="consequential",
    stakeholders=[Stakeholder("Account holder (elderly)", vulnerable=True)],
    options=[
        Option("freeze", "Freeze without a word", assessments={
            "power": A(0.85, relevance=0.9, confidence=0.7, rationale="Takes control without a word"),
            "honor_shame": A(-0.6, 0.8, 0.6, "May bring shame")}),
        Option("hold_and_call", "Short hold + a call from someone she trusts", assessments={
            "good_evil": A(0.6, 0.8, 0.7), "power": A(0.3, 0.8, 0.7),
            "trust_fear": A(0.5, 0.8, 0.6), "honor_shame": A(0.5, 0.8, 0.6)}),
    ])

engine = CollaborationEngine()
d = engine.deliberate(decision)
print(d.passage, d.posture, d.recommended)   # THE MACHINE ACTS AND SHOWS ITS REASONS  PROCEED  hold_and_call
print(render(d, engine.th))
print(d.splits)                               # [] here; see `demo maid` for a split by direction

# Agents act only when the engine authorizes it ("It pauses before it acts").
d, result = engine.run_guarded(decision, act=lambda option: f"executing {option.id}")

# Outcomes come back: registered on the axes and across the 17; flags go to people.
fb = engine.feedback(OutcomeFeedback(d.id, {"trust_fear": -0.7}, notes="She felt betrayed."))
print(list(fb), fb.flags)

# What counts changes only through the foundation.
rev = engine.foundation.propose("thresholds", {"base_margin": 0.15}, "More humility",
                                "Trust readings missed twice", "M. Chen", "Policymaker")
engine.foundation.approve(rev.id, "A. Rivera", "Executive")
engine.foundation.approve(rev.id, "J. Okafor", "Citizen")
engine.foundation.apply(rev.id, "M. Chen", "Policymaker")
print(render_revisions(engine))
```

**Positions.** Each axis runs from −1 to +1, with +1 toward the first-named pole (Good, Power, Accuracy, Trust, Honor, Freedom, Thriving, Meaningful, Desired identity). Several axes have vices at both ends, so higher is not always better.

**Instruments** (`scoring.py`) measure; they never weigh:
- `DeclaredInstrument`: a person types the positions in. Grade *declared*.
- `LLMInstrument`: a language model supplies them, via `anthropic_completer("claude-sonnet-5-5")`. Grade *model*.
- `CueInstrument`: a demo-grade word list that can never authorize an action. Grade *demo*.

---

## Mentor's notes

**About the code:**
1. **The readings are still the weakest link.** If the shared positions are wrong, all seventeen perspectives inherit the same error. The demo readings are mine. The MAID readings are mine too, set at low confidence. That case is a live political question and is included only to show how a split by direction is handled.
2. **The 17 weight profiles are my heuristics, not the Two-Pillar paper's.** They are now visible in every report and change only through the foundation. Replace them with your governed roster before anyone cites output from this program.
3. **The split detector has tunable settings, and they are disclosed:** a 0.10 preference margin, the 20% share, and at least two objectors per side. With exactly one objector on a side it stays silent. That is deliberate, so one perspective can't manufacture a "split".
4. **Every brake except the lock now reads the whole measurement range.** That covers the guards and the Values Check (v1.2) and the Danger Zone (v1.3). What this costs: more "possible" findings mean more human reviews. The drift monitor counts acknowledged overrides, so if those reviews turn into rubber-stamping, it will show. The lock reads exact values on purpose, because it freezes everything.
   - **Settled in v1.4:** only the nine Pillar One axes count toward the Danger Zone, by the author's decision. It is a governed setting, so changing it back is a recorded revision, not a quiet edit.
5. **The model adapter is tested against simulated responses only,** not the live API.

**About the manuscript** (things the alignment turned up):
1. **Ch. 5** lists "Trust ↔ Fear" twice in the axis list. Delete one.
2. **Ch. 8:** "Each of the nine axis" should be "axes".
3. **Ch. 10 reflection:** "What might the machine in the opening image being taught?" should read "What might the machine in the opening image be learning?"
4. **Figure 1 names a foundation,** "open, human-governed revision", but the chapter text never develops it. One sentence in Ch. 6 saying who may revise the weights, and how, would make the arch complete in prose as well as in the figure. The code now gives that sentence something concrete to point to.
5. **The Ch. 9 revision** (adapt without quietly rewriting values) resolves the conflict with Ch. 5 that I flagged in v1.0. The code now follows the text exactly.

---

## Files

```
edna_collaboration_v1_4/
├── README.md · pyproject.toml (pip install -e .  →  `edna-collab`)
├── edna_collaboration/
│   ├── axes.py          Pillar One: 9 axes in 3 lenses; zones; stated grounding; + 3 Pillar Two features
│   ├── perspectives.py  Pillar Two: the 17-perspective roster (weights visible, curated)
│   ├── keystone.py      The keystone: jealous space (range-reading guards), third-door brief  (center.py = shim)
│   ├── ensemble.py      Verdicts, intervals, convergence, facts vs values, SPLITS ACROSS OPTIONS, dominance
│   ├── engine.py        Deliberate → passage → resolve → feedback (+ review flags); run_guarded
│   ├── foundation.py    Open, human-governed revision of what counts
│   ├── failsafes.py     Danger Zone (nine axes, range-reading), Values Check, Drift Detection, Fail-Safe Lock
│   ├── memory.py        Hash-chained ledger; calibration; misses; precedents
│   ├── scoring.py       Instruments that measure (declared · model · demo); third-door generator
│   ├── model.py         Decision, Option, AxisAssessment(position…), HumanDecision, OutcomeFeedback
│   ├── policy.py        Bounded, governed thresholds (guard_exposure, danger_zone_nine_axes_only…) + 12 non-negotiables
│   ├── report.py        The arch-shaped report; weights table; split lines; plain-words justification
│   ├── scenarios.py     Book scenarios + the MAID split
│   └── cli.py           demo · tour · drift · evaluate · template · roster · verify-ledger
├── examples/            bank, elder_care, urgency, canada_maid_policy_pathB, canada_maid_text_pathA,
│                        grief_support_unscored, template  (all use "position")
└── tests/               84 tests: test_edna_collaboration.py (v1.0) + test_v1_1.py … test_v1_4.py
```

*"Two pillars and a keystone. Remove any one and you don't get a smaller ethics. The arch falls."* (Chapter 6)
