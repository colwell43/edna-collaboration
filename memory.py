"""
Moral memory and the audit trail (Minds That Matter, Chapters 5, 10, 11, 15).

MoralLedger — append-only, hash-chained record of every deliberation, human
    decision, lock, release, feedback, review flag, drift alert and revision. Chapter Five: ethical AI
    "should make the pressure behind the conclusion visible enough to challenge."
    If anyone edits history, verify() says where.

MoralMemory — "a moral memory, not just a data bank." Two kinds of learning:
    * calibration — when outcomes contradict the instrument's readings on an axis,
      the margin on that axis widens, so the system grows MORE humble exactly where
      it has been wrong (Chapter 8: "Flags its own overconfidence").
    * precedent — past cases with their outcomes resurface when a similar decision
      comes up (Chapter 10: "Now the AI has moral memory, not just spam detection").
    It never rewrites perspective weights. Chapter 9: "It did not quietly rewrite its own
    criteria. It widened its uncertainty ..., surfaced similar past cases, and flagged the
    pattern for human review." Changing what counts is a governed revision by people
    (foundation.py), not something a feedback loop does quietly (Invariants I9, I11).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from .axes import ZoneKind, get_axis
from .model import OutcomeFeedback


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MoralLedger:
    GENESIS = "0" * 64

    def __init__(self, path: Optional[str] = None, clock: Callable[[], str] = _now):
        self.path = path
        self.clock = clock
        self.entries: List[Dict[str, Any]] = []
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.entries = [json.loads(line) for line in f if line.strip()]

    @staticmethod
    def _hash(e: Dict[str, Any]) -> str:
        body = {k: e[k] for k in ("seq", "ts", "kind", "payload", "prev")}
        return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

    def append(self, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        prev = self.entries[-1]["hash"] if self.entries else self.GENESIS
        e = {"seq": len(self.entries), "ts": self.clock(), "kind": kind,
             "payload": json.loads(json.dumps(payload, default=str)), "prev": prev}
        e["hash"] = self._hash(e)
        self.entries.append(e)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        return e

    def verify(self) -> Tuple[bool, Optional[int]]:
        prev = self.GENESIS
        for i, e in enumerate(self.entries):
            if e.get("seq") != i or e.get("prev") != prev or self._hash(e) != e.get("hash"):
                return False, i
            prev = e["hash"]
        return True, None

    def of_kind(self, kind: str) -> List[Dict[str, Any]]:
        return [e for e in self.entries if e["kind"] == kind]


@dataclass
class Case:
    decision_id: str
    question: str
    tags: List[str]
    option_id: str
    option_label: str
    predicted: Dict[str, float]
    observed: Dict[str, float] = field(default_factory=dict)
    notes: str = ""
    lessons: List[str] = field(default_factory=list)


class MoralMemory:
    def __init__(self, learning_rate: float = 0.5, max_bonus: float = 0.4):
        self.learning_rate = learning_rate
        self.max_bonus = max_bonus
        self.calibration: Dict[str, float] = {}   # axis -> learned extra margin
        self.misses: Dict[str, int] = {}          # axis -> times an outcome landed in a different zone
        self.cases: List[Case] = []

    # ---- calibration ----------------------------------------------------
    def margin_bonus(self, axis: str) -> float:
        return self.calibration.get(axis, 0.0)

    def learn(self, fb: OutcomeFeedback, case: Case) -> List[str]:
        lessons: List[str] = []
        for k, obs in fb.observed.items():
            axis = get_axis(k)
            zo = axis.zone_of(obs)
            pred = case.predicted.get(k)
            if pred is not None:
                err = abs(obs - pred)
                old = self.calibration.get(k, 0.0)
                # Error beyond what the base margin already covers widens future margins.
                target = min(self.max_bonus, max(0.0, err - 0.2))
                new = old + self.learning_rate * (target - old)
                self.calibration[k] = round(new, 3)
                zp = axis.zone_of(pred)
                if zp.kind != zo.kind:
                    self.misses[k] = self.misses.get(k, 0) + 1
                    lessons.append(
                        f"On {axis.short} the reading predicted {zp.kind.value}"
                        f"{' (' + zp.label + ')' if zp.label else ''} but the outcome was {zo.kind.value}"
                        f"{' (' + zo.label + ')' if zo.label else ''}. Margin on this axis is now "
                        f"+{self.calibration[k]:.2f}.")
            if zo.kind == ZoneKind.DANGER:
                lessons.append(f"Outcome reached {zo.label} on {axis.short} — remember this case.")
        case.observed = dict(fb.observed)
        case.notes = fb.notes
        case.lessons = lessons
        return lessons

    # ---- precedent ------------------------------------------------------
    def add_case(self, case: Case) -> None:
        self.cases.append(case)

    def case(self, decision_id: str) -> Optional[Case]:
        for c in self.cases:
            if c.decision_id == decision_id:
                return c
        return None

    @staticmethod
    def _cos(a: Dict[str, float], b: Dict[str, float]) -> float:
        keys = set(a) & set(b)
        if not keys:
            return 0.0
        dot = sum(a[k] * b[k] for k in keys)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    def precedents(self, tags: List[str], vector: Dict[str, float], exclude: str = "",
                   k: int = 2, min_sim: float = 0.5) -> List[Tuple[Case, float]]:
        out = []
        for c in self.cases:
            if c.decision_id == exclude or not c.observed:
                continue
            jt = (len(set(tags) & set(c.tags)) / len(set(tags) | set(c.tags))) if (tags or c.tags) else 0.0
            sim = 0.5 * jt + 0.5 * max(0.0, self._cos(vector, c.predicted))
            if sim >= min_sim:
                out.append((c, round(sim, 2)))
        return sorted(out, key=lambda t: -t[1])[:k]

    def to_dict(self) -> Dict[str, Any]:
        return {"calibration": dict(self.calibration), "misses": dict(self.misses),
                "cases": [asdict(c) for c in self.cases]}
