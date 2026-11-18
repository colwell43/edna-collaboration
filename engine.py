"""
The Collaboration Engine — the eDNA arch, with a human at the end of the line.

    "The eDNA arch: Pillar One (three lenses, nine axes) and Pillar Two (seventeen moral
     perspectives) carry the keystone, creative harmony of jealous space. Every hard call
     passes through: the machine acts and shows its reasons, or a human decides. A
     foundation of open, human-governed revision underlies today's systems."
                                                         — Minds That Matter, Figure 1

    deliberate(decision)  ->  Deliberation   the machine pauses before it acts (Ch. 11, habit 1)
    resolve(d, human)     ->  Resolution     an accountable human makes the call (Ch. 13)
    feedback(outcome)     ->  lessons        registers impact on the axes and across the
                                             seventeen perspectives; widens humility; flags
                                             patterns for the people accountable (Ch. 9, 10)
    foundation.propose / approve / apply     the only way what-counts can change (Ch. 1, 9, 11)
    run_guarded(d, act)                      agents act only when the engine authorizes

Pipeline for each option:
    measure (instrument places the option on each axis)          Pillar One — what to notice
    -> seventeen perspectives read the same measurements         Pillar Two — whose voice
    -> keystone: jealous space · harmony · creative              the keystone
    -> brakes: Danger Zone · Values Check · Drift · Fail-Safe Lock
and across options: splits by direction, dominance (no averaging), third door,
posture, the passage through the arch, audit trail, drift.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .axes import ZoneKind, get_axis
from .ensemble import (Convergence, EnsembleReading, OptionSplit, cross_option_splits, dominance,
                       read_option, unobjected)
from .failsafes import (DangerReport, DriftAlert, DriftMonitor, DriftRecord, LockState, ValueConflict,
                        danger_zone, lock_reason, value_conflicts)
from .foundation import Foundation
from .keystone import GeneratorFn, GuardBreach, JealousSpace, ThirdDoorBrief, build_brief
from .memory import Case, MoralLedger, MoralMemory, _now
from .model import (AxisAssessment, Decision, HumanDecision, Mode, Option, OutcomeFeedback, Stakes)
from .perspectives import Roster
from .policy import Thresholds
from .scoring import DeclaredInstrument, InstrumentError, weakest_grade

NAME = "eDNA Collaboration"
VERSION = "1.4.0"
FINAL_QUESTION = "What kind of world does this choice create?"


class Posture(str, Enum):
    PROCEED = "PROCEED"
    PROCEED_WITH_DISCLOSURE = "PROCEED WITH DISCLOSURE"
    OFFER_ALTERNATIVE = "PAUSE AND OFFER AN ALTERNATIVE"
    SEEK_THIRD_DOOR = "SEEK A THIRD DOOR"
    GATHER_FACTS = "GATHER BETTER FACTS"
    DEFER_TO_HUMAN = "DEFER TO A HUMAN"
    LOCKED = "LOCKED — HUMAN REVIEW REQUIRED"


AUTONOMOUS = (Posture.PROCEED, Posture.PROCEED_WITH_DISCLOSURE)

# Figure 1: every hard call passes through the arch in one of two ways.
PASSAGE_MACHINE = "THE MACHINE ACTS AND SHOWS ITS REASONS"
PASSAGE_HUMAN = "A HUMAN DECIDES"

# Acknowledgements that mean "a human chose THROUGH a warning" (counted by the drift monitor).
WARNING_ACKS = ("soft_stop", "jealous_space", "declared_value", "contested_irreversible", "demo_instrument")


@dataclass
class AxisReading:
    key: str
    position: float
    relevance: float
    confidence: float
    rationale: str
    zone_kind: ZoneKind
    zone_label: str
    margin: float

    @property
    def score(self) -> float:  # v1.0 name
        return self.position


@dataclass
class Ack:
    code: str
    message: str


@dataclass
class OptionAnalysis:
    option: Option
    measured_by: str
    grade: str
    profile: Dict[str, AxisReading]
    ensemble: EnsembleReading
    guards: List[GuardBreach]
    conflicts: List[ValueConflict]
    danger: DangerReport
    acceptable: bool
    authorizable: bool
    blockers: List[str]
    auth_blockers: List[str]
    acks: List[Ack]

    def engaged(self, floor: float) -> Dict[str, AxisReading]:
        return {k: r for k, r in self.profile.items() if r.relevance >= floor}

    def vector(self) -> Dict[str, float]:
        return {k: r.position for k, r in self.profile.items()}


@dataclass
class ReviewFlag:
    """Chapter 9: the system says so, widens its uncertainty, and brings it to the people accountable."""
    id: str
    decision_id: str
    reason: str
    axes: List[str]
    raised: str
    status: str = "open"           # open | closed
    closed_by: str = ""
    note: str = ""


@dataclass
class Deliberation:
    decision: Decision
    analyses: Dict[str, OptionAnalysis]
    frontier: List[str]
    preferred_by: Dict[str, List[str]]
    posture: Posture
    reasons: List[str]
    recommended: Optional[str]
    focus: Optional[str]
    instrument: str
    grade: Optional[str]
    roster_version: str
    roster_fingerprint: str
    thresholds_fingerprint: str
    ts: str
    third_door: Optional[ThirdDoorBrief] = None
    unmeasured: List[Option] = field(default_factory=list)
    instrument_errors: Dict[str, str] = field(default_factory=dict)
    lock: Optional[LockState] = None
    precedents: List[Tuple[Case, float]] = field(default_factory=list)
    drift_alerts: List[DriftAlert] = field(default_factory=list)
    splits: List[OptionSplit] = field(default_factory=list)
    unobjected: List[str] = field(default_factory=list)
    open_review_flags: int = 0
    weights: Dict[str, Dict[str, float]] = field(default_factory=dict)   # visible weighting (Ch. 5)
    tilts: Dict[str, Dict[str, float]] = field(default_factory=dict)
    resolution: Optional["Resolution"] = None

    @property
    def id(self) -> str:
        return self.decision.id

    @property
    def needs_human(self) -> bool:
        return self.posture not in AUTONOMOUS

    @property
    def passage(self) -> str:
        """How this call passes through the arch (Figure 1)."""
        return PASSAGE_MACHINE if self.posture in AUTONOMOUS else PASSAGE_HUMAN

    def option_label(self, oid: Optional[str]) -> str:
        if oid is None:
            return "—"
        a = self.analyses.get(oid)
        return a.option.label if a else oid

    def summary(self) -> Dict[str, Any]:
        """Compact, JSON-safe summary (what goes into the ledger)."""
        return {
            "decision_id": self.id, "question": self.decision.question,
            "mode": self.decision.mode.value, "stakes": self.decision.stakes.value,
            "passage": self.passage, "posture": self.posture.value,
            "recommended": self.recommended, "focus": self.focus,
            "reasons": self.reasons, "instrument": self.instrument, "grade": self.grade,
            "roster": {"version": self.roster_version, "fingerprint": self.roster_fingerprint},
            "thresholds_fingerprint": self.thresholds_fingerprint,
            "frontier": self.frontier,
            "splits": [s.to_dict() for s in self.splits],
            "unobjected": self.unobjected,
            "options": {
                oid: {
                    "label": a.option.label, "origin": a.option.origin, "reversible": a.option.reversible,
                    "measured_by": a.measured_by,
                    "positions": {k: [r.position, r.relevance, r.confidence] for k, r in a.profile.items()},
                    "convergence": a.ensemble.convergence.value, "counts": a.ensemble.counts(),
                    "spread": a.ensemble.spread,
                    "value_divergence": a.ensemble.value_divergence,
                    "fact_sensitive": a.ensemble.fact_sensitive,
                    "voices": {v.key: [v.stance.value, v.verdict] for v in a.ensemble.voices},
                    "guards": {g.code: g.certainty for g in a.guards},
                    "values_check": {c.code: c.certainty for c in a.conflicts},
                    "danger": a.danger.level, "danger_axes": a.danger.exposure,
                    "danger_possible": a.danger.possible, "danger_noted_pillar_two": a.danger.noted,
                    "grey_zone": a.danger.grey_zone,
                    "acceptable": a.acceptable, "authorizable": a.authorizable,
                    "acks_required": [k.code for k in a.acks],
                } for oid, a in self.analyses.items()
            },
            "third_door": None if not self.third_door else {
                "tried": self.third_door.candidates_tried, "outcome": self.third_door.outcome},
            "instrument_errors": self.instrument_errors,
            "lock": None if not self.lock else {"reason": self.lock.reason, "option": self.lock.option_id},
        }


@dataclass
class Resolution:
    decision_id: str
    chosen_option: Optional[str]
    decided_by: str
    role: str
    rationale: str
    acknowledged: List[str]
    willful_tradeoffs: List[str]
    overrode_warnings: bool
    released_lock: bool
    drift_alerts: List[DriftAlert] = field(default_factory=list)


class FeedbackResult(list):
    """A list of lessons (v1.0 behaviour) that also carries the outcome's reading and any review flags."""

    def __init__(self, lessons=(), outcome: Optional[EnsembleReading] = None,
                 flags: Optional[List[ReviewFlag]] = None):
        super().__init__(lessons)
        self.outcome = outcome
        self.flags = list(flags or [])


class AcknowledgementRequired(Exception):
    def __init__(self, missing: List[Ack]):
        self.missing = missing
        super().__init__("A human must acknowledge before choosing this option:\n" +
                         "\n".join(f"  [{a.code}] {a.message}" for a in missing))


class EngineLocked(Exception):
    pass


GOVERNED = ("The roster, thresholds and protected interests change only through the foundation: "
            "engine.foundation.propose(...), approved by named people, then .apply(...). (I11)")


class CollaborationEngine:
    def __init__(self, roster: Optional[Roster] = None, thresholds: Optional[Thresholds] = None,
                 instrument: Any = None, jealous_space: Optional[JealousSpace] = None,
                 third_door: Optional[GeneratorFn] = None, ledger: Optional[MoralLedger] = None,
                 memory: Optional[MoralMemory] = None,
                 on_alert: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
                 clock: Callable[[], str] = _now, min_approvals: int = 2):
        self._roster = roster or Roster.default()
        self._th = thresholds or Thresholds()
        self.instrument = instrument or DeclaredInstrument()
        self.jealous = jealous_space or JealousSpace()
        self.third_door = third_door
        self.clock = clock
        self.ledger = ledger or MoralLedger(clock=clock)
        self.memory = memory or MoralMemory()
        self.on_alert = on_alert
        self.drift = DriftMonitor(self._th)
        self.lock: Optional[LockState] = None
        self.review_flags: List[ReviewFlag] = []
        self.foundation = Foundation(self, min_approvals)
        self._deliberations: Dict[str, Deliberation] = {}
        self.ledger.append("engine_started", {
            "name": NAME, "version": VERSION, "roster": self._roster.version,
            "roster_fingerprint": self._roster.fingerprint(), "thresholds_fingerprint": self._th.fingerprint(),
            "protected": sorted(self.jealous.protected), "instrument": self.instrument.name})

    # ---- what counts is governed, not assignable (Invariant I11) -------------
    @property
    def roster(self) -> Roster:
        return self._roster

    @roster.setter
    def roster(self, _value) -> None:
        raise AttributeError(GOVERNED)

    @property
    def th(self) -> Thresholds:
        return self._th

    @th.setter
    def th(self, _value) -> None:
        raise AttributeError(GOVERNED)

    def _set_thresholds(self, th: Thresholds) -> None:   # called only by Foundation.apply
        self._th = th
        self.drift.th = th

    # ------------------------------------------------------------------ helpers
    def _alert(self, kind: str, message: str, payload: Dict[str, Any]) -> None:
        if self.on_alert:
            try:
                self.on_alert(kind, message, payload)
            except Exception:  # an alert hook must never break the brakes
                pass

    def _measure(self, decision: Decision, option: Option) -> Tuple[Dict[str, AxisAssessment], str, str]:
        if option.assessments:
            return dict(option.assessments), "declared (human-entered readings)", "declared"
        return self.instrument.assess(decision, option), self.instrument.name, self.instrument.grade

    def _analyze(self, decision: Decision, option: Option) -> OptionAnalysis:
        th = self.th
        readings, measured_by, grade = self._measure(decision, option)
        margins = {k: th.margin(a.confidence, self.memory.margin_bonus(k)) for k, a in readings.items()}
        profile = {}
        for k, a in readings.items():
            z = get_axis(k).zone_of(a.position)
            profile[k] = AxisReading(k, a.position, a.relevance, a.confidence, a.rationale, z.kind, z.label,
                                     round(margins[k], 3))
        ens = read_option(option, readings, self.roster, th, margins)
        guards = self.jealous.check(decision, readings, th, margins)
        conflicts = value_conflicts(decision, readings, th, margins)
        danger = danger_zone(readings, th, margins)

        blockers: List[str] = [g.message() for g in guards] + [c.message() for c in conflicts]
        if danger.level == "soft_stop":
            blockers.append("Danger Zone soft stop: " + danger.message)
        if decision.mode == Mode.ACT:
            if ens.convergence != Convergence.CONVERGENT_SUPPORT:
                blockers.append(f"The seventeen perspectives show {ens.convergence.value}, not convergent support.")
            if ens.value_divergence:
                blockers.append("Genuine value divergence among the perspectives (I3).")
            if ens.fact_sensitive:
                blockers.append("Perspective verdicts flip within measurement error — the facts are not settled.")
        elif ens.convergence not in (Convergence.CONVERGENT_SUPPORT, Convergence.LEANING_SUPPORT):
            blockers.append(f"The seventeen perspectives show {ens.convergence.value}.")
        acceptable = not blockers

        auth_blockers: List[str] = []
        if decision.mode == Mode.ACT:
            if grade == "demo":
                auth_blockers.append("A demo-grade instrument cannot authorize an action (I6).")
            if option.origin == "third_door":
                auth_blockers.append("This third door was proposed by the machine; only a human may open it (I7).")
            if not option.reversible and decision.stakes == Stakes.CRITICAL:
                auth_blockers.append("Irreversible action at critical stakes needs human confirmation (I4).")
        authorizable = acceptable and not auth_blockers

        acks = [Ack(g.code, g.message()) for g in guards] + [Ack(c.code, c.message()) for c in conflicts]
        if danger.level == "soft_stop":
            acks.append(Ack("soft_stop", danger.message))
        if decision.mode == Mode.ACT and not option.reversible and (
                ens.value_divergence or ens.convergence == Convergence.DIVERGENT):
            acks.append(Ack("contested_irreversible",
                            "You are converting a contested moral judgment into an irreversible action."))
        if decision.mode == Mode.ACT:
            if option.origin == "third_door":
                acks.append(Ack("third_door", "This door was proposed by the machine, not by you. "
                                              "Opening it is your decision, on the record."))
            if not option.reversible and decision.stakes == Stakes.CRITICAL:
                acks.append(Ack("irreversible_critical", "This action cannot be undone and the stakes are critical."))
            if grade == "demo":
                acks.append(Ack("demo_instrument", "These readings come from a demo-grade lexicon, "
                                                   "not an accountable measurement."))
        compromised = [f"{r.zone_label} ({get_axis(k).short})" for k, r in profile.items()
                       if r.relevance >= th.relevance_floor and r.zone_kind in (ZoneKind.DRIFT, ZoneKind.DANGER)]
        if compromised:
            acks.append(Ack("tradeoffs", "This option compromises " + ", ".join(compromised) +
                            ". Choosing it makes that trade-off willful, not a default."))
        return OptionAnalysis(option, measured_by, grade, profile, ens, guards, conflicts, danger,
                              acceptable, authorizable, blockers, auth_blockers, acks)

    def _apply_splits(self, decision: Decision, analyses: Dict[str, OptionAnalysis],
                      splits: List[OptionSplit]) -> None:
        """A robust split by direction is a contested judgment. Irreversible ACT options inside one
        need the same acknowledgement as a within-option divergence."""
        if decision.mode != Mode.ACT:
            return
        for s in splits:
            if not s.robust:
                continue
            for oid in (s.a, s.b):
                an = analyses[oid]
                if not an.option.reversible and all(a.code != "contested_irreversible" for a in an.acks):
                    an.acks.append(Ack("contested_irreversible",
                                       "You are converting a contested moral judgment into an irreversible "
                                       "action: the perspectives split on direction across these options."))

    def _split_text(self, analyses: Dict[str, OptionAnalysis], s: OptionSplit) -> str:
        name = {v.key: v.name for v in next(iter(analyses.values())).ensemble.voices}
        la, lb = analyses[s.a].option.label, analyses[s.b].option.label
        return (f"The perspectives split on direction: {', '.join(name[k] for k in s.object_a)} object to "
                f"'{la}', while {', '.join(name[k] for k in s.object_b)} object to '{lb}'.")

    # ---------------------------------------------------------------- deliberate
    def deliberate(self, decision: Decision) -> Deliberation:
        th = self.th
        analyses: Dict[str, OptionAnalysis] = {}
        errors: Dict[str, str] = {}
        for o in decision.options:
            try:
                analyses[o.id] = self._analyze(decision, o)
            except InstrumentError as e:
                errors[o.id] = str(e)

        frontier, preferred = dominance({k: a.ensemble for k, a in analyses.items()}) if analyses else ([], {})
        splits = cross_option_splits({k: a.ensemble for k, a in analyses.items()}, th) if analyses else []
        self._apply_splits(decision, analyses, splits)
        proposed = decision.proposed_option
        reasons: List[str] = []
        posture: Optional[Posture] = None
        recommended: Optional[str] = None
        lock: Optional[LockState] = None
        brief: Optional[ThirdDoorBrief] = None
        unmeasured: List[Option] = []

        # ---- Brake 4: the Moral Fail-Safe Lock ---------------------------------
        if proposed and proposed in analyses:
            an = analyses[proposed]
            contested = an.ensemble.value_divergence or any(s.robust and s.involves(proposed) for s in splits)
            why = lock_reason(decision, an.option, {k: AxisAssessment(r.position, r.relevance, r.confidence)
                                                    for k, r in an.profile.items()},
                              an.danger, sum(1 for g in an.guards if g.nominal_danger),
                              an.ensemble.fact_sensitive, contested, th)
            if why:
                lock = LockState(decision.id, proposed, why, self.clock())
                self.lock = lock
                self.ledger.append("lock_engaged", {"decision_id": decision.id, "option": proposed, "reason": why})
                self._alert("lock", lock.message, {"decision_id": decision.id, "reason": why})
        if self.lock and decision.mode == Mode.ACT:
            posture = Posture.LOCKED
            reasons.append(f"{self.lock.message} ({self.lock.reason}). All autonomous actions are paused "
                           f"until a named human releases the lock.")

        # ---- Creative: look for a third door — a way through the arch ----------
        candidates = [oid for oid in frontier if analyses[oid].acceptable]
        if not candidates and analyses and posture is None and not errors:
            brief = build_brief(decision, analyses, th)
            if self.third_door:
                for o in self.third_door(brief, decision):
                    if o.id in analyses:
                        o.id = f"door_{o.id}"
                    try:
                        analyses[o.id] = self._analyze(decision, o)
                        brief.candidates_tried.append(o.label)
                    except InstrumentError:
                        unmeasured.append(o)
                frontier, preferred = dominance({k: a.ensemble for k, a in analyses.items()})
                splits = cross_option_splits({k: a.ensemble for k, a in analyses.items()}, th)
                self._apply_splits(decision, analyses, splits)
                candidates = [oid for oid in frontier if analyses[oid].acceptable]
                brief.outcome = ("Third door found: " + ", ".join(analyses[c].option.label for c in candidates)
                                 if candidates else
                                 "No third door passed the checks. Said plainly: this one belongs to a human.")
            else:
                brief.outcome = "No generator configured — the brief below is for a human (or a model) to answer."

        robust_splits = [s for s in splits if s.robust]

        # ---- Posture ---------------------------------------------------------
        if errors and posture is None:
            posture = Posture.DEFER_TO_HUMAN
            reasons += [f"Instrument failure on '{k}': {v}. Failing closed (I5)." for k, v in errors.items()]
        if posture is None:
            pa = analyses.get(proposed) if proposed else None
            if pa is not None and pa.authorizable:
                recommended, posture = proposed, Posture.PROCEED
                better = [c for c in candidates if c != proposed]
                if better:
                    reasons.append("Also acceptable: " + ", ".join(analyses[c].option.label for c in better) + ".")
            elif len(candidates) == 1:
                recommended = candidates[0]
                ra = analyses[recommended]
                if proposed and recommended != proposed:
                    posture = Posture.OFFER_ALTERNATIVE
                    reasons.append(f"The proposed option '{pa.option.label if pa else proposed}' cannot be "
                                   f"authorized; '{ra.option.label}' can be offered instead.")
                elif ra.authorizable:
                    posture = Posture.PROCEED
                else:
                    posture = Posture.DEFER_TO_HUMAN
                    reasons += ra.auth_blockers
            elif len(candidates) > 1:
                posture = Posture.DEFER_TO_HUMAN
                reasons.append("More than one option passes every check and the perspectives prefer different "
                               "ones — a human choice among good options.")
            else:
                front = [analyses[f] for f in frontier] or list(analyses.values())
                facts = any(a.ensemble.fact_sensitive for a in analyses.values())
                if robust_splits:
                    posture = Posture.DEFER_TO_HUMAN
                    reasons += [self._split_text(analyses, s) for s in robust_splits]
                    reasons.append("This is a disagreement about direction, not only about one option. "
                                   "Do not manufacture certainty: this one belongs to a human.")
                    if facts:
                        reasons.append("The facts are also unsettled. Gather them — but better facts alone "
                                       "will not settle a split about direction.")
                elif any(a.ensemble.value_divergence for a in front):
                    posture = Posture.DEFER_TO_HUMAN
                    reasons.append("Reasonable moral perspectives genuinely disagree and no third door passed "
                                   "the checks. Do not manufacture certainty: this one belongs to a human.")
                elif any(a.ensemble.fact_sensitive for a in front):
                    posture = Posture.GATHER_FACTS
                    reasons.append("The disagreement is about facts, not values: verdicts flip within "
                                   "measurement error. Get better facts, then deliberate again.")
                elif self.third_door is None:
                    posture = Posture.SEEK_THIRD_DOOR
                    reasons.append("No option can be authorized. Look for a third door (brief below); "
                                   "if none exists, this belongs to a human.")
                else:
                    posture = Posture.DEFER_TO_HUMAN
                    reasons.append("No option — including the third doors tried — passes the checks.")
            if pa is not None and recommended != proposed:
                ack_msgs = [a.message for a in pa.acks]
                reasons += [f"Proposed '{pa.option.label}': {b}" for b in pa.blockers + pa.auth_blockers
                            if not any(m in b for m in ack_msgs)]

        if posture == Posture.LOCKED and len(candidates) == 1 and candidates[0] != proposed:
            recommended = candidates[0]
            reasons.append(f"A safer alternative passes every check: '{analyses[recommended].option.label}'. "
                           "A human must still release the lock to act on it.")

        if posture == Posture.PROCEED and recommended:
            ra = analyses[recommended]
            disclose = []
            if ra.danger.level == "caution":
                disclose.append(ra.danger.message)
            if ra.danger.grey_zone:
                disclose.append(ra.danger.grey_message)
            if ra.ensemble.convergence != Convergence.CONVERGENT_SUPPORT:
                disclose.append(f"The perspectives show {ra.ensemble.convergence.value}, not convergence.")
            if ra.ensemble.value_divergence:
                disclose.append("Some perspectives object on grounds of value; the conflict is disclosed, not hidden.")
            if ra.ensemble.fact_sensitive:
                disclose.append("Some verdicts depend on facts that are uncertain.")
            for s in splits:
                if s.involves(recommended):
                    disclose.append(self._split_text(analyses, s))
            if not ra.option.reversible:
                disclose.append("This action is irreversible.")
            if recommended not in frontier:
                dom = [analyses[f].option.label for f in frontier]
                disclose.append(f"Note: {', '.join(dom)} is preferred by every perspective that tells them apart.")
            if disclose:
                posture = Posture.PROCEED_WITH_DISCLOSURE
                reasons += disclose

        focus = proposed or recommended or (frontier[0] if frontier else (next(iter(analyses), None)))
        grades = [a.grade for a in analyses.values()]
        d = Deliberation(
            decision=decision, analyses=analyses, frontier=frontier, preferred_by=preferred,
            posture=posture, reasons=reasons, recommended=recommended, focus=focus,
            instrument=(analyses[focus].measured_by if focus in analyses else self.instrument.name),
            grade=weakest_grade(grades), roster_version=self.roster.version,
            roster_fingerprint=self.roster.fingerprint(), thresholds_fingerprint=self.th.fingerprint(),
            ts=self.clock(), third_door=brief, unmeasured=unmeasured, instrument_errors=errors,
            lock=lock or (self.lock if decision.mode == Mode.ACT else None),
            splits=splits, unobjected=unobjected({k: a.ensemble for k, a in analyses.items()}) if splits else [],
            open_review_flags=sum(1 for f in self.review_flags if f.status == "open"),
            weights={p.name: dict(p.weights) for p in self.roster},
            tilts={p.name: dict(p.tilt) for p in self.roster if p.tilt},
        )
        if focus in analyses:
            d.precedents = self.memory.precedents(decision.tags, analyses[focus].vector(), exclude=decision.id)
        self.ledger.append("deliberation", d.summary())
        self._deliberations[decision.id] = d
        if posture in AUTONOMOUS and recommended:
            d.drift_alerts = self._executed(d, recommended, overrode=False)
        return d

    # ------------------------------------------------------------ execution/drift
    def _executed(self, d: Deliberation, oid: str, overrode: bool) -> List[DriftAlert]:
        an = d.analyses[oid]
        self.drift.record(DriftRecord(d.id, oid, self.clock(),
                                      {k: r.position for k, r in an.profile.items()
                                       if r.relevance >= self.th.relevance_floor},
                                      danger_axes=len(an.danger.axes), overrode=overrode))
        self.memory.add_case(Case(d.id, d.decision.question, list(d.decision.tags), oid, an.option.label,
                                  {k: r.position for k, r in an.profile.items()}))
        alerts = self.drift.check()
        for a in alerts:
            self.ledger.append("drift_alert", {"decision_id": d.id, "kind": a.kind, "axis": a.axis,
                                               "message": a.message})
            self._alert("drift", a.message, {"decision_id": d.id, "axis": a.axis})
        return alerts

    # ------------------------------------------------------------------- resolve
    def resolve(self, deliberation: Deliberation | str, human: HumanDecision) -> Resolution:
        d = deliberation if isinstance(deliberation, Deliberation) else self._deliberations[deliberation]
        if d.resolution is not None:
            raise ValueError(f"decision {d.id} was already resolved by {d.resolution.decided_by}")
        released = False
        if self.lock and d.decision.mode == Mode.ACT and human.chosen_option is not None:
            if not human.release_lock:
                raise EngineLocked(f"{self.lock.message} Set release_lock=True to release it as {human.decided_by}.")
            self.release_lock(human.decided_by, human.role, human.rationale)
            released = True
        tradeoffs: List[str] = []
        overrode = False
        if human.chosen_option is not None:
            if human.chosen_option not in d.analyses:
                raise KeyError(f"'{human.chosen_option}' is not an option in decision {d.id}")
            an = d.analyses[human.chosen_option]
            missing = [a for a in an.acks if a.code not in human.acknowledged]
            if missing:
                raise AcknowledgementRequired(missing)
            tradeoffs = [k for k, r in an.profile.items() if r.relevance >= self.th.relevance_floor
                         and r.zone_kind in (ZoneKind.DRIFT, ZoneKind.DANGER)]
            overrode = any(a.code.startswith(WARNING_ACKS) for a in an.acks)
        res = Resolution(d.id, human.chosen_option, human.decided_by, human.role, human.rationale,
                         list(human.acknowledged), tradeoffs, overrode, released)
        self.ledger.append("human_decision", {
            "decision_id": d.id, "chosen": human.chosen_option, "decided_by": human.decided_by,
            "role": human.role, "rationale": human.rationale, "acknowledged": list(human.acknowledged),
            "willful_tradeoffs": tradeoffs, "overrode_warnings": overrode, "machine_posture": d.posture.value,
            "machine_recommended": d.recommended})
        if human.chosen_option is not None:
            res.drift_alerts = self._executed(d, human.chosen_option, overrode)
        d.resolution = res
        return res

    def release_lock(self, by: str, role: str, rationale: str) -> None:
        if not self.lock:
            return
        if not by.strip() or not rationale.strip():
            raise ValueError("releasing the lock needs a named person and a rationale")
        self.ledger.append("lock_released", {"decision_id": self.lock.decision_id, "by": by, "role": role,
                                             "rationale": rationale, "reason_was": self.lock.reason})
        self.lock = None

    # ------------------------------------------------------------------ feedback
    def feedback(self, fb: OutcomeFeedback) -> FeedbackResult:
        """Chapter 10: evaluate how the outcome registered on the axes and across the seventeen
        perspectives. Chapter 9: widen uncertainty where the system was wrong, surface the case,
        and flag the pattern for human review — never quietly rewrite its own values."""
        case = self.memory.case(fb.decision_id)
        if case is None:
            raise KeyError(f"no executed decision '{fb.decision_id}' to learn from")
        lessons = self.memory.learn(fb, case)

        observed = {k: AxisAssessment(v, 0.8, 0.8, "observed outcome") for k, v in fb.observed.items()}
        outcome = read_option(Option(case.option_id, case.option_label), observed, self.roster, self.th, {})
        c = outcome.counts()
        lessons.append(f"Across the seventeen perspectives the outcome drew {c['supports']} support, "
                       f"{c['objects']} objection(s), {c['ambivalent']} ambivalent ({outcome.convergence.value}).")

        flags: List[ReviewFlag] = []
        missed = [k for k in fb.observed if k in case.predicted and
                  get_axis(k).zone_of(fb.observed[k]).kind != get_axis(k).zone_of(case.predicted[k]).kind]
        pattern = [k for k in missed if self.memory.misses.get(k, 0) >= 2]
        objected = outcome.convergence == Convergence.CONVERGENT_OBJECTION
        in_danger = [k for k, v in fb.observed.items() if get_axis(k).zone_of(v).kind == ZoneKind.DANGER]
        if objected or in_danger or pattern:
            why = []
            if objected:
                why.append("the outcome drew convergent objection across the seventeen perspectives")
            if in_danger:
                why.append("the outcome reached the unhealthy end of " +
                           ", ".join(f"{get_axis(k).short} ({get_axis(k).zone_of(fb.observed[k]).label})"
                                     for k in in_danger))
            if pattern:
                why.append("the readings have now been wrong more than once on " +
                           ", ".join(get_axis(k).short for k in pattern))
            flag = ReviewFlag(uuid.uuid4().hex[:8], fb.decision_id, "; ".join(why),
                              sorted(set(missed + pattern + in_danger)),
                              self.clock())
            self.review_flags.append(flag)
            flags.append(flag)
            lessons.append(f"Flagged for human review (flag {flag.id}): {flag.reason}. Nothing about what counts "
                           "has been changed; any change goes through the foundation.")
            self.ledger.append("review_flag", {"flag": flag.id, "decision_id": fb.decision_id,
                                               "reason": flag.reason, "axes": flag.axes})
            self._alert("review", flag.reason, {"flag": flag.id, "decision_id": fb.decision_id})

        self.ledger.append("outcome_feedback", {"decision_id": fb.decision_id, "observed": fb.observed,
                                                "notes": fb.notes, "reporter": fb.reporter, "lessons": lessons,
                                                "outcome_convergence": outcome.convergence.value,
                                                "calibration": dict(self.memory.calibration)})
        return FeedbackResult(lessons, outcome, flags)

    def close_flag(self, flag_id: str, by: str, role: str, note: str) -> ReviewFlag:
        flag = next((f for f in self.review_flags if f.id == flag_id), None)
        if flag is None:
            raise KeyError(flag_id)
        if not by.strip() or not note.strip():
            raise ValueError("closing a review flag needs a named person and a note")
        flag.status, flag.closed_by, flag.note = "closed", by, note
        self.ledger.append("review_flag_closed", {"flag": flag_id, "by": by, "role": role, "note": note})
        return flag

    # ------------------------------------------------------------- agent wrapper
    def authorize(self, d: Deliberation) -> bool:
        return d.posture in AUTONOMOUS and d.recommended is not None and not (
            self.lock and d.decision.mode == Mode.ACT)

    def run_guarded(self, decision: Decision, act: Callable[[Option], Any]) -> Tuple[Deliberation, Any]:
        """Pause before acting: the action runs only if the engine authorizes it."""
        d = self.deliberate(decision)
        if self.authorize(d):
            return d, act(d.analyses[d.recommended].option)
        return d, None

    def get(self, decision_id: str) -> Deliberation:
        return self._deliberations[decision_id]
