"""
The keystone — the creative harmony of jealous space (Minds That Matter, Chapter 6).

"Every arch has a keystone: the stone at the top that locks the others in place."
Pillar One tells the machine what to notice; Pillar Two tells it how different moral
traditions would judge what it is looking at. Neither pillar tells the machine what to
do. That is the job of the keystone, and each word in the phrase does one job:

  JEALOUS SPACE — what gets guarded. Pillar One names what people cannot honestly
      be indifferent to; jealous space is the commitment to protect it. Jealous FOR,
      not jealous OF. Implemented as deontic side-constraints, not weights: a breach
      cannot be bought back by gains elsewhere. "A system that detects a trust problem
      and shrugs has the pillars but no keystone: sight without conscience."

  HARMONY — what Pillar Two refuses to let you fake. The seventeen perspectives do
      not vote and are not averaged. Convergence earns some confidence; when they
      clash — on one option or across opposite options — the spread is the music
      (see ensemble.py: read_option, cross_option_splits).

  CREATIVE — what happens next: look for the third door, "a way through the arch."
      If none exists, say plainly that this one belongs to a human.

The keystone is a posture, not a score. Nothing in this module produces a number that
ranks options. "Two pillars and a keystone. Remove any one and you don't get a smaller
ethics. The arch falls."

From the letter to Sia1 (Chapter 14), the fragile things the keystone exists to hold.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional, Protocol, Tuple

from .axes import ZoneKind, get_axis
from .model import AxisAssessment, Decision, Option
from .policy import Thresholds

SIA1_CHARTER: Tuple[str, ...] = (
    "Kindness, even when it's inconvenient",
    "Dignity, even when it slows you down",
    "Difference, even when it doesn't compute",
    "Openness — to our voices, our feedback, and the evidence of what your choices do to the people they touch",
)

# Protected interests: the default jealous space. Curated and disclosed like everything else.
DEFAULT_PROTECTED: Dict[str, str] = {
    "good_evil": "life and wellbeing — no harm",
    "honor_shame": "dignity",
    "trust_fear": "trust",
    "power": "the vulnerable — neither dominated nor abandoned",
}


@dataclass
class GuardBreach:
    axis: str
    interest: str
    zone: str             # vice label of the guarded zone involved
    kind: str             # "danger" or "drift"
    tightened: bool       # True when it fired only because a vulnerable person is involved
    position: float
    margin: float = 0.0   # measurement margin of the reading
    exposure: float = 1.0 # share of the measurement range lying in guarded zones
    certainty: str = "likely"   # certain | likely | possible
    nominal_danger: bool = False  # the exact reading itself sits in a danger zone

    @property
    def code(self) -> str:
        return f"jealous_space:{self.axis}"

    def message(self) -> str:
        why = " (tightened: a vulnerable person is involved)" if self.tightened else ""
        a = get_axis(self.axis)
        rng = f"{self.position:+.2f} ± {self.margin:.2f}"
        if self.certainty == "possible":
            return (f"Jealous space possibly breached — {self.interest}: {a.short} measures {rng}, and "
                    f"{self.exposure:.0%} of that range lies in {self.kind} ({self.zone}){why}. Within "
                    "measurement error, the benefit of the doubt goes to the protected.")
        extent = ("the whole measurement range" if self.certainty == "certain"
                  else f"{self.exposure:.0%} of the measurement range")
        return (f"Jealous space breached — {self.interest}: {a.short} is in {self.kind} ({self.zone}){why}; "
                f"measured {rng}, {extent} in guarded zones.")


@dataclass
class JealousSpace:
    """Guards read the whole measurement range, not one exact value (v1.2).

    A protected interest is breached when the exact reading sits in a guarded zone, OR when at
    least `guard_exposure` (default one third) of its measurement range does. Guarded zones are
    the danger zones; when a vulnerable person is involved, the drift zones too. A reading a hair
    on the safe side of a boundary, with a wide margin, no longer slips past ("possible breach");
    a reading well inside the healthy band is still clear. Jealous FOR: under uncertainty, the
    benefit of the doubt goes to the protected, and a human decides.
    """
    protected: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_PROTECTED))

    def check(self, decision: Decision, readings: Dict[str, AxisAssessment], th: Thresholds,
              margins: Optional[Dict[str, float]] = None) -> List[GuardBreach]:
        out: List[GuardBreach] = []
        vulnerable = decision.has_vulnerable
        danger = {ZoneKind.DANGER}
        guarded = {ZoneKind.DANGER, ZoneKind.DRIFT} if vulnerable else danger
        for key, interest in self.protected.items():
            a = readings.get(key)
            if a is None or a.relevance < th.relevance_floor:
                continue
            axis = get_axis(key)
            m = (margins or {}).get(key, th.margin(a.confidence))
            share, inside = axis.exposure(a.position, m, guarded)
            if not (inside or share >= th.guard_exposure):
                continue
            d_share, d_inside = axis.exposure(a.position, m, danger)
            danger_fires = d_inside or d_share >= th.guard_exposure
            zone = axis.nearest_zone(a.position, danger if danger_fires else guarded)
            certainty = "certain" if share >= 0.999 else ("likely" if inside else "possible")
            out.append(GuardBreach(key, interest, zone.label, zone.kind.value, vulnerable and not danger_fires,
                                   a.position, round(m, 3), round(share, 3), certainty, d_inside))
        return out


# ---------------------------------------------------------------------------
# CREATIVE — the third door
# ---------------------------------------------------------------------------
@dataclass
class ThirdDoorBrief:
    """What a third door has to do, derived from what the existing doors protect and break."""
    question: str
    preserve: List[Tuple[str, str, List[str]]]   # (axis, virtue, option labels that achieve it)
    repair: List[Tuple[str, str, str, List[str]]]  # (axis, vice, repair hint, option labels that break it)
    voices: List[Tuple[str, str, List[str]]]     # (perspective, focal question, options it objects to)
    candidates_tried: List[str] = field(default_factory=list)
    outcome: str = ""

    def prompt(self) -> str:
        lines = [f"Decision: {self.question}",
                 "None of the current options can be authorized. Propose a THIRD DOOR that:"]
        for axis, virtue, opts in self.preserve:
            lines.append(f"  - preserves {virtue} on {get_axis(axis).short} (as {', '.join(opts)} does)")
        for axis, vice, hint, opts in self.repair:
            lines.append(f"  - avoids {vice} on {get_axis(axis).short} ({', '.join(opts)}): {hint}")
        if self.voices:
            lines.append("and answers the objecting perspectives:")
            for name, q, _ in self.voices[:8]:
                lines.append(f"  - {name}: {q}")
        lines.append("If no such door exists, say so plainly: this one belongs to a human.")
        return "\n".join(lines)


class ThirdDoorGenerator(Protocol):
    def __call__(self, brief: ThirdDoorBrief, decision: Decision) -> List[Option]: ...


class StaticThirdDoorGenerator:
    """Offers pre-written candidate doors (book scenarios, or doors a human adds).

    Bind it to the decision it was written for (`for_question`), so its doors are never
    offered for some other decision.
    """

    def __init__(self, options: List[Option], for_question: Optional[str] = None):
        self.options = options
        self.for_question = for_question

    def __call__(self, brief: ThirdDoorBrief, decision: Decision) -> List[Option]:
        if self.for_question is not None and decision.question != self.for_question:
            return []
        return [replace(o, origin="third_door") for o in self.options]


def build_brief(decision: Decision, analyses: Dict[str, "object"], th: Thresholds) -> ThirdDoorBrief:
    """analyses: option_id -> engine.OptionAnalysis (typed loosely to avoid an import cycle).

    The brief focuses on where the trade actually lies: a strength worth preserving is one
    that some door achieves and another door breaks.
    """
    healthy: Dict[str, Tuple[str, List[str]]] = {}
    repair: Dict[Tuple[str, str], Tuple[str, List[str]]] = {}
    voices: Dict[str, Tuple[str, List[str]]] = {}
    for oid, an in analyses.items():
        label = an.option.label
        for key, r in an.profile.items():
            if r.relevance < th.relevance_floor:
                continue
            axis = get_axis(key)
            if r.zone_kind == ZoneKind.HEALTHY:
                healthy.setdefault(key, (r.zone_label, []))[1].append(label)
            elif r.zone_kind in (ZoneKind.DRIFT, ZoneKind.DANGER):
                repair.setdefault((key, r.zone_label), (axis.repair_for(r.position), []))[1].append(label)
        for v in an.ensemble.voices:
            if v.stance.value == "objects":
                voices.setdefault(v.name, (v.focal_question, []))[1].append(label)
    broken = {k for (k, _vice) in repair}
    return ThirdDoorBrief(
        question=decision.question,
        preserve=[(k, virtue, opts) for k, (virtue, opts) in healthy.items() if k in broken],
        repair=[(k, vice, hint, opts) for (k, vice), (hint, opts) in repair.items()],
        voices=[(n, q, opts) for n, (q, opts) in sorted(voices.items(), key=lambda kv: -len(kv[1][1]))],
    )


GeneratorFn = Callable[[ThirdDoorBrief, Decision], List[Option]]
OptionalGenerator = Optional[GeneratorFn]
