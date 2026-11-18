"""
Reading an option through the seventeen perspectives (Pillar Two, Chapter 5) — and holding the spread.

For each perspective p and option o:

    verdict(p, o) = Σ_f  w_p(f)·rel(f)·u_f(position_f − tilt_p(f))  /  Σ_f w_p(f)·rel(f)

where u_f is the Pillar One zone utility (and a perspective objects outright when one of
its central commitments is in danger — see read_voice). Taking each reading to the
worst and best zone reachable inside its measurement margin, and combining those
shifts as independent errors, gives an interval.
That interval is what lets the engine tell a FACTUAL problem (the stance flips
inside measurement error — "get better facts") from a MORAL disagreement (perspectives
split even when the readings are taken as given — "do not manufacture certainty").

Two shapes of moral disagreement are detected, and neither is averaged away:
  * WITHIN one option — some perspectives support it, others object (read_option);
  * ACROSS options — different families of perspectives object to OPPOSITE options, a split
    about direction (cross_option_splits, new in v1.1).

Nothing here averages the seventeen verdicts into one number. The outputs are counts,
a convergence class, a spread, splits, and a dominance comparison across options.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .axes import ZoneKind, get_axis
from .model import AxisAssessment, Option
from .perspectives import Perspective, Roster
from .policy import Thresholds


class Stance(str, Enum):
    SUPPORTS = "supports"
    OBJECTS = "objects"
    AMBIVALENT = "ambivalent"
    ABSTAINS = "abstains"


class Convergence(str, Enum):
    CONVERGENT_SUPPORT = "convergent support"
    CONVERGENT_OBJECTION = "convergent objection"
    DIVERGENT = "divergent"
    LEANING_SUPPORT = "leaning support"
    LEANING_OBJECTION = "leaning objection"
    UNSETTLED = "unsettled"
    INSUFFICIENT = "insufficient voices"


@dataclass
class Voice:
    key: str
    name: str
    family: str
    focal_question: str
    stance: Stance
    verdict: Optional[float] = None       # None when the perspective abstains
    lo: Optional[float] = None
    hi: Optional[float] = None
    robust: bool = True                   # stance unchanged across the measurement interval
    drivers: List[Tuple[str, float]] = field(default_factory=list)  # (feature, signed contribution)
    veto: Optional[str] = None            # central commitment in danger (objects regardless of the sum)

    def concern(self, n: int = 2) -> List[str]:
        """The features pulling this perspective toward objection, most negative first (a veto leads)."""
        ks = [k for k, c in sorted(self.drivers, key=lambda kv: kv[1]) if c < 0]
        if self.veto:
            ks = [self.veto] + [k for k in ks if k != self.veto]
        return ks[:n]

    def appreciation(self, n: int = 2) -> List[str]:
        return [k for k, c in sorted(self.drivers, key=lambda kv: -kv[1]) if c > 0][:n]


@dataclass
class EnsembleReading:
    option_id: str
    voices: List[Voice]
    convergence: Convergence
    value_divergence: bool      # split survives measurement uncertainty -> it is about values
    fact_sensitive: bool        # many stances flip inside measurement error -> it is about facts
    spread: Dict[str, float]    # range / IQR of verdicts — a dispersion, never a mean

    def by(self, stance: Stance) -> List[Voice]:
        return [v for v in self.voices if v.stance == stance]

    @property
    def n_voices(self) -> int:
        return sum(1 for v in self.voices if v.stance != Stance.ABSTAINS)

    def counts(self) -> Dict[str, int]:
        return {s.value: len(self.by(s)) for s in Stance}

    def verdict_of(self, key: str) -> float:
        for v in self.voices:
            if v.key == key:
                return v.verdict if v.verdict is not None else 0.0
        raise KeyError(key)


def _stance(v: float, cut: float) -> Stance:
    if v >= cut:
        return Stance.SUPPORTS
    if v <= -cut:
        return Stance.OBJECTS
    return Stance.AMBIVALENT


CENTRAL_SALIENCE = 3.0      # a perspective's central commitments
CENTRAL_RELEVANCE = 0.5     # ... engaged at least this much


def read_voice(p: Perspective, readings: Dict[str, AxisAssessment],
               margins: Dict[str, float], th: Thresholds) -> Voice:
    """One perspective reads one option.

    Two rules, both disclosed:
      * Weighted zone utilities give the verdict. The interval combines each reading's
        measurement margin as independent errors (root-sum-square), not as a worst case
        where every reading is wrong in the same direction at once.
      * Central commitments are not traded for peripheral gains: if a feature this perspective
        holds central (salience 3) is engaged and in DANGER, the perspective objects — a
        side-constraint inside the perspective, mirroring jealous space at the center.
    """
    num = den = 0.0
    down2 = up2 = 0.0
    contrib: List[Tuple[str, float]] = []
    veto_nominal: Optional[str] = None
    veto_possible = veto_certain = False
    for f, a in readings.items():
        w = p.w(f) * a.relevance
        if w <= 0:
            continue
        axis = get_axis(f)
        s = a.position - p.tilt.get(f, 0.0)
        u = axis.utility(s)
        m = margins.get(f, th.margin(a.confidence))
        ulo, uhi = axis.utility_range(s - m, s + m)
        num += w * u
        den += w
        down2 += (w * (u - ulo)) ** 2
        up2 += (w * (uhi - u)) ** 2
        contrib.append((f, w * u))
        if p.w(f) >= CENTRAL_SALIENCE and a.relevance >= CENTRAL_RELEVANCE:
            possible, certain = axis.danger_reach(s - m, s + m)
            if axis.zone_of(s).kind == ZoneKind.DANGER and veto_nominal is None:
                veto_nominal = f
            veto_possible = veto_possible or possible
            veto_certain = veto_certain or certain
    if den < th.min_engaged_weight:
        return Voice(p.key, p.name, p.family, p.focal_question, Stance.ABSTAINS)
    v = num / den
    vlo, vhi = v - math.sqrt(down2) / den, v + math.sqrt(up2) / den
    cut = th.support_cut
    stance = Stance.OBJECTS if veto_nominal else _stance(v, cut)
    s_lo = Stance.OBJECTS if veto_possible else _stance(vlo, cut)
    s_hi = Stance.OBJECTS if veto_certain else _stance(vhi, cut)
    # A stance "flips" when measurement error alone could carry it into the OPPOSITE camp.
    # (Support weakening to ambivalence is softer evidence, not a flip.)
    if stance == Stance.SUPPORTS:
        robust = s_lo != Stance.OBJECTS
    elif stance == Stance.OBJECTS:
        robust = s_hi != Stance.SUPPORTS
    else:
        robust = not (s_lo == Stance.OBJECTS and s_hi == Stance.SUPPORTS)
    return Voice(p.key, p.name, p.family, p.focal_question, stance,
                 round(v, 3), round(vlo, 3), round(vhi, 3), robust=robust,
                 drivers=[(f, round(c / den, 3)) for f, c in contrib], veto=veto_nominal)


def _quantile(xs: List[float], q: float) -> float:
    xs = sorted(xs)
    if not xs:
        return 0.0
    pos = (len(xs) - 1) * q
    i, frac = int(pos), pos - int(pos)
    return xs[i] if i + 1 >= len(xs) else xs[i] + (xs[i + 1] - xs[i]) * frac


def read_option(option: Option, readings: Dict[str, AxisAssessment], roster: Roster,
                th: Thresholds, margins: Dict[str, float]) -> EnsembleReading:
    voices = [read_voice(p, readings, margins, th) for p in roster]
    active = [v for v in voices if v.stance != Stance.ABSTAINS]
    n = len(active)
    S = sum(1 for v in active if v.stance == Stance.SUPPORTS)
    O = sum(1 for v in active if v.stance == Stance.OBJECTS)
    rS = sum(1 for v in active if v.stance == Stance.SUPPORTS and v.robust)
    rO = sum(1 for v in active if v.stance == Stance.OBJECTS and v.robust)
    flips = sum(1 for v in active if not v.robust)

    if n < th.min_voices:
        conv = Convergence.INSUFFICIENT
    elif S >= th.convergence_share * n and O <= th.convergence_dissent_max * n:
        conv = Convergence.CONVERGENT_SUPPORT
    elif O >= th.convergence_share * n and S <= th.convergence_dissent_max * n:
        conv = Convergence.CONVERGENT_OBJECTION
    elif S >= th.divergence_share * n and O >= th.divergence_share * n:
        conv = Convergence.DIVERGENT
    elif S > O and S >= 0.5 * n:
        conv = Convergence.LEANING_SUPPORT
    elif O > S and O >= 0.5 * n:
        conv = Convergence.LEANING_OBJECTION
    else:
        conv = Convergence.UNSETTLED

    value_div = n >= th.min_voices and rS >= th.divergence_share * n and rO >= th.divergence_share * n
    fact_sens = n >= 1 and flips >= th.fact_sensitivity_share * n
    vs = [v.verdict for v in active]
    spread = {
        "min": round(min(vs), 3) if vs else 0.0,
        "max": round(max(vs), 3) if vs else 0.0,
        "range": round(max(vs) - min(vs), 3) if vs else 0.0,
        "iqr": round(_quantile(vs, 0.75) - _quantile(vs, 0.25), 3) if vs else 0.0,
    }
    return EnsembleReading(option.id, voices, conv, value_div, fact_sens, spread)


def dominance(readings: Dict[str, EnsembleReading], eps: float = 0.05) -> Tuple[List[str], Dict[str, List[str]]]:
    """Pareto comparison across options without weighing one perspective against another.

    Option A dominates B if no perspective prefers B to A (beyond eps) and at least one perspective
    prefers A. Returns the non-dominated frontier and, for each option, the perspectives
    that rank it first.
    """
    ids = list(readings)
    keys = [v.key for v in next(iter(readings.values())).voices] if readings else []

    def dom(a: str, b: str) -> bool:
        better = False
        for k in keys:
            va, vb = readings[a].verdict_of(k), readings[b].verdict_of(k)
            if va < vb - eps:
                return False
            if va > vb + eps:
                better = True
        return better

    frontier = [a for a in ids if not any(dom(b, a) for b in ids if b != a)]
    preferred: Dict[str, List[str]] = {i: [] for i in ids}
    for k in keys:
        best = max(readings[i].verdict_of(k) for i in ids)
        if all(readings[i].verdict_of(k) == 0.0 for i in ids):
            continue
        for i in ids:
            if readings[i].verdict_of(k) >= best - 1e-9:
                name = next(v.name for v in readings[i].voices if v.key == k)
                preferred[i].append(name)
    return frontier, preferred


# ---------------------------------------------------------------------------
# v1.1 — the split ACROSS options
# ---------------------------------------------------------------------------
# v1.0 only saw disagreement inside one option (some perspectives support it, others object).
# It missed the other shape of moral conflict: different families of perspectives
# objecting to OPPOSITE options — e.g. care and communal traditions objecting to one
# door while autonomy-centred traditions object to the opposite door. That is a
# disagreement about DIRECTION, and better facts alone will not settle it.
PREFERENCE_MARGIN = 0.10      # a perspective "prefers" a over b when its verdicts differ by at least this
SPLIT_MIN_OBJECTORS = 2       # each side must include at least this many perspectives objecting to the other door


@dataclass
class OptionSplit:
    a: str
    b: str
    favor_a: List[str]                 # perspective keys preferring a over b
    favor_b: List[str]
    object_a: List[str]                # perspectives (among favor_b) that object to a
    object_b: List[str]                # perspectives (among favor_a) that object to b
    robust: bool                       # each side has an objection that survives measurement error
    families_a: Dict[str, int] = field(default_factory=dict)
    families_b: Dict[str, int] = field(default_factory=dict)
    n_active: int = 0

    def involves(self, oid: str) -> bool:
        return oid in (self.a, self.b)

    def to_dict(self) -> Dict[str, object]:
        return {"a": self.a, "b": self.b, "favor_a": self.favor_a, "favor_b": self.favor_b,
                "object_a": self.object_a, "object_b": self.object_b, "robust": self.robust,
                "families_a": self.families_a, "families_b": self.families_b}


def cross_option_splits(readings: Dict[str, EnsembleReading], th: Thresholds) -> List[OptionSplit]:
    """Find pairs of options on which the perspectives split by DIRECTION.

    A pair (a, b) is split when:
      * at least `divergence_share` of the perspectives engaged by both options materially prefer a,
        and at least that share materially prefer b (difference >= PREFERENCE_MARGIN); and
      * each camp includes at least SPLIT_MIN_OBJECTORS perspectives that OBJECT to the other door.
    The split is robust when each camp has at least one objection that measurement error
    could not turn into support.
    """
    ids = list(readings)
    out: List[OptionSplit] = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            va = {v.key: v for v in readings[a].voices}
            vb = {v.key: v for v in readings[b].voices}
            active = [k for k in va if k in vb and va[k].stance != Stance.ABSTAINS
                      and vb[k].stance != Stance.ABSTAINS]
            n = len(active)
            if n < th.min_voices:
                continue
            fa = [k for k in active if va[k].verdict - vb[k].verdict >= PREFERENCE_MARGIN]
            fb = [k for k in active if vb[k].verdict - va[k].verdict >= PREFERENCE_MARGIN]
            oa = [k for k in fb if va[k].stance == Stance.OBJECTS]
            ob = [k for k in fa if vb[k].stance == Stance.OBJECTS]
            if (len(fa) >= th.divergence_share * n and len(fb) >= th.divergence_share * n
                    and len(oa) >= SPLIT_MIN_OBJECTORS and len(ob) >= SPLIT_MIN_OBJECTORS):
                fam = lambda keys: {f: sum(1 for k in keys if va[k].family == f)  # noqa: E731
                                    for f in sorted({va[k].family for k in keys})}
                out.append(OptionSplit(a, b, fa, fb, oa, ob,
                                       robust=any(va[k].robust for k in oa) and any(vb[k].robust for k in ob),
                                       families_a=fam(fa), families_b=fam(fb), n_active=n))
    return out


def unobjected(readings: Dict[str, EnsembleReading]) -> List[str]:
    """Options no perspective objects to. Beside a split, these are resting places, not resolutions."""
    return [oid for oid, r in readings.items() if r.n_voices and not r.by(Stance.OBJECTS)]
