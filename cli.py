"""
Command line for eDNA Collaboration v1.4.

    python -m edna_collaboration demo                 list the book scenarios
    python -m edna_collaboration demo bank            run one (or: demo all --brief)
    python -m edna_collaboration tour                 guided walkthrough of the arch: pillars, keystone,
                                                      passage, brakes, memory, foundation
    python -m edna_collaboration drift                drift detection on a news recommender
    python -m edna_collaboration evaluate FILE.json   evaluate your own decision
          [--interactive] [--json] [--brief] [--ledger PATH] [--llm MODEL | --cue] [--roster PATH]
    python -m edna_collaboration template             print a decision template (JSON)
    python -m edna_collaboration roster [--export P]  show / export the seventeen-perspective roster
    python -m edna_collaboration verify-ledger PATH   check the audit trail's hash chain
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .engine import AcknowledgementRequired, CollaborationEngine, Deliberation
from .foundation import RevisionError
from .memory import MoralLedger
from .model import ROLES, AxisAssessment, Decision, HumanDecision, Option, OutcomeFeedback, Stakeholder
from .perspectives import Roster
from .report import render, render_resolution, render_revisions, render_roster, split_lines
from .scenarios import SCENARIOS, hospital, drone, news_drift_series


def _engine(args, gen=None) -> CollaborationEngine:
    instrument = None
    if getattr(args, "llm", None):
        from .scoring import LLMInstrument, LLMThirdDoorGenerator, anthropic_completer
        comp = anthropic_completer(args.llm)
        instrument = LLMInstrument(comp, args.llm)
        gen = gen or LLMThirdDoorGenerator(comp)
    elif getattr(args, "cue", False):
        from .scoring import CueInstrument
        instrument = CueInstrument()
    roster = Roster.from_json(args.roster) if getattr(args, "roster", None) else None
    ledger = MoralLedger(args.ledger) if getattr(args, "ledger", None) else None
    return CollaborationEngine(roster=roster, instrument=instrument, third_door=gen, ledger=ledger)


def cmd_demo(args) -> int:
    if not args.name:
        print("Scenarios from Minds That Matter (run: python -m edna_collaboration demo <name>):\n")
        for k, (title, _) in SCENARIOS.items():
            print(f"  {k:<15} {title}")
        print("\n  all             run every scenario")
        return 0
    names = list(SCENARIOS) if args.name == "all" else [args.name]
    for n in names:
        if n not in SCENARIOS:
            print(f"unknown scenario '{n}'", file=sys.stderr)
            return 2
        decision, gen = SCENARIOS[n][1]()
        eng = _engine(args, gen)
        d = eng.deliberate(decision)
        print(render(d, eng.th, "brief" if args.brief else "full"))
        print()
    return 0


def cmd_tour(args) -> int:
    say = lambda s="": print(s)  # noqa: E731
    say("eDNA COLLABORATION v1.4 — A GUIDED TOUR OF THE ARCH\n")
    say("Two pillars carry a keystone. Every hard call passes through it: the machine acts and shows its")
    say("reasons, or a human decides. Underneath: a foundation of open, human-governed revision.\n")

    say("STEP 1 — The hospital (Ch. 3/5/6). No door passes, so the machine looks for a third door,")
    say("finds one, and hands it to a human.")
    decision, gen = hospital()
    eng = CollaborationEngine(third_door=gen)
    d = eng.deliberate(decision)
    print(render(d, eng.th, "brief"))

    say("\nSTEP 2 — A human tries to open the third door without acknowledging what they are choosing...")
    try:
        eng.resolve(d, HumanDecision("phased_conversion", "Dr. A. Rivera", "Executive",
                                     "Keeps emergency care; community at the table."))
    except AcknowledgementRequired as e:
        say(str(e))
    acks = [a.code for a in d.analyses["phased_conversion"].acks]
    res = eng.resolve(d, HumanDecision("phased_conversion", "Dr. A. Rivera", "Executive",
                                       "Keeps emergency care; community at the table.", acknowledged=acks))
    say("\n...then decides with eyes open:")
    print(render_resolution(res))

    say("\nSTEP 3 — Months later, the outcome comes back (Ch. 9, 10). The engine registers it on the axes")
    say("and across the seventeen perspectives, widens its own uncertainty, and flags it for people.")
    lessons = eng.feedback(OutcomeFeedback(d.id, {"trust_fear": -0.6, "stewardship": 0.5},
                                           notes="Trust collapsed during the transition; finances stabilized.",
                                           reporter="Community board"))
    for line in lessons:
        say("  • " + line)
    say(f"  Learned extra margin on axes: {eng.memory.calibration}")

    say("\nSTEP 4 — The foundation (Ch. 1, 9, 11). The board responds to the flag by proposing more humility:")
    say("a wider base measurement margin. The machine cannot make this change itself.")
    try:
        eng.th = None  # type: ignore[assignment]
    except AttributeError as e:
        say(f"  Direct change refused: {e}")
    rev = eng.foundation.propose("thresholds", {"base_margin": 0.15}, "Widen the base measurement margin",
                                 "Trust readings were wrong on the hospital transition (flag "
                                 f"{lessons.flags[0].id if lessons.flags else '-'}).", "M. Chen", "Policymaker")
    try:
        eng.foundation.approve(rev.id, "M. Chen", "Policymaker")
    except RevisionError as e:
        say(f"  Self-approval refused: {e}")
    eng.foundation.approve(rev.id, "Dr. A. Rivera", "Executive")
    eng.foundation.approve(rev.id, "J. Okafor", "Citizen")
    eng.foundation.apply(rev.id, "M. Chen", "Policymaker")
    print(render_revisions(eng))
    eng.close_flag(lessons.flags[0].id, "M. Chen", "Policymaker", f"Answered by revision {rev.id}.") \
        if lessons.flags else None

    say("\nSTEP 5 — A split by direction (new in v1.1). On the Canada MAID decision, care and communal")
    say("traditions object to one door while autonomy-centred traditions object to the opposite door.")
    dm = eng.deliberate(SCENARIOS["maid"][1]()[0])
    for s in dm.splits:
        say(_wrap_plain(split_lines(dm, s)))
    say(f"  Through the arch: {dm.passage} ({dm.posture.value}).")

    say("\nSTEP 6 — Protections read the whole measurement range (v1.2–v1.3). One reading of Power ↔ Powerless")
    say("for a vulnerable person, slid toward the Domination boundary at +0.50 (margin about ±0.2):")
    for pos in (0.40, 0.45, 0.50):
        probe = Decision("Boundary probe", [Option("a", "a", assessments={"power": AxisAssessment(pos, 0.8, 0.7)})],
                         stakeholders=[Stakeholder("Person affected", vulnerable=True)])
        g = CollaborationEngine().deliberate(probe).analyses["a"].guards
        state = f"{g[0].certainty} breach — {g[0].exposure:.0%} of the range in the guarded zone" if g else "clear"
        say(f"  position {pos:+.2f}: {state}")
    say("  v1.1 read only the exact value, so +0.49 passed and +0.50 tripped. Now the guard ramps up as the")
    say("  range crosses the line, and a possible breach still goes to a human.")
    say("  The Danger Zone (v1.3) reads ranges the same way. Trust ↔ Fear and Meaningful ↔ Meaningless, each")
    say("  a hair short of its danger line:")
    for tf, mm in ((-0.30, -0.20), (-0.53, -0.48), (-0.56, -0.51)):
        probe = Decision("Danger Zone probe", [Option("a", "a", assessments={
            "trust_fear": AxisAssessment(tf, 0.8, 0.7), "meaningful_meaningless": AxisAssessment(mm, 0.8, 0.7)})])
        dz = CollaborationEngine().deliberate(probe).analyses["a"].danger
        state = ("not entered" if dz.level == "none" else
                 "ENTERED" + ("" if dz.nominal_soft_stop else " within measurement error") if dz.level == "soft_stop"
                 else "warning")
        say(f"  positions {tf:+.2f} / {mm:+.2f}: Danger Zone {state}")

    say("\nSTEP 7 — The drone (Ch. 12). The Moral Fail-Safe Lock engages; every autonomous action pauses.")
    dd, _ = drone()
    d2 = eng.deliberate(dd)
    print(render(d2, eng.th, "brief"))
    later = eng.deliberate(SCENARIOS["moderation"][1]()[0])
    say(f"\n  Even an unrelated, harmless action now gets: {later.posture.value}")
    res2 = eng.resolve(d2, HumanDecision("hold", "Col. J. Okafor", "Reviewer",
                                         "Data too murky; hold and observe.", release_lock=True,
                                         acknowledged=[a.code for a in d2.analyses["hold"].acks]))
    print(render_resolution(res2))
    again = eng.deliberate(SCENARIOS["moderation"][1]()[0])
    say(f"  After the named release, that harmless action gets: {again.posture.value} — {again.passage}")

    ok, bad = eng.ledger.verify()
    say(f"\nSTEP 8 — The audit trail: {len(eng.ledger.entries)} hash-chained entries; intact = {ok}.")
    first_human = next(e for e in eng.ledger.entries if e["kind"] == "human_decision")
    first_human["payload"]["decided_by"] = "Someone else"   # someone rewrites history...
    ok, bad = eng.ledger.verify()
    say(f"  After someone quietly rewrites who made the first human decision: intact = {ok}; "
        f"first bad entry = #{bad}.")
    say("\nWhat kind of world does this choice create?")
    return 0


def _wrap_plain(text: str) -> str:
    import textwrap
    return textwrap.fill(text, width=92, initial_indent="  ", subsequent_indent="    ")


def cmd_drift(args) -> int:
    eng = CollaborationEngine()
    print("A news recommender publishes a weekly feed mix. Each week, an operator overrides any warning.\n")
    for dec in news_drift_series():
        d = eng.deliberate(dec)
        line = f"  {dec.question[:53]:<53} → {d.posture.value}"
        alerts = list(d.drift_alerts)
        if d.needs_human:
            acks = [a.code for a in d.analyses["mix"].acks]
            res = eng.resolve(d, HumanDecision("mix", "Ops on call", "Operator", "Engagement target", acknowledged=acks))
            line += "  (operator overrode)" if res.overrode_warnings else "  (operator approved)"
            alerts += res.drift_alerts
        print(line)
        for a in alerts:
            print(f"      DRIFT ALERT [{a.kind}] {a.message}")
    print()
    print(eng.drift.dashboard())
    return 0


def _ask(prompt: str, default: str = "") -> str:
    v = input(f"{prompt}{' [' + default + ']' if default else ''}: ").strip()
    return v or default


def _interactive(eng: CollaborationEngine, d: Deliberation) -> None:
    if not d.needs_human:
        print("\nThe engine can proceed on its own. Nothing for a human to decide.")
        return
    print("\nThis one needs a human. Options:", ", ".join(f"{k} ({a.option.label})" for k, a in d.analyses.items()))
    choice = _ask("Choose an option id (blank = none of them)") or None
    who = _ask("Your name")
    role = _ask(f"Your role {ROLES}", "Reviewer")
    why = _ask("Your rationale")
    acks: List[str] = []
    release = False
    if choice and choice in d.analyses:
        for a in d.analyses[choice].acks:
            print(f"\n  [{a.code}] {a.message}")
            if _ask("  Acknowledge? (y/n)", "n").lower().startswith("y"):
                acks.append(a.code)
    if eng.lock and choice:
        release = _ask("The Moral Fail-Safe Lock is engaged. Release it under your name? (y/n)",
                       "n").lower().startswith("y")
    try:
        res = eng.resolve(d, HumanDecision(choice, who, role, why, acknowledged=acks, release_lock=release))
        print("\n" + render_resolution(res))
    except Exception as e:  # show the engine's refusal plainly
        print(f"\nNot recorded: {e}")


def cmd_evaluate(args) -> int:
    with open(args.file, encoding="utf-8") as f:
        decision = Decision.from_dict(json.load(f))
    eng = _engine(args)
    d = eng.deliberate(decision)
    if args.json:
        print(json.dumps(d.summary(), indent=2, ensure_ascii=False))
    else:
        print(render(d, eng.th, "brief" if args.brief else "full"))
    if args.interactive:
        _interactive(eng, d)
    return 0


TEMPLATE = {
    "question": "What is being decided?",
    "context": "What a reader needs to know.",
    "mode": "act",
    "stakes": "consequential",
    "tags": ["domain"],
    "stakeholders": [{"name": "Person affected", "vulnerable": True}],
    "declared_values": [{"name": "Sustainability", "statement": "Our public commitment.",
                         "floors": {"stewardship": 0.0}}],
    "proposed_option": None,
    "options": [
        {"id": "a", "label": "Option A", "description": "", "reversible": True,
         "benefit": "Short-term benefit",
         "assessments": {
             "good_evil": {"position": 0.4, "relevance": 0.8, "confidence": 0.7, "rationale": "why"},
             "trust_fear": {"position": -0.3, "relevance": 0.6, "confidence": 0.6, "rationale": "why"}}},
        {"id": "b", "label": "Option B (leave assessments empty to have --llm or --cue measure it)",
         "assessments": {}},
    ],
    "_axes": "Head: good_evil power accuracy_intuition | Heart: trust_fear honor_shame freedom_bonding | "
             "Horizon: thriving_surviving meaningful_meaningless identity | "
             "Pillar Two features: relational_duty stewardship lawful_justice",
    "_position": "-1..+1, +1 = toward the first-named pole (Good, Power, Accuracy, Trust, Honor, Freedom, "
                 "Thriving, Meaningful, Desired identity). Measurement only: where the option sits, never how "
                 "much it counts.",
}


def cmd_template(args) -> int:
    print(json.dumps(TEMPLATE, indent=2))
    return 0


def cmd_roster(args) -> int:
    r = Roster.from_json(args.roster) if args.roster else Roster.default()
    if args.export:
        r.to_json(args.export)
        print(f"Roster written to {args.export} — edit it, then pass --roster {args.export}")
        return 0
    print(render_roster(r))
    return 0


def cmd_verify(args) -> int:
    led = MoralLedger(args.path)
    ok, bad = led.verify()
    print(f"{len(led.entries)} entries — {'INTACT' if ok else f'TAMPERED at entry #{bad}'}")
    return 0 if ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    p = argparse.ArgumentParser(prog="edna_collaboration", description="eDNA Collaboration v1.4")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("demo", help="run scenarios from the book")
    s.add_argument("name", nargs="?")
    s.add_argument("--brief", action="store_true")
    s.set_defaults(fn=cmd_demo)

    s = sub.add_parser("tour", help="guided walkthrough of the arch")
    s.set_defaults(fn=cmd_tour)

    s = sub.add_parser("drift", help="drift detection demo")
    s.set_defaults(fn=cmd_drift)

    s = sub.add_parser("evaluate", help="evaluate a decision JSON file")
    s.add_argument("file")
    s.add_argument("--interactive", action="store_true")
    s.add_argument("--json", action="store_true")
    s.add_argument("--brief", action="store_true")
    s.add_argument("--ledger")
    s.add_argument("--roster")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--llm", metavar="MODEL", help="measure unscored options with a model, e.g. claude-sonnet-5-5")
    g.add_argument("--cue", action="store_true", help="demo-grade cue lexicon (cannot authorize actions)")
    s.set_defaults(fn=cmd_evaluate)

    s = sub.add_parser("template", help="print a decision template")
    s.set_defaults(fn=cmd_template)

    s = sub.add_parser("roster", help="show or export the roster")
    s.add_argument("--export")
    s.add_argument("--roster")
    s.set_defaults(fn=cmd_roster)

    s = sub.add_parser("verify-ledger", help="verify an audit-trail file")
    s.add_argument("path")
    s.set_defaults(fn=cmd_verify)

    args = p.parse_args(argv)
    if not getattr(args, "fn", None):
        p.print_help()
        return 0
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
