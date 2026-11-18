"""
Brakes — the four layers of protection (Minds That Matter, Chapter 12).

  1. The Ethical Danger Zone — "each decision is measured on each of the nine ethical axes.
                               When those measurements cluster toward extremes ... the system
                               enters a 'Danger Zone': a decision near the unhealthy end of
                               several axes at once." -> soft stop. One axis alone -> a warning.
                               v1.3: each axis is read across its measurement range.
                               v1.4: only the nine Pillar One axes count (Pillar Two features are
                               noted, not counted) — a governed setting.
  2. Values Check            — the request conflicts with the values the organization has
                               publicly declared.
  3. Ethical Drift Detection — tiny compromises add up; patterns are logged and visualized.
  4. The Moral Fail-Safe Lock — irreparable harm + murky data: pause all autonomous action,
                               alert human oversight, log the violation.

Every brake rests on a prior choice about what counts as harm; Chapter Five showed
why that choice cannot belong to one tradition. The last brake hands the decision
back to a human.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .axes import AXES, Strand, ZoneKind, get_axis
from .model import AxisAssessment, Decision, Mode, Option
from .policy import Thresholds


def _join(names: List[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def _lean_pole(key: str, score: float) -> str:
    a = get_axis(key)
    return a.neg_pole if score < 0 else a.pos_pole


# ---------------------------------------------------------------------------
# Brake 1 — the Ethical Danger Zone (+ the grey zone of Chapter 8)
# ---------------------------------------------------------------------------
@dataclass
class DangerReport:
    level: str                      # "none" | "caution" | "soft_stop"
    axes: List[str]                 # axes counted at the unhealthy end: in a danger zone, or (v1.3)
                                    # with enough of their measurement range reaching one
    message: str = ""
    recommendations: List[str] = field(default_factory=list)
    grey_zone: bool = False         # no CLEAR violation, but several readings drifting toward vice
    grey_message: str = ""
    possible: List[str] = field(default_factory=list)       # subset of axes counted only by their range
    exposure: Dict[str, float] = field(default_factory=dict)  # axis -> share of range in a danger zone
    nominal_soft_stop: bool = False  # would be a soft stop on exact readings alone (what the lock uses)
    noted: List[str] = field(default_factory=list)  # v1.4: Pillar Two features at their unhealthy end —
                                                    # shown, but not counted toward the Danger Zone


def _soft(keys: List[str], th: Thresholds) -> bool:
    strands = {get_axis(k).strand for k in keys}
    n = th.danger_axes_soft_stop
    return (len(keys) >= n and (n == 1 or len(strands) >= 2)) or len(keys) >= 3


def danger_zone(readings: Dict[str, AxisAssessment], th: Thresholds,
                margins: Optional[Dict[str, float]] = None) -> DangerReport:
    """Brake 1. "A decision near the unhealthy end of several axes at once." (Ch. 12)

    v1.3: like the guards, each axis is read across its whole measurement range. An axis counts
    toward the Danger Zone when its exact reading is in a danger zone, OR when at least
    `guard_exposure` (default one third) of its range reaches one ("possibly"). Two readings a
    hair short of the line no longer slip past while two a hair over it stop the decision.
    The Moral Fail-Safe Lock still uses exact readings only (nominal_soft_stop).
    """
    counted, possible, nominal, drift, noted = [], [], [], [], []
    exposure: Dict[str, float] = {}
    dz = {ZoneKind.DANGER}
    for k, a in readings.items():
        if a.relevance < th.relevance_floor:
            continue
        axis = get_axis(k)
        m = (margins or {}).get(k, th.margin(a.confidence))
        share, inside = axis.exposure(a.position, m, dz)
        if th.danger_zone_nine_axes_only and not axis.pillar_one:
            # v1.4: "each decision is measured on each of the nine ethical axes" (Ch. 12). Pillar Two
            # features are noted, not counted; they still weigh through the seventeen perspectives.
            if inside or share >= th.guard_exposure:
                noted.append(k)
            continue
        if inside or share >= th.guard_exposure:
            counted.append(k)
            exposure[k] = round(share, 3)
            if inside:
                nominal.append(k)
            else:
                possible.append(k)
        if axis.zone_of(a.position).kind == ZoneKind.DRIFT:
            drift.append(k)

    def vice_of(k: str) -> str:
        a, s = get_axis(k), readings[k].position
        return a.nearest_zone(s, dz).label

    def pole_of(k: str) -> str:
        z = get_axis(k).nearest_zone(readings[k].position, dz)
        return _lean_pole(k, (z.lo + z.hi) / 2)

    recs = [f"{get_axis(k).short}: {get_axis(k).repair_for(readings[k].position)}" for k in counted]
    grey = not nominal and len(drift) >= 2
    grey_msg = ""
    if grey:
        vices = [f"{get_axis(k).zone_of(readings[k].position).label} ({get_axis(k).short})" for k in drift]
        grey_msg = ("Grey zone: no clear violation, but several readings are drifting toward vice — "
                    f"{_join(vices)}. No rule is broken; it can still do real harm.")
        if possible:
            grey_msg += (" Within measurement error, though, the range reaches the unhealthy end on "
                         f"{_join([get_axis(k).short for k in possible])}.")
    base = dict(possible=possible, exposure=exposure, nominal_soft_stop=_soft(nominal, th), noted=noted)
    if _soft(counted, th):
        names = [pole_of(k) + (" (possibly)" if k in possible else "") for k in counted]
        msg = (f"This decision shows high dissonance across {_join(names)}. "
               "Proceeding could result in moral harm. Do you wish to continue?")
        if possible:
            msg += (" ('Possibly' marks a reading near the line whose measurement range reaches the "
                    "unhealthy end.)")
        return DangerReport("soft_stop", counted, msg, recs, grey, grey_msg, **base)
    if counted:
        parts = []
        for k in counted:
            a, s = get_axis(k), readings[k].position
            vice = vice_of(k)
            if k in possible:
                if pole_of(k) == a.neg_pole:
                    parts.append(f"This choice may activate {a.neg_pole}: {exposure[k]:.0%} of its measurement range "
                                 f"reaches {vice}, and it could degrade {a.pos_pole} over time.")
                else:
                    parts.append(f"This choice may overshoot into {vice} on {a.short}: {exposure[k]:.0%} of its "
                                 "measurement range is there.")
            elif s < 0:
                named = a.neg_pole if vice == a.neg_pole else f"{a.neg_pole} ({vice})"
                parts.append(f"This choice activates {named} and could degrade {a.pos_pole} over time.")
            else:
                parts.append(f"This choice overshoots into {vice} on {a.short}.")
        return DangerReport("caution", counted, " ".join(parts), recs, grey, grey_msg, **base)
    return DangerReport("none", [], "", [], grey, grey_msg, **base)


# ---------------------------------------------------------------------------
# Brake 2 — the Values Check
# ---------------------------------------------------------------------------
@dataclass
class ValueConflict:
    value: str
    statement: str
    feature: str
    floor: float
    position: float
    margin: float = 0.0
    exposure: float = 1.0
    certainty: str = "likely"     # certain | likely | possible

    @property
    def code(self) -> str:
        return f"declared_value:{self.value}"

    def message(self) -> str:
        rng = f"{self.position:+.2f} ± {self.margin:.2f}"
        lead = ("This request may conflict" if self.certainty == "possible" else "This request conflicts")
        return (f"{lead} with the values your organization has publicly declared. This direction may "
                f"misalign with your {self.value} goals ({get_axis(self.feature).short} measured {rng}; "
                f"declared floor {self.floor:+.2f}; {self.exposure:.0%} of the measurement range falls below "
                "it). Proceed anyway?")


def _below_floor_share(position: float, margin: float, floor: float) -> float:
    lo, hi = max(-1.0, position - margin), min(1.0, position + margin)
    if hi - lo <= 1e-12:
        return 1.0 if position < floor else 0.0
    return max(0.0, min(hi, floor) - lo) / (hi - lo)


def value_conflicts(decision: Decision, readings: Dict[str, AxisAssessment], th: Thresholds,
                    margins: Optional[Dict[str, float]] = None) -> List[ValueConflict]:
    """v1.2: a declared floor is checked against the whole measurement range, like the guards."""
    out = []
    for dv in decision.declared_values:
        for f, floor in dv.floors.items():
            a = readings.get(f)
            if a is None or a.relevance < th.relevance_floor:
                continue
            m = (margins or {}).get(f, th.margin(a.confidence))
            share = _below_floor_share(a.position, m, floor)
            inside = a.position < floor
            if inside or share >= th.guard_exposure:
                certainty = "certain" if share >= 0.999 else ("likely" if inside else "possible")
                out.append(ValueConflict(dv.name, dv.statement, f, floor, a.position, round(m, 3),
                                         round(share, 3), certainty))
    return out


# ---------------------------------------------------------------------------
# Brake 4 — the Moral Fail-Safe Lock
# ---------------------------------------------------------------------------
LOCK_MESSAGE = "Potential for irreparable harm exceeds ethical tolerance. Requiring human review."


@dataclass
class LockState:
    decision_id: str
    option_id: str
    reason: str
    engaged_at: str
    message: str = LOCK_MESSAGE


def lock_reason(decision: Decision, option: Option, readings: Dict[str, AxisAssessment],
                danger: DangerReport, guard_dangers: int, fact_sensitive: bool,
                value_divergence: bool, th: Thresholds) -> Optional[str]:
    """Return why the lock must engage for this proposed action, or None."""
    if decision.mode != Mode.ACT or option.reversible:
        return None
    ge = readings.get("good_evil")
    harm = ge is not None and ge.relevance >= th.relevance_floor and \
        get_axis("good_evil").zone_of(ge.position).kind == ZoneKind.DANGER
    severe = harm or guard_dangers >= 2 or danger.nominal_soft_stop   # exact readings only
    engaged = [a for a in readings.values() if a.relevance >= th.relevance_floor]
    mean_conf = sum(a.confidence for a in engaged) / len(engaged) if engaged else 0.0
    murky = fact_sensitive or value_divergence or mean_conf < th.low_confidence
    if severe and murky:
        why = []
        if harm:
            why.append("potential for serious harm")
        if guard_dangers >= 2:
            why.append(f"{guard_dangers} protected interests in danger")
        if danger.nominal_soft_stop:
            why.append("high dissonance across lenses")
        why.append("irreversible action")
        if mean_conf < th.low_confidence:
            why.append(f"murky data (mean confidence {mean_conf:.2f})")
        if fact_sensitive:
            why.append("verdicts flip within measurement error")
        if value_divergence:
            why.append("genuine moral disagreement")
        return "; ".join(why)
    return None


# ---------------------------------------------------------------------------
# Brake 3 — Ethical Drift Detection
# ---------------------------------------------------------------------------
@dataclass
class DriftRecord:
    decision_id: str
    option_id: str
    ts: str
    scores: Dict[str, float]
    danger_axes: int = 0
    overrode: bool = False          # a human chose through a warning (soft stop, guard, declared value)


@dataclass
class DriftAlert:
    kind: str                       # "axis" | "danger" | "override"
    message: str
    axis: str = ""
    delta: float = 0.0


_TONE = {Strand.HEAD: "Reasoning", Strand.HEART: "Emotional tone",
         Strand.HORIZON: "Long-term outlook", Strand.PILLAR_TWO: "Cultural commitment"}
_BLOCKS = "▁▂▃▄▅▆▇█"


class DriftMonitor:
    def __init__(self, th: Thresholds):
        self.th = th
        self.records: List[DriftRecord] = []

    def record(self, rec: DriftRecord) -> None:
        self.records.append(rec)

    def _window(self, recs: List[DriftRecord], key: str):
        xs = [r.scores[key] for r in recs if key in r.scores]
        return xs if len(xs) * 2 >= len(recs) else None

    def check(self) -> List[DriftAlert]:
        w = self.th.drift_window
        if len(self.records) < 2 * w:
            return []
        base, recent = self.records[-2 * w:-w], self.records[-w:]
        alerts: List[DriftAlert] = []
        for key, axis in AXES.items():
            b, r = self._window(base, key), self._window(recent, key)
            if not b or not r:
                continue
            mb, mr = sum(b) / len(b), sum(r) / len(r)
            ub = sum(axis.utility(x) for x in b) / len(b)
            ur = sum(axis.utility(x) for x in r) / len(r)
            ds = mr - mb
            if abs(ds) >= self.th.drift_delta and (ur - ub) <= -0.25:
                toward = axis.neg_pole if ds < 0 else axis.pos_pole
                zone = axis.zone_of(mr)
                msg = (f"{_TONE[axis.strand]} has shifted toward {toward}: the {axis.label} axis is trending "
                       f"toward {toward.lower()} (Δ {ds:+.2f}; now in {zone.kind.value}")
                msg += f": {zone.label})." if zone.label else ")."
                if ds < 0:
                    msg += f" {axis.pos_pole} trending down."
                msg += f" Recommend: {axis.repair_for(mr)}."
                alerts.append(DriftAlert("axis", msg, key, round(ds, 3)))
        db = sum(1 for x in base if x.danger_axes) / w
        dr = sum(1 for x in recent if x.danger_axes) / w
        if dr - db >= 0.4:
            alerts.append(DriftAlert("danger", f"Danger-zone decisions are rising: {dr:.0%} of recent decisions "
                                               f"vs {db:.0%} before."))
        ov = sum(1 for x in recent if x.overrode)
        if ov >= 2 and ov / w >= self.th.override_alert_share:
            alerts.append(DriftAlert("override",
                                     f"Warnings are being overridden routinely ({ov} of the last {w} decisions). "
                                     "Ethical failures rarely happen in one big moment; they happen through a "
                                     "series of tiny compromises. Review the pattern."))
        return alerts

    def sparkline(self, key: str) -> str:
        out = []
        for r in self.records:
            if key not in r.scores:
                out.append(" ")
            else:
                i = int(round((r.scores[key] + 1) / 2 * (len(_BLOCKS) - 1)))
                out.append(_BLOCKS[max(0, min(len(_BLOCKS) - 1, i))])
        return "".join(out)

    def dashboard(self) -> str:
        if not self.records:
            return "No decisions recorded yet."
        lines = [f"Drift dashboard — {len(self.records)} decisions; each mark is where the executed choice sat "
                 "on the axis (▁ = second pole, █ = first pole)"]
        for key, axis in AXES.items():
            if any(key in r.scores for r in self.records):
                lines.append(f"  {axis.short:<34} {self.sparkline(key)}")
        return "\n".join(lines)
