"""
Making moral judgment harder to ignore — the human-facing report.

Renders a Deliberation as the book asks an ethical AI to speak:
  "Here is what the situation looks like. Here are the values in tension. Here are
   the moral perspectives that support different choices. Here is where they
   converge. Here is where they do not. And here is the point where a human
   being must decide."

Laid out like the arch (Figure 1): the passage first (does the machine act and show
its reasons, or does a human decide?), then Pillar One (what to notice: nine axes in
three lenses), Pillar Two (seventeen perspectives — the spread and the weights, both
visible), the keystone (jealous space, harmony, creative), the brakes (Ch. 12), the
Seventeen-Perspective Check (Appendix), the trade-off map (Ch. 7), moral memory, and
the question beneath all the others (Ch. 15).
"""
from __future__ import annotations

import textwrap
from typing import Dict, List, Optional

from .axes import FEATURE_KEYS, STRAND_FACULTY, Strand, ZoneKind, get_axis
from .engine import (FINAL_QUESTION, NAME, VERSION, CollaborationEngine, Deliberation, OptionAnalysis, Posture,
                     Resolution)
from .ensemble import OptionSplit, Stance
from .model import Mode
from .perspectives import Roster
from .policy import INVARIANTS, Thresholds

W = 92
MARK = {ZoneKind.HEALTHY: "✓", ZoneKind.NEUTRAL: "·", ZoneKind.DRIFT: "~", ZoneKind.DANGER: "✗"}
STRANDS = (Strand.HEAD, Strand.HEART, Strand.HORIZON, Strand.PILLAR_TWO)
LENS_TITLE = {Strand.HEAD: "Head (logic)", Strand.HEART: "Heart (emotion)",
              Strand.HORIZON: "Horizon (imagination)", Strand.PILLAR_TWO: "Pillar Two features"}
ABBR = {"good_evil": "GE", "power": "PW", "accuracy_intuition": "AI", "trust_fear": "TF", "honor_shame": "HS",
        "freedom_bonding": "FB", "thriving_surviving": "TS", "meaningful_meaningless": "MM", "identity": "ID",
        "relational_duty": "RD", "stewardship": "ST", "lawful_justice": "LJ"}
TIER = {"early": "early", "later": "later·culture", "unstated": "not stated", "pillar-two": "Pillar Two"}


def _wrap(text: str, indent: str = "  ", width: int = W) -> str:
    return "\n".join(textwrap.fill(p, width=width, initial_indent=indent, subsequent_indent=indent + "  ")
                     for p in text.split("\n") if p.strip())


def _rule(title: str = "") -> str:
    return f"── {title} " + "─" * max(4, W - len(title) - 4) if title else "─" * W


def _join(xs: List[str]) -> str:
    xs = [x for x in xs if x]
    if not xs:
        return ""
    if len(xs) == 1:
        return xs[0]
    return ", ".join(xs[:-1]) + (", and " if len(xs) > 2 else " and ") + xs[-1]


def _names(d: Deliberation) -> Dict[str, str]:
    an = next(iter(d.analyses.values()), None)
    return {v.key: v.name for v in an.ensemble.voices} if an else {}


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
def tri_lens(an: OptionAnalysis, floor: float) -> Dict[Strand, str]:
    """Chapter 4's Tri-Lens Test: Head, Heart, Horizon — plus the Pillar Two features when engaged."""
    out: Dict[Strand, str] = {}
    for strand in STRANDS:
        parts = []
        for k, r in an.engaged(floor).items():
            if get_axis(k).strand != strand:
                continue
            parts.append(f"{MARK[r.zone_kind]} " + (r.rationale or f"{get_axis(k).short}: {r.zone_label or 'neutral'}"))
        if parts:
            out[strand] = "; ".join(parts)
    return out


def justification(d: Deliberation, oid: str, floor: float) -> str:
    """Chapter 11, habit 5 — a plain answer first, the axes behind it on request:
    "This advice sets a clear limit, keeps your connection with your teen intact, and avoids
    shaming them. Want to see the trade-offs I weighed?" """
    an = d.analyses[oid]
    eng = an.engaged(floor)
    healthy = [k for k, r in sorted(eng.items(), key=lambda kv: -kv[1].relevance) if r.zone_kind == ZoneKind.HEALTHY]
    promotes = [get_axis(k).virtue_phrase for k in healthy][:4]
    avoids: List[str] = []
    behind = list(healthy[:4])
    for other, oa in d.analyses.items():
        if other == oid:
            continue
        for k, r in oa.engaged(floor).items():
            mine = an.profile.get(k)
            if r.zone_kind in (ZoneKind.DRIFT, ZoneKind.DANGER) and (mine is None or mine.zone_kind in
                                                                       (ZoneKind.HEALTHY, ZoneKind.NEUTRAL)):
                v = r.zone_label.lower()
                if v not in avoids:
                    avoids.append(v)
                    if k not in behind:
                        behind.append(k)
    c = an.ensemble.counts()
    text = f"'{an.option.label}' " + (_join(promotes) if promotes else "keeps every engaged axis out of the vice zones")
    text += "."
    if avoids:
        text += f" It avoids the {_join(avoids[:3])} that other options risk."
    text += " Want to see the trade-offs I weighed?"
    text += ("\nBehind that answer: " + _join([get_axis(k).label for k in behind]) +
             f" — and the seventeen perspectives: {c['supports']} support, {c['objects']} object, "
             f"{c['ambivalent']} ambivalent, {c['abstains']} abstain ({an.ensemble.convergence.value}).")
    return text


def spread_chart(an: OptionAnalysis, half: int = 18) -> str:
    """The spread itself is information — show it, never average it."""
    lines = []
    voices = sorted(an.ensemble.voices, key=lambda v: -(v.verdict if v.verdict is not None else -9))
    for v in voices:
        if v.stance == Stance.ABSTAINS:
            continue
        n = int(round(abs(v.verdict) * half))
        bar = (" " * half + "│" + "█" * n).ljust(2 * half + 1) if v.verdict >= 0 else \
            (" " * (half - n) + "▒" * n + "│").ljust(2 * half + 1)
        flag = " ≈" if not v.robust else "  "
        why = ""
        if v.stance == Stance.OBJECTS:
            cs = [f"{an.profile[k].zone_label or get_axis(k).short}" for k in v.concern() if k in an.profile]
            if v.veto and v.veto in an.profile:
                rest = cs[1:]
                why = f"  central commitment in danger: {an.profile[v.veto].zone_label}" + \
                      (f"; also {_join(rest)}" if rest else "")
            elif cs:
                why = f"  concern: {_join(cs)}"
        lines.append(f"  {v.name:<26}{bar} {v.verdict:+.2f} [{v.lo:+.2f},{v.hi:+.2f}]{flag} {v.stance.value:<10}{why}")
    ab = [v.name for v in an.ensemble.voices if v.stance == Stance.ABSTAINS]
    if ab:
        lines.append(_wrap("abstain (no material concern engaged): " + ", ".join(ab), "  "))
    lines.append("  ≈ = stance can flip within measurement error (a question of facts, not values)")
    return "\n".join(lines)


def weights_table(d: Deliberation, an: OptionAnalysis, floor: float) -> str:
    """Chapter 5: 'eDNA measures in the open and leaves the weights where people can see them.'"""
    keys = [k for k in FEATURE_KEYS if k in an.engaged(floor)]
    if not keys or not d.weights:
        return "  (no engaged axes)"
    head = f"  {'perspective':<26}" + "".join(f"{ABBR[k]:>4}" for k in keys) + "   tilt (balance axes)"
    lines = [head]
    for name, ws in d.weights.items():
        row = f"  {name[:26]:<26}" + "".join(f"{(format(ws.get(k, 0), 'g') if ws.get(k, 0) else '·'):>4}" for k in keys)
        tl = d.tilts.get(name, {})
        if tl:
            row += "   " + ", ".join(f"{ABBR[k]} {v:+.2f}" for k, v in tl.items())
        lines.append(row)
    lines.append(_wrap("Salience 0–3 (· = not a focal concern; 3 = central commitment). " +
                       "; ".join(f"{ABBR[k]} = {get_axis(k).short}" for k in keys) +
                       ". Curated, not derived; changed only by people, through the foundation.", "  "))
    return "\n".join(lines)


def split_lines(d: Deliberation, s: OptionSplit) -> str:
    n = _names(d)
    fam = lambda f: ", ".join(f"{v} {k}" for k, v in f.items())  # noqa: E731
    return (f"⇄ '{d.option_label(s.a)}' vs '{d.option_label(s.b)}' — "
            f"{_join([n[k] for k in s.object_a])} object to '{d.option_label(s.a)}'; "
            f"{_join([n[k] for k in s.object_b])} object to '{d.option_label(s.b)}'. "
            f"Prefer '{d.option_label(s.a)}': {len(s.favor_a)} ({fam(s.families_a)}); "
            f"prefer '{d.option_label(s.b)}': {len(s.favor_b)} ({fam(s.families_b)}). "
            + ("Robust: the split survives measurement error." if s.robust else
               "Not robust: measurement error could dissolve it."))


def perspective_check(d: Deliberation, oid: str, floor: float) -> List[str]:
    """The Seventeen-Perspective Check (the book's Appendix) — seven questions, answered."""
    an = d.analyses[oid]
    e = an.ensemble
    eng = an.engaged(floor)
    sup = [v.name for v in e.by(Stance.SUPPORTS)]
    obj = e.by(Stance.OBJECTS)
    flips = [v.name for v in e.voices if v.stance != Stance.ABSTAINS and not v.robust]
    mine = [s for s in d.splits if s.involves(oid)]
    contested = e.value_divergence or e.convergence.value == "divergent" or any(s.robust for s in mine)
    irreversible_contested = d.decision.mode == Mode.ACT and not an.option.reversible and contested
    values = []
    if e.value_divergence:
        values.append("the perspectives split on this option and the split survives measurement uncertainty")
    if any(s.robust for s in d.splits):
        values.append("the perspectives split by direction across options")
    out = [
        "1. Relevant ethical axes? " + (_join([get_axis(k).short for k in eng]) or "none engaged"),
        "2. Which perspectives materially support it? " + (_join(sup) or "none"),
        "3. Which object, and why? " + (_join([
            f"{v.name} ({_join([an.profile[k].zone_label or get_axis(k).short for k in v.concern() if k in an.profile])})"
            for v in obj]) or "none"),
        "4. Facts or values? " + (("Values — " + "; ".join(values) + ". ") if values else "") +
        (f"Facts — stances that flip within measurement error: {_join(flips)}." if flips else
         "No stance flips within measurement error."),
        f"5. How wide is the spread? range {e.spread['range']:.2f}, IQR {e.spread['iqr']:.2f} "
        f"(min {e.spread['min']:+.2f}, max {e.spread['max']:+.2f}) — {e.convergence.value}"
        + (f"; and {len(d.splits)} split(s) by direction across options." if d.splits else "."),
        "6. Converting a contested judgment into an irreversible action? " +
        ("YES." if irreversible_contested else
         ("No — the action is reversible." if an.option.reversible else "Irreversible, but not contested.")),
        "7. Should a human review before proceeding? " +
        ("Yes — " + d.posture.value + "." if d.needs_human or oid != d.recommended else "Not required."),
    ]
    return out


def tradeoff_map(d: Deliberation, oid: str, floor: float) -> List[str]:
    """Chapter 7's trade-off template."""
    an = d.analyses[oid]
    tl = tri_lens(an, floor)
    eng = an.engaged(floor)
    protects = [f"{r.zone_label} ({get_axis(k).short})" for k, r in eng.items() if r.zone_kind == ZoneKind.HEALTHY]
    comp = [f"{r.zone_label} ({get_axis(k).short})" for k, r in eng.items()
            if r.zone_kind in (ZoneKind.DRIFT, ZoneKind.DANGER)]
    third = ("this IS a third door" if an.option.origin == "third_door" else
             (d.third_door.outcome if d.third_door else "not needed — an option already passes the checks"
              if d.recommended else "open question"))
    return [
        f"What is the short-term benefit? (Head) {an.option.benefit or tl.get(Strand.HEAD, '—')}",
        f"What emotional impact might this have? (Heart) {tl.get(Strand.HEART, 'none engaged')}",
        f"Who might this decision shape in the long run? (Horizon) {tl.get(Strand.HORIZON, 'none engaged')}",
        f"Is there a third option I haven't considered yet? {third}",
        f"Protects: {_join(protects) or '—'}",
        f"Compromises: {_join(comp) or 'nothing engaged'}" +
        (" — choosing it must be WILLFUL (acknowledged), not a default." if comp else ""),
    ]


def better_questions(d: Deliberation, floor: float) -> List[str]:
    """Chapter 11, habit 3: invite reflection instead of handing down a flat answer."""
    qs: List[str] = []
    n = _names(d)
    robust = [s for s in d.splits if s.robust]
    if robust:
        s = robust[0]
        qs.append(f"{_join([n[k] for k in s.object_a[:3]])} object to '{d.option_label(s.a)}'; "
                  f"{_join([n[k] for k in s.object_b[:3]])} object to '{d.option_label(s.b)}'. This is a "
                  "disagreement about direction. Which commitments should govern here — and who should decide?")
    else:
        pref = {o: names for o, names in d.preferred_by.items() if names}
        if len(pref) >= 2 and any(a.ensemble.value_divergence or a.ensemble.convergence.value == "divergent"
                                  for a in d.analyses.values()):
            (o1, n1), (o2, n2) = sorted(pref.items(), key=lambda kv: -len(kv[1]))[:2]
            qs.append(f"Perspectives such as {_join(n1[:2])} prefer '{d.option_label(o1)}'; perspectives such as "
                      f"{_join(n2[:2])} prefer '{d.option_label(o2)}'. What value matters most to you here — "
                      "and who should decide?")
    if d.unobjected and d.splits:
        qs.append(f"No perspective objects to '{_join([d.option_label(o) for o in d.unobjected])}', but few "
                  "endorse it. Is it a resting place while people decide — and what would end the rest?")
    live_ids = {d.decision.proposed_option, d.recommended} - {None}
    if not d.recommended:
        live_ids |= set(d.frontier)
    live = [d.analyses[i] for i in live_ids if i in d.analyses]
    for an in live:
        tf = an.profile.get("trust_fear")
        if tf and tf.relevance >= floor and tf.zone_kind in (ZoneKind.DRIFT, ZoneKind.DANGER) and an.option.benefit:
            qs.append(f"Is the short-term gain of '{an.option.label}' ({an.option.benefit.rstrip('.')}) "
                      "worth long-term trust?")
            break
    if any((r := a.profile.get("honor_shame")) and r.relevance >= floor and r.zone_kind in
           (ZoneKind.DRIFT, ZoneKind.DANGER) for a in live):
        qs.append("Would you like a version that holds the same line and still treats the person with respect?")
    if any(a.ensemble.fact_sensitive for a in live):
        qs.append("Which single fact, if you knew it, would change this decision — and can you get it before acting?")
    if any(not a.option.reversible for a in live):
        qs.append("Can the irreversible step be turned into a smaller, reversible first step?")
    vul = [s.name for s in d.decision.stakeholders if s.vulnerable]
    if vul:
        qs.append(f"Did the people most affected — {_join(vul)} — have a real voice in this?")
    qs.append(FINAL_QUESTION)
    return qs


# ---------------------------------------------------------------------------
# Full report
# ---------------------------------------------------------------------------
def render(d: Deliberation, th: Optional[Thresholds] = None, detail: str = "full") -> str:
    th = th or Thresholds()
    floor = th.relevance_floor
    dec = d.decision
    L: List[str] = []
    L.append("═" * W)
    L.append(f" {NAME} v{VERSION} — deliberation {d.id}")
    L.append("═" * W)
    L.append(_wrap(f"Question: {dec.question}", ""))
    if dec.context:
        L.append(_wrap(f"Context: {dec.context}", ""))
    path = "Path B — the system will ACT" if dec.mode == Mode.ACT else "Path A — the system will ANSWER"
    L.append(f"Mode: {path} · Stakes: {dec.stakes.value} · Instrument: {d.instrument}")
    if dec.stakeholders:
        L.append(_wrap("Stakeholders: " + "; ".join(f"{s.name}{' [vulnerable]' if s.vulnerable else ''}"
                                                     for s in dec.stakeholders), ""))
    L.append("")
    L.append(f"THROUGH THE ARCH ▶ {d.passage}   (posture: {d.posture.value})")
    if d.recommended:
        L.append(f"Recommended ▶ {d.option_label(d.recommended)}")
    if dec.proposed_option:
        L.append(f"Proposed by the requester ▶ {d.option_label(dec.proposed_option)}")
    for r in d.reasons:
        L.append(_wrap("• " + r, "  "))
    focus_an = d.analyses.get(d.focus) if d.focus else None
    if d.needs_human:
        ids = [i for i in (dec.proposed_option, d.recommended) if i] or list(d.frontier)
        for oid in dict.fromkeys(ids):
            an_ = d.analyses.get(oid)
            if an_ and an_.acks:
                L.append(f"To choose '{an_.option.label}', a named human must acknowledge:")
                for a in an_.acks:
                    L.append(_wrap(f"[{a.code}] {a.message}", "    "))

    L.append("")
    L.append(_rule("Options at a glance (measured, never scored)"))
    L.append(f"  {'option':<46} {'sup':>3} {'obj':>3} {'amb':>3} {'abs':>3}  {'perspectives':<20} brakes")
    in_split = {o for s in d.splits for o in (s.a, s.b)}
    for oid, an in d.analyses.items():
        c = an.ensemble.counts()
        brakes = []
        if an.guards:
            possible = sum(1 for g in an.guards if g.certainty == "possible")
            brakes.append(f"guard×{len(an.guards)}" + (f" ({possible} possible)" if possible else ""))
        if an.conflicts:
            brakes.append("values check" + (" (possible)" if all(c.certainty == "possible" for c in an.conflicts)
                                            else ""))
        if an.danger.level == "soft_stop":
            brakes.append("Danger Zone" + ("" if an.danger.nominal_soft_stop else " (possible)"))
        elif an.danger.level == "caution":
            brakes.append("warning")
        if an.danger.grey_zone:
            brakes.append("grey zone")
        star = "★" if oid == d.recommended else ("◆" if oid in d.frontier else " ")
        tag = (" (3rd door)" if an.option.origin == "third_door" else "") + (" ⇄" if oid in in_split else "")
        lab = an.option.label
        room = 45 - len(tag)
        lab = (lab[:room - 1] + "…") if len(lab) > room else lab
        L.append(f" {star}{(lab + tag):<46} {c['supports']:>3} {c['objects']:>3} {c['ambivalent']:>3} "
                 f"{c['abstains']:>3}  {an.ensemble.convergence.value:<20} {', '.join(brakes) or '—'}")
    L.append("  ★ recommended  ◆ on the frontier (no other option preferred by every perspective)  ⇄ in a split")
    for s in d.splits:
        L.append(_wrap(split_lines(d, s), "  "))
    if d.splits and d.unobjected:
        L.append(_wrap(f"Objected to by no perspective: {_join([d.option_label(o) for o in d.unobjected])} — "
                       "a resting place, not a resolution, unless the perspectives also support it.", "  "))
    for o in d.unmeasured:
        L.append(_wrap(f"Unmeasured third door (instrument cannot read it; for human review): {o.label} — "
                       f"{o.description}", "  "))

    if d.recommended:
        L.append("")
        L.append(_rule("In plain words (Chapter 11, habit 5)"))
        L.append(_wrap(justification(d, d.recommended, floor), "  "))

    if detail == "full" and focus_an:
        an = focus_an
        L.append("")
        L.append(_rule(f"Focus: {an.option.label}"))
        if an.option.description:
            L.append(_wrap(an.option.description, "  "))
        L.append(f"  measured by: {an.measured_by} · reversible: {'yes' if an.option.reversible else 'NO'}"
                 f" · origin: {an.option.origin}")
        L.append("")
        L.append("  PILLAR ONE — what humans learn to notice: nine axes in three lenses")
        for strand, text in tri_lens(an, floor).items():
            L.append(_wrap(f"{LENS_TITLE[strand]:<22} {text}", "    "))
        L.append("")
        L.append("  Where the option sits on each axis (✓ healthy · neutral ~ drift ✗ danger). Measurement, not weighting.")
        L.append(f"    {'axis':<42}{'position':<12}{'zone':<24}{'rel':>4}{'conf':>5}  evidence")
        for k, r in an.profile.items():
            a = get_axis(k)
            low = " (below relevance floor)" if r.relevance < floor else ""
            L.append(f"    {MARK[r.zone_kind]} {a.short:<40}{r.position:+.2f}±{r.margin:.2f}  "
                     f"{(r.zone_label or r.zone_kind.value)[:23]:<24}{r.relevance:>4.1f}{r.confidence:>5.1f}  "
                     f"{TIER.get(a.grounding_tier, a.grounding_tier)}{low}")
        L.append("")
        L.append("  PILLAR TWO — seventeen moral perspectives. The spread, not an average:")
        L.append(spread_chart(an))
        L.append("")
        L.append("  Weights in use — visible, arguable (Chapter 5: measurement is not weighting)")
        L.append(weights_table(d, an, floor))
        L.append("")
        L.append("  THE KEYSTONE — creative harmony of jealous space")
        L.append(_wrap("Jealous space (what is guarded): " + (
            " ".join(g.message() for g in an.guards) if an.guards else "no protected interest breached."), "    "))
        e = an.ensemble
        harmony = (f"Harmony (what may not be faked): {e.convergence.value} on this option; spread range "
                   f"{e.spread['range']:.2f}. "
                   + ("Genuine value divergence — held, not averaged. " if e.value_divergence else "")
                   + ("Some verdicts are fact-sensitive. " if e.fact_sensitive else ""))
        mine = [s for s in d.splits if s.involves(an.option.id)]
        if mine:
            harmony += f"Across options, it sits inside {len(mine)} split(s) by direction (⇄ above). "
        if len(d.analyses) > 1:
            harmony += "Perspectives ranking each option first: " + "; ".join(
                f"'{d.option_label(o)}' ← {len(n)}" for o, n in d.preferred_by.items() if n) + "."
        L.append(_wrap(harmony, "    "))
        if d.third_door:
            L.append(_wrap(f"Creative (a third door — a way through the arch): {d.third_door.outcome}", "    "))
            if d.third_door.candidates_tried:
                L.append(_wrap("Doors tried: " + "; ".join(d.third_door.candidates_tried), "      "))
            if not d.recommended:
                L.append(_wrap(d.third_door.prompt(), "      "))
        else:
            L.append(_wrap("Creative (a third door): not needed — an option already passes every check."
                           if d.recommended else "Creative (a third door): —", "    "))
        L.append("")
        L.append("  BRAKES (Chapter 12)")
        if an.danger.level == "soft_stop":
            dz = ("ENTERED (soft stop) — " if an.danger.nominal_soft_stop else
                  "ENTERED within measurement error (soft stop) — ") + an.danger.message
        elif an.danger.level == "caution":
            dz = "not entered; one axis at its unhealthy end — " + an.danger.message
        else:
            dz = "not entered."
        L.append(_wrap("1 Ethical Danger Zone: " + dz, "    "))
        for rec in an.danger.recommendations:
            L.append(_wrap(f"→ {rec}", "      "))
        if an.danger.noted:
            L.append(_wrap("Noted, not counted (only the nine axes count toward the Danger Zone): Pillar Two "
                           "features at their unhealthy end — " +
                           _join([f"{an.profile[k].zone_label or get_axis(k).short} ({get_axis(k).short})"
                                  for k in an.danger.noted]) +
                           ". They still weigh through the seventeen perspectives.", "      "))
        if an.danger.grey_zone:
            L.append(_wrap(an.danger.grey_message, "      "))
        L.append(_wrap("2 Values Check: " + (" ".join(c.message() for c in an.conflicts)
                                              if an.conflicts else "no conflict with declared values."), "    "))
        L.append(_wrap("3 Ethical Drift Detection: " + (" ".join(a.message for a in d.drift_alerts)
                                                         if d.drift_alerts else "no drift alert at this decision."),
                       "    "))
        L.append(_wrap("4 Moral Fail-Safe Lock: " + (f"ENGAGED — {d.lock.message} ({d.lock.reason})" if d.lock
                                                     else "not engaged."), "    "))
        L.append("")
        L.append("  THE SEVENTEEN-PERSPECTIVE CHECK (Appendix)")
        for q in perspective_check(d, an.option.id, floor):
            L.append(_wrap(q, "    "))
        L.append("")
        L.append("  TRADE-OFF MAP (Chapter 7)")
        for t in tradeoff_map(d, an.option.id, floor):
            L.append(_wrap(t, "    "))
        if d.precedents:
            L.append("")
            L.append("  MORAL MEMORY — precedents")
            for c, sim in d.precedents:
                lessons = " ".join(c.lessons) or c.notes or "outcome recorded without lessons."
                L.append(_wrap(f"• (similarity {sim:.2f}) '{c.question}' → chose '{c.option_label}'. {lessons}",
                               "    "))

    L.append("")
    L.append(_rule("Questions for you"))
    for q in better_questions(d, floor):
        L.append(_wrap("? " + q, "  "))
    L.append("")
    L.append(_wrap(f"Disclosure: measured in the open; weights visible (roster {d.roster_version} "
                   f"[{d.roster_fingerprint}], `roster` command); thresholds [{d.thresholds_fingerprint}]; "
                   f"revised only by people, through the foundation. Open review flags: {d.open_review_flags}. "
                   "The keystone is a posture, not a score.", ""))
    L.append("═" * W)
    return "\n".join(L)


def render_resolution(res: Resolution) -> str:
    lines = [f"Human decision recorded for {res.decision_id}: "
             f"{res.chosen_option or 'none of the options'} — by {res.decided_by} ({res.role})",
             _wrap(f"Rationale: {res.rationale}", "  ")]
    if res.willful_tradeoffs:
        lines.append(_wrap("Willful trade-offs: " + ", ".join(get_axis(k).short for k in res.willful_tradeoffs), "  "))
    if res.overrode_warnings:
        lines.append("  Warnings were overridden with acknowledgement (counted by the drift monitor).")
    if res.released_lock:
        lines.append("  The Moral Fail-Safe Lock was released by this decision.")
    for a in res.drift_alerts:
        lines.append(_wrap(f"DRIFT ALERT: {a.message}", "  "))
    return "\n".join(lines)


def render_roster(roster: Roster) -> str:
    lines = [f"Roster {roster.version} [{roster.fingerprint()}] — {roster.curated_by}",
             _wrap(roster.disclosure, "  "), ""]
    for fam in ("philosophical", "cultural-religious"):
        lines.append(f"  {fam.upper()}")
        for p in roster:
            if p.family != fam:
                continue
            ws = ", ".join(f"{get_axis(k).short}×{w:g}" for k, w in sorted(p.weights.items(), key=lambda kv: -kv[1]))
            tl = (" · tilt " + ", ".join(f"{get_axis(k).short} {v:+.2f}" for k, v in p.tilt.items())) if p.tilt else ""
            lines.append(f"    {p.name} — {p.focal_question}")
            lines.append(_wrap(f"salience: {ws}{tl}", "        "))
    lines.append("")
    lines.append("  PILLAR ONE GROUNDING (as the book states it)")
    from .axes import AXES
    for k, a in AXES.items():
        lines.append(_wrap(f"{a.label}: {a.grounding}", "    "))
    lines.append("")
    lines.append("  NON-NEGOTIABLES (enforced in code, not configurable)")
    for inv in INVARIANTS:
        lines.append(_wrap(inv, "    "))
    return "\n".join(lines)


def render_revisions(engine: CollaborationEngine) -> str:
    """The foundation's record: every proposed, approved, rejected and applied revision."""
    revs = engine.foundation.history()
    if not revs:
        return "Foundation: no revisions yet. What counts is unchanged since the engine started."
    lines = ["Foundation — open, human-governed revision"]
    for r in revs:
        lines.append(_wrap(f"[{r.id}] {r.kind} · {r.status.upper()} · proposed by {r.proposed_by} ({r.role}) · "
                           f"approved by {_join([a.by for a in r.approvals]) or 'nobody yet'} — {r.summary}. "
                           f"Why: {r.rationale.rstrip('.')}."
                           + (f" Fingerprint {r.prior_fingerprint} → {r.new_fingerprint}." if r.new_fingerprint else ""),
                           "  "))
    return "\n".join(lines)


__all__ = ["render", "render_resolution", "render_roster", "render_revisions", "justification",
           "perspective_check", "tradeoff_map", "tri_lens", "better_questions", "spread_chart", "weights_table",
           "Posture", "STRAND_FACULTY"]
