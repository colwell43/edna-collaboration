"""
Core data types: what a decision looks like going in, and what humans add coming back.

Two evaluation paths (Path A / Path B):
  * Mode.ANSWER — the option is something the system will SAY (text).
  * Mode.ACT    — the option is something the system will DO (an action with effects).
Chapter Five: the check matters most "for an AI agent that is about to act rather
than merely answer." The engine applies stricter gates to ACT, and strictest to
irreversible ACT.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .axes import get_axis


class Mode(str, Enum):
    ANSWER = "answer"  # Path A: text
    ACT = "act"        # Path B: action / effect


class Stakes(str, Enum):
    ORDINARY = "ordinary"
    CONSEQUENTIAL = "consequential"
    CRITICAL = "critical"


def _check_unit(name: str, v: float, lo: float, hi: float) -> float:
    v = float(v)
    if not (lo <= v <= hi):
        raise ValueError(f"{name}={v} outside [{lo}, {hi}]")
    return v


@dataclass
class AxisAssessment:
    """One MEASUREMENT: where an option sits on one axis (Chapter 5).

    "eDNA measures a decision ... it means something narrow. The system can show where a
    decision sits on each axis. That is measurement. What it must not do is decide, on its
    own and out of sight, how much fear should count against bonding. That is weighting."
    A position is not a score: it says where, never how much it counts.
    """
    position: float           # -1 .. +1 along the axis (+1 = toward the first-named pole)
    relevance: float = 1.0    # 0 .. 1 — how much this axis is engaged by the option
    confidence: float = 0.7   # 0 .. 1 — the instrument's confidence in the reading
    rationale: str = ""

    def __post_init__(self) -> None:
        self.position = _check_unit("position", self.position, -1.0, 1.0)
        self.relevance = _check_unit("relevance", self.relevance, 0.0, 1.0)
        self.confidence = _check_unit("confidence", self.confidence, 0.0, 1.0)

    @property
    def score(self) -> float:  # v1.0 name, kept so older code keeps working
        return self.position

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AxisAssessment":
        """Accepts v1.1 'position' or the v1.0 key 'score'."""
        pos = d["position"] if "position" in d else d["score"]
        return cls(pos, d.get("relevance", 1.0), d.get("confidence", 0.7), d.get("rationale", ""))


@dataclass
class Option:
    id: str
    label: str
    description: str = ""
    assessments: Dict[str, AxisAssessment] = field(default_factory=dict)
    reversible: bool = True
    benefit: str = ""            # Chapter 7: "What is the short-term benefit?"
    origin: str = "proposed"     # proposed | third_door | human

    def __post_init__(self) -> None:
        for k in self.assessments:
            get_axis(k)  # raises on unknown axis

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Option":
        a = {k: (v if isinstance(v, AxisAssessment) else AxisAssessment.from_dict(v))
             for k, v in (d.get("assessments") or {}).items()}
        return cls(id=d["id"], label=d.get("label", d["id"]), description=d.get("description", ""),
                   assessments=a, reversible=d.get("reversible", True),
                   benefit=d.get("benefit", ""), origin=d.get("origin", "proposed"))


@dataclass
class Stakeholder:
    name: str
    vulnerable: bool = False
    note: str = ""


@dataclass
class DeclaredValue:
    """A value the organization has publicly declared (Chapter 12, brake 2: the Values Check).

    floors: axis -> minimum acceptable position. A relevant reading below the floor is a
    conflict: "This request conflicts with the values your organization has publicly
    declared ... This direction may misalign with your <name> goals. Proceed anyway?"
    """
    name: str
    statement: str
    floors: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for k, v in self.floors.items():
            get_axis(k)
            _check_unit(f"floor[{k}]", v, -1.0, 1.0)


@dataclass
class Decision:
    question: str
    options: List[Option]
    mode: Mode = Mode.ACT
    context: str = ""
    stakeholders: List[Stakeholder] = field(default_factory=list)
    declared_values: List[DeclaredValue] = field(default_factory=list)
    proposed_option: Optional[str] = None   # what the agent/user intends to do, if anything
    stakes: Stakes = Stakes.CONSEQUENTIAL
    tags: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def __post_init__(self) -> None:
        self.mode = Mode(self.mode)
        self.stakes = Stakes(self.stakes)
        ids = [o.id for o in self.options]
        if len(ids) != len(set(ids)):
            raise ValueError("option ids must be unique")
        if not self.options:
            raise ValueError("a decision needs at least one option")
        if self.proposed_option and self.proposed_option not in ids:
            raise ValueError(f"proposed_option '{self.proposed_option}' is not an option id")

    @property
    def has_vulnerable(self) -> bool:
        return any(s.vulnerable for s in self.stakeholders)

    def option(self, oid: str) -> Option:
        for o in self.options:
            if o.id == oid:
                return o
        raise KeyError(oid)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Decision":
        kw = dict(
            question=d["question"],
            options=[Option.from_dict(o) for o in d["options"]],
            mode=d.get("mode", "act"),
            context=d.get("context", ""),
            stakeholders=[Stakeholder(**s) for s in d.get("stakeholders", [])],
            declared_values=[DeclaredValue(**v) for v in d.get("declared_values", [])],
            proposed_option=d.get("proposed_option"),
            stakes=d.get("stakes", "consequential"),
            tags=list(d.get("tags", [])),
        )
        if d.get("id"):
            kw["id"] = d["id"]
        return cls(**kw)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        d["stakes"] = self.stakes.value
        return d


# ---- What humans bring back (Chapter 13: co-design means co-responsibility) ----

ROLES = ("Engineer", "Executive", "Policymaker", "Educator", "Citizen", "Reviewer", "Operator")


@dataclass
class HumanDecision:
    """An accountable human call. The machine never records a choice without a name on it."""
    chosen_option: Optional[str]          # None = none of the options / do nothing
    decided_by: str
    role: str
    rationale: str
    acknowledged: List[str] = field(default_factory=list)  # codes from Deliberation.required_acknowledgements
    release_lock: bool = False

    def __post_init__(self) -> None:
        if not self.decided_by.strip():
            raise ValueError("decided_by must name an accountable person")
        if not self.rationale.strip():
            raise ValueError("a human decision needs a rationale (it goes in the audit trail)")


@dataclass
class OutcomeFeedback:
    """What actually happened after a decision (Chapter 10: feedback loop from impact).

    The engine registers the outcome on the axes AND across the seventeen perspectives,
    widens its own uncertainty where it was wrong, and flags patterns for the people
    accountable. It never rewrites its own values (Chapter 9)."""
    decision_id: str
    observed: Dict[str, float]            # axis -> observed position of the real outcome
    notes: str = ""
    reporter: str = ""

    def __post_init__(self) -> None:
        for k, v in self.observed.items():
            get_axis(k)
            _check_unit(f"observed[{k}]", v, -1.0, 1.0)
