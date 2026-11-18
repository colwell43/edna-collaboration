"""
The foundation — open, human-governed revision (Minds That Matter, Chapters 1, 6, 9, 11, 12).

    "It's not rigid. It can be revised—openly, and by people."                    (Ch. 1)
    "A foundation of open, human-governed revision underlies today's systems."    (Ch. 6, Figure 1)
    "Any change to what the system counts as merit went through the people accountable
     for it—a deliberate, documented revision of the roster of values, not a private
     adjustment the machine made on its own."                                     (Ch. 9)
    "It Learns Virtuous Patterns—Under Human Governance"                          (Ch. 11)
    "Disclosed values, revised by people"                                         (Ch. 12)

Everything that decides how much something COUNTS — the seventeen-perspective roster
(weights, tilts), the deferral thresholds, and the protected interests of jealous
space — changes only here: a named person proposes, other named people approve (never
the proposer alone), and every step goes into the hash-chained ledger with the
fingerprint before and after. The engine refuses any other route (Invariant I11).
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List

from .axes import get_axis
from .perspectives import Roster
from .policy import Thresholds

if TYPE_CHECKING:  # pragma: no cover
    from .engine import CollaborationEngine

KINDS = ("roster", "thresholds", "protected")


class RevisionError(Exception):
    pass


@dataclass
class Approval:
    by: str
    role: str
    ts: str


@dataclass
class Revision:
    id: str
    kind: str
    summary: str
    rationale: str
    proposed_by: str
    role: str
    payload: Dict[str, Any]
    created: str
    status: str = "proposed"          # proposed | rejected | applied
    approvals: List[Approval] = field(default_factory=list)
    prior_fingerprint: str = ""
    new_fingerprint: str = ""
    note: str = ""


def _named(who: str, what: str) -> str:
    if not who or not who.strip():
        raise RevisionError(f"{what} needs a named, accountable person")
    return who.strip()


class Foundation:
    def __init__(self, engine: "CollaborationEngine", min_approvals: int = 2):
        if min_approvals < 1:
            raise RevisionError("a revision needs at least one approver besides the proposer")
        self.engine = engine
        self.min_approvals = min_approvals
        self.revisions: Dict[str, Revision] = {}

    # ---- helpers ----------------------------------------------------------
    def _validate(self, kind: str, payload: Dict[str, Any]) -> None:
        if kind not in KINDS:
            raise RevisionError(f"unknown revision kind '{kind}' (use one of {KINDS})")
        if kind == "roster":
            Roster.from_dict(payload)                       # raises on a malformed roster
        elif kind == "thresholds":
            Thresholds(**{**asdict(self.engine.th), **payload})   # raises outside the bounds
        else:
            if not payload:
                raise RevisionError("jealous space cannot be emptied: at least one protected interest")
            for k in payload:
                get_axis(k)

    def _fingerprint(self, kind: str) -> str:
        if kind == "roster":
            return self.engine.roster.fingerprint()
        if kind == "thresholds":
            return self.engine.th.fingerprint()
        return ",".join(sorted(self.engine.jealous.protected))

    def get(self, rev_id: str) -> Revision:
        try:
            return self.revisions[rev_id]
        except KeyError:
            raise RevisionError(f"no revision '{rev_id}'") from None

    # ---- the governed path -------------------------------------------------
    def propose(self, kind: str, payload: Dict[str, Any], summary: str, rationale: str,
                proposed_by: str, role: str) -> Revision:
        _named(proposed_by, "a proposal")
        if not rationale.strip():
            raise RevisionError("a revision needs a rationale people can argue with")
        self._validate(kind, payload)
        rev = Revision(uuid.uuid4().hex[:8], kind, summary, rationale, proposed_by.strip(), role,
                       payload, self.engine.clock(), prior_fingerprint=self._fingerprint(kind))
        self.revisions[rev.id] = rev
        self.engine.ledger.append("revision_proposed", {
            "revision": rev.id, "kind": kind, "summary": summary, "rationale": rationale,
            "proposed_by": rev.proposed_by, "role": role, "prior_fingerprint": rev.prior_fingerprint})
        return rev

    def approve(self, rev_id: str, by: str, role: str) -> Revision:
        rev = self.get(rev_id)
        who = _named(by, "an approval")
        if rev.status != "proposed":
            raise RevisionError(f"revision {rev_id} is {rev.status}")
        if who == rev.proposed_by:
            raise RevisionError("the proposer cannot approve their own revision")
        if any(a.by == who for a in rev.approvals):
            raise RevisionError(f"{who} has already approved revision {rev_id}")
        rev.approvals.append(Approval(who, role, self.engine.clock()))
        self.engine.ledger.append("revision_approved", {"revision": rev.id, "by": who, "role": role})
        return rev

    def reject(self, rev_id: str, by: str, role: str, rationale: str) -> Revision:
        rev = self.get(rev_id)
        who = _named(by, "a rejection")
        rev.status, rev.note = "rejected", rationale
        self.engine.ledger.append("revision_rejected", {"revision": rev.id, "by": who, "role": role,
                                                        "rationale": rationale})
        return rev

    def apply(self, rev_id: str, applied_by: str, role: str) -> Revision:
        rev = self.get(rev_id)
        who = _named(applied_by, "applying a revision")
        if rev.status != "proposed":
            raise RevisionError(f"revision {rev_id} is {rev.status}")
        if len(rev.approvals) < self.min_approvals:
            raise RevisionError(f"revision {rev_id} has {len(rev.approvals)} approval(s); "
                                f"{self.min_approvals} required")
        if rev.prior_fingerprint != self._fingerprint(rev.kind):
            raise RevisionError("the live configuration changed since this revision was proposed; re-propose it")
        eng = self.engine
        if rev.kind == "roster":
            new = Roster.from_dict(rev.payload)
            if new.version == eng.roster.version:
                new.version = f"{eng.roster.version}+rev.{rev.id}"
            eng._roster = new
        elif rev.kind == "thresholds":
            eng._set_thresholds(Thresholds(**{**asdict(eng.th), **rev.payload}))
        else:
            eng.jealous.protected = dict(rev.payload)
        rev.status, rev.new_fingerprint = "applied", self._fingerprint(rev.kind)
        eng.ledger.append("revision_applied", {
            "revision": rev.id, "kind": rev.kind, "applied_by": who, "role": role,
            "approvals": [a.by for a in rev.approvals], "prior_fingerprint": rev.prior_fingerprint,
            "new_fingerprint": rev.new_fingerprint})
        return rev

    def history(self) -> List[Revision]:
        return list(self.revisions.values())
