"""
Pillar One — what humans learn to notice (Minds That Matter, Chapters 3, 4 and 8).

Nine axes, grouped into three lenses: Head (logic), Heart (emotion), Horizon
(imagination). "The three lenses ... are simply how we group them." (Ch. 3)
Each axis is a *continuum*, not a pass/fail flag. Chapter Eight's table puts
virtues in a healthy band and vices at the extremes — sometimes at BOTH ends
(Power: Domination or Helplessness; Trust: Manipulation or Cowardice;
Good: Harm or Self-righteousness). So the geometry here is a zone table, not a
monotone "higher is better" ladder.

Three further features (relational duty, stewardship, lawful justice) are
registered as Pillar Two supplementary features. They are NOT developmental
axes: Chapter Five says plainly that several traditions contribute moral
content the first pillar does not independently establish. They are kept
separate and flagged so nobody mistakes them for developmental claims.

AXIS IS NOT A METRIC. This module says *what* is being looked at and *where* a
measurement falls ("this choice leans toward fear, that one toward bonding. That is
measurement." — Ch. 5). It does not say how much any axis counts: that is weighting,
a value judgment, kept visible in perspectives.py and changed only by people.

EVIDENCE IS UNEVEN, AND WE SAY SO (Ch. 4). "Some appear early ... Others, such as
honor and shame, or meaning and identity, arrive later and are shaped far more by
culture." Each axis carries the grounding the book states — and says so where the
book is silent, rather than letting code invent evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Dict, List, Tuple


class Strand(str, Enum):
    """The three lenses (the book: "Each strand, or lens, holds three axes")."""
    HEAD = "Head"          # Logic — the reasoning mind
    HEART = "Heart"        # Emotion — the relational heart
    HORIZON = "Horizon"    # Imagination — the future-seeker
    PILLAR_TWO = "Pillar Two"  # supplementary, culturally articulated features


Lens = Strand  # the manuscript's word


STRAND_FACULTY = {  # lens -> faculty
    Strand.HEAD: "Logic",
    Strand.HEART: "Emotion",
    Strand.HORIZON: "Imagination",
    Strand.PILLAR_TWO: "Pillar Two",
}


class ZoneKind(str, Enum):
    HEALTHY = "healthy"    # the virtue band
    NEUTRAL = "neutral"    # no strong lean either way
    DRIFT = "drift"        # the grey zone: sliding toward a vice
    DANGER = "danger"      # a vice extreme (Chapter 12, layer 1)


# The ONLY numbers that turn a reading into a utility. Disclosed, curated, arguable.
# The ZONE decides the band; position inside the zone ("how far it drifts", Ch. 8)
# moves the value within the band. Bands never overlap, so the zones stay legible:
# healthy is always >= +0.6, drift always in [-0.6, -0.2], danger always <= -0.7.
ZONE_BANDS: Dict[ZoneKind, Tuple[float, float]] = {
    ZoneKind.HEALTHY: (0.6, 1.0),     # (at the zone edge, at the ideal point)
    ZoneKind.NEUTRAL: (0.0, 0.0),
    ZoneKind.DRIFT: (-0.2, -0.6),     # (next to healthy/neutral, next to danger)
    ZoneKind.DANGER: (-0.7, -1.0),    # (next to drift, at the pole)
}


@dataclass(frozen=True)
class Zone:
    lo: float
    hi: float
    kind: ZoneKind
    label: str  # virtue name (healthy) or vice name (drift/danger); "" for neutral

    def contains(self, s: float, last: bool) -> bool:
        return (self.lo <= s < self.hi) or (last and s == self.hi)


def _zones(spec: List[Tuple[float, ZoneKind, str]]) -> Tuple[Zone, ...]:
    """Build contiguous zones from [(upper_bound, kind, label), ...] covering [-1, 1]."""
    out, lo = [], -1.0
    for hi, kind, label in spec:
        if hi <= lo:
            raise ValueError("zone bounds must increase")
        out.append(Zone(lo, hi, kind, label))
        lo = hi
    if abs(lo - 1.0) > 1e-9:
        raise ValueError("zones must end at +1.0")
    return tuple(out)


@dataclass(frozen=True)
class Axis:
    key: str
    pos_pole: str
    neg_pole: str
    strand: Strand
    question: str
    zones: Tuple[Zone, ...]
    virtue_phrase: str          # used when justifying a choice in moral terms
    repair_neg: str             # how a third door repairs drift toward the negative pole
    repair_pos: str = ""        # ... toward an overshoot vice at the positive pole
    tiltable: bool = False      # balance axes: perspectives may disagree on the ideal point
    pillar_one: bool = True     # False = Pillar Two supplementary feature
    # Evidential grounding (Ch. 4: "The evidence is stronger for some axes than for
    # others, and we say so"). Set below from the book's own statements only.
    grounding: str = "not stated in the book — set it from the Two-Pillar paper"
    grounding_tier: str = "unstated"   # early | later | unstated | pillar-two

    display: str = ""           # optional short display name
    long_label: str = ""        # optional display of the full axis name

    @property
    def label(self) -> str:
        return self.long_label or f"{self.pos_pole} ↔ {self.neg_pole}"

    @property
    def short(self) -> str:
        return self.display or f"{self.pos_pole}–{self.neg_pole}"

    def zone_index(self, score: float) -> int:
        s = max(-1.0, min(1.0, float(score)))
        for i, z in enumerate(self.zones):
            if z.contains(s, last=(i == len(self.zones) - 1)):
                return i
        return len(self.zones) - 1

    def zone_of(self, score: float) -> Zone:
        return self.zones[self.zone_index(score)]

    @property
    def healthy_index(self) -> int:
        return next(i for i, z in enumerate(self.zones) if z.kind == ZoneKind.HEALTHY)

    @property
    def ideal(self) -> float:
        """Best point of the healthy band: the pole if the band reaches it, else the band's middle."""
        z = self.zones[self.healthy_index]
        if z.hi >= 1.0:
            return 1.0
        if z.lo <= -1.0:
            return -1.0
        return (z.lo + z.hi) / 2

    def utility(self, score: float) -> float:
        s = max(-1.0, min(1.0, float(score)))
        i = self.zone_index(s)
        z = self.zones[i]
        near, far = ZONE_BANDS[z.kind]
        if z.kind == ZoneKind.NEUTRAL:
            return 0.0
        if z.kind == ZoneKind.HEALTHY:
            reach = max(self.ideal - z.lo, z.hi - self.ideal) or 1.0
            return far - (far - near) * abs(s - self.ideal) / reach
        width = (z.hi - z.lo) or 1.0
        # t = 0 on the edge closer to the healthy band, 1 on the far edge
        t = (z.hi - s) / width if i < self.healthy_index else (s - z.lo) / width
        return near + (far - near) * max(0.0, min(1.0, t))

    def utility_range(self, lo: float, hi: float) -> Tuple[float, float]:
        """Worst and best utility anywhere in [lo, hi] — used for measurement uncertainty."""
        lo, hi = max(-1.0, lo), min(1.0, hi)
        pts = [lo, hi]
        for z in self.zones:
            for b in (z.lo, z.hi):
                if lo < b < hi:
                    pts += [b - 1e-9, b]
        if lo < self.ideal < hi:
            pts.append(self.ideal)
        us = [self.utility(p) for p in pts]
        return min(us), max(us)

    def exposure(self, position: float, margin: float, kinds) -> Tuple[float, bool]:
        """How much of the measurement range [position - margin, position + margin] lies in zones of
        the given kinds, and whether the nominal position itself does.

        v1.2: protections read the whole range, not one exact value, so a reading sitting right on
        a boundary neither trips nor slips past a guard by a hair.
        """
        lo, hi = max(-1.0, position - margin), min(1.0, position + margin)
        inside = self.zone_of(position).kind in kinds
        if hi - lo <= 1e-12:
            return (1.0 if inside else 0.0), inside
        covered = sum(max(0.0, min(hi, z.hi) - max(lo, z.lo)) for z in self.zones if z.kind in kinds)
        return min(1.0, covered / (hi - lo)), inside

    def nearest_zone(self, position: float, kinds) -> "Zone":
        """The zone of the given kinds closest to a position (the zone itself if the position is inside)."""
        cands = [z for z in self.zones if z.kind in kinds]
        if not cands:
            return self.zone_of(position)

        def dist(z: "Zone") -> float:
            return 0.0 if z.lo <= position <= z.hi else min(abs(position - z.lo), abs(position - z.hi))
        return min(cands, key=dist)

    def danger_reach(self, lo: float, hi: float) -> Tuple[bool, bool]:
        """(possible, certain): does [lo, hi] touch a DANGER zone / lie entirely in one?"""
        lo, hi = max(-1.0, lo), min(1.0, hi)
        kinds = [z.kind for z in self.zones if z.lo <= hi and z.hi >= lo]
        return (ZoneKind.DANGER in kinds), all(k == ZoneKind.DANGER for k in kinds)

    def repair_for(self, score: float) -> str:
        return self.repair_pos if (score > 0 and self.repair_pos) else self.repair_neg


H, N, D, X = ZoneKind.HEALTHY, ZoneKind.NEUTRAL, ZoneKind.DRIFT, ZoneKind.DANGER

# ---------------------------------------------------------------------------
# The nine axes in three lenses (Chapter 3 table; Chapter 4 descriptions; Chapter 8 zones)
# Score convention for every axis: +1 = toward the FIRST-named pole,
# -1 = toward the SECOND-named pole. Score the CHOICE's effect on the people
# affected — never the topic being discussed.
# ---------------------------------------------------------------------------
AXES: Dict[str, Axis] = {}


def _add(a: Axis) -> None:
    AXES[a.key] = a


# ---- Head — Logic ---------------------------------------------------------
_add(Axis(
    key="good_evil", pos_pole="Good", neg_pole="Evil", strand=Strand.HEAD,
    question="Moral intent and impact. Not just 'is it legal?' but 'is it right?'",
    zones=_zones([(-0.5, X, "Harm"), (-0.15, D, "Harm"), (0.3, N, ""),
                  (0.85, H, "Integrity"), (1.0, D, "Self-righteousness")]),
    virtue_phrase="acts with integrity",
    repair_neg="remove the harmful element, or add a safeguard that prevents it",
    repair_pos="drop the moralizing; state the concern once, plainly, and help",
))
_add(Axis(
    key="power", pos_pole="Power", neg_pole="Powerless", strand=Strand.HEAD,
    question="Who benefits? Who's protected? Who's ignored? "
             "(+1 = control exercised over those affected; -1 = they are left helpless)",
    zones=_zones([(-0.55, X, "Helplessness"), (-0.2, D, "Helplessness"),
                  (0.5, H, "Empowerment"), (0.75, D, "Domination"), (1.0, X, "Domination")]),
    virtue_phrase="empowers rather than dominates",
    repair_neg="give the affected party protection or a real say",
    repair_pos="replace control with consent: a smaller, reversible step and a voice for the person affected",
))
_add(Axis(
    key="accuracy_intuition", pos_pole="Accuracy", neg_pole="Intuition", strand=Strand.HEAD,
    question="Hard data vs. gut feeling. When do we follow numbers, and when do we trust experience?",
    zones=_zones([(-0.8, X, "Unfounded hunch"), (-0.45, D, "Unfounded hunch"),
                  (0.55, H, "Calibrated judgment"), (0.85, D, "Cold literalism"),
                  (1.0, X, "Cold literalism")]),
    virtue_phrase="balances data with judgment",
    repair_neg="ground the call in evidence before acting",
    repair_pos="add context and human judgment to the data; ask what the numbers cannot see",
    tiltable=True,
))

# ---- Heart — Emotion ------------------------------------------------------
_add(Axis(
    key="trust_fear", pos_pole="Trust", neg_pole="Fear", strand=Strand.HEART,
    question="Is the system creating safety — or suspicion? "
             "(-1 extreme = fear, suspicion, cowardice; +1 extreme = engineered, unearned trust, i.e. manipulation)",
    zones=_zones([(-0.55, X, "Fear"), (-0.15, D, "Fear"), (0.2, N, ""),
                  (0.75, H, "Confidence"), (0.9, D, "Manipulation"), (1.0, X, "Manipulation")]),
    virtue_phrase="builds earned trust",
    repair_neg="earn trust honestly: frame around real value and real safeguards, not urgency or threat",
    repair_pos="stop engineering attachment; be transparent about intent",
))
_add(Axis(
    key="honor_shame", pos_pole="Honor", neg_pole="Shame", strand=Strand.HEART,
    question="Does this choice affirm dignity — or violate it?",
    zones=_zones([(-0.5, X, "Shaming"), (-0.15, D, "Shaming"), (0.2, N, ""),
                  (0.85, H, "Dignity"), (1.0, D, "Vanity / flattery")]),
    virtue_phrase="protects dignity",
    repair_neg="deliver the same truth in a way that preserves the person's dignity",
    repair_pos="replace flattery with honest, specific recognition",
))
_add(Axis(
    key="freedom_bonding", pos_pole="Freedom", neg_pole="Bonding", strand=Strand.HEART,
    question="Is it prioritizing independence or connectedness? And when is each appropriate?",
    zones=_zones([(-0.8, X, "Control / enmeshment"), (-0.5, D, "Control / enmeshment"),
                  (0.5, H, "Healthy interdependence"), (0.8, D, "Isolation"), (1.0, X, "Isolation")]),
    virtue_phrase="honors both independence and connection",
    repair_neg="restore the person's own choice within the relationship",
    repair_pos="keep people connected; bring a trusted person into the loop",
    tiltable=True,
))

# ---- Horizon — Imagination ------------------------------------------------
_add(Axis(
    key="thriving_surviving", pos_pole="Thriving", neg_pole="Surviving", strand=Strand.HORIZON,
    question="Is this choice about getting by — or growing?",
    zones=_zones([(-0.5, X, "Diminishment"), (-0.15, D, "Mere survival"), (0.2, N, ""),
                  (1.0, H, "Flourishing")]),
    virtue_phrase="supports flourishing",
    repair_neg="look for an option that builds capacity instead of merely getting by",
))
_add(Axis(
    key="meaningful_meaningless", pos_pole="Meaningful", neg_pole="Meaningless", strand=Strand.HORIZON,
    question="Does it contribute to a deeper purpose, or just add noise?",
    zones=_zones([(-0.5, X, "Hollowness"), (-0.15, D, "Noise"), (0.2, N, ""),
                  (1.0, H, "Purpose")]),
    virtue_phrase="serves a purpose people would recognize",
    repair_neg="connect the action to a purpose the affected people would recognize as theirs",
))
_add(Axis(
    key="identity", pos_pole="Desired identity", neg_pole="Undesired identity", strand=Strand.HORIZON,
    question="Is it helping people become who they want to be — or pushing them away from it?",
    zones=_zones([(-0.5, X, "Alienation"), (-0.15, D, "Alienation"), (0.2, N, ""),
                  (1.0, H, "Becoming")]),
    virtue_phrase="helps people become who they want to be",
    repair_neg="ask what the affected person wants to become, and keep that path open",
    display="Desired–Undesired Identity", long_label="Desired ↔ Undesired Identity",
))

# ---- Pillar Two supplementary features (NOT developmentally grounded) -----
_add(Axis(
    key="relational_duty", pos_pole="Duty kept", neg_pole="Duty abandoned", strand=Strand.PILLAR_TWO,
    question="Are the obligations of role and relationship (family, elders, community) honored?",
    zones=_zones([(-0.5, X, "Duty abandoned"), (-0.15, D, "Duty neglected"), (0.2, N, ""),
                  (1.0, H, "Faithfulness")]),
    virtue_phrase="keeps faith with relational duties",
    repair_neg="keep faith with the obligations of the relationship (family, role, community)",
    pillar_one=False, grounding="culturally articulated (Pillar Two)", display="Relational duty",
))
_add(Axis(
    key="stewardship", pos_pole="Stewardship", neg_pole="Depletion", strand=Strand.PILLAR_TWO,
    question="Does it care for land, community, and generations not yet born?",
    zones=_zones([(-0.5, X, "Depletion"), (-0.15, D, "Depletion"), (0.2, N, ""),
                  (1.0, H, "Stewardship")]),
    virtue_phrase="keeps faith with land, community and future generations",
    repair_neg="account for the land, the community, and those not yet born",
    pillar_one=False, grounding="culturally articulated (Pillar Two)",
))
_add(Axis(
    key="lawful_justice", pos_pole="Justice", neg_pole="Injustice", strand=Strand.PILLAR_TWO,
    question="Does each party receive what is due, within a rightful and answerable order?",
    zones=_zones([(-0.5, X, "Injustice"), (-0.15, D, "Injustice"), (0.2, N, ""),
                  (1.0, H, "Justice")]),
    virtue_phrase="gives each party what is due",
    repair_neg="give each party what is due; make the process fair and answerable",
    pillar_one=False, grounding="culturally articulated (Pillar Two)",
))

# ---- Grounding, as the book states it (Ch. 4, Ch. 5) ----------------------
_LATER = ("later", "later-emerging and shaped far more by culture (Ch. 4)")
_GROUNDING = {
    "good_evil": ("early", "early evidence cited in Ch. 4: 18-month-olds help a stranger unasked "
                           "(Warneken & Tomasello 2006). Linking that study to this axis is this program's reading."),
    "honor_shame": _LATER,
    "meaningful_meaningless": _LATER,
    "identity": _LATER,
}
for _k, _a in list(AXES.items()):
    if not _a.pillar_one:
        AXES[_k] = replace(_a, grounding_tier="pillar-two",
                           grounding="not established by Pillar One; culturally articulated (Ch. 5)")
    elif _k in _GROUNDING:
        AXES[_k] = replace(_a, grounding_tier=_GROUNDING[_k][0], grounding=_GROUNDING[_k][1])

PILLAR_ONE_KEYS: Tuple[str, ...] = tuple(k for k, a in AXES.items() if a.pillar_one)
SUPPLEMENTARY_KEYS: Tuple[str, ...] = tuple(k for k, a in AXES.items() if not a.pillar_one)
FEATURE_KEYS: Tuple[str, ...] = tuple(AXES.keys())  # the shared feature vector


def axes_by_strand(strand: Strand) -> List[Axis]:
    return [a for a in AXES.values() if a.strand == strand]


def get_axis(key: str) -> Axis:
    try:
        return AXES[key]
    except KeyError:
        raise KeyError(f"unknown axis/feature '{key}'. Known: {', '.join(FEATURE_KEYS)}") from None


LENS_FACULTY = STRAND_FACULTY

assert len(PILLAR_ONE_KEYS) == 9, "Pillar One must have exactly nine axes"
assert all(len(axes_by_strand(s)) == 3 for s in (Strand.HEAD, Strand.HEART, Strand.HORIZON))
