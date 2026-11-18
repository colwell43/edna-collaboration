"""
Pillar Two — a set of seventeen moral perspectives (Minds That Matter, Chapter 5).

Six philosophical frameworks and eleven cultural-religious traditions. "In plain
English, the seventeen perspectives are not seventeen independent artificial
philosophers. They are different ways of looking at the same underlying ethical
situation." (The Two-Pillar paper's term: differentially weighted proxies over a
shared feature vector.) eDNA never says "the Buddhist answer is ...". It asks: what
happens when this moral perspective is given a voice in the analysis?

This module is where WEIGHTING lives — "how much fear should count against bonding."
Chapter 5: "That is weighting, and weighting is a value judgment. eDNA measures in the
open and leaves the weights where people can see them, argue with them, and change
them." So the weights are printed in every full report, exported with `roster
--export`, fingerprinted into the ledger, and changed only through foundation.py.

Each proxy has:
  * salience weights over the shared features (0 = not a focal concern, 3 = central)
  * optional tilts on balance axes — where this perspective locates the healthy point
    (e.g., Ubuntu locates it closer to Bonding, Existentialism closer to Freedom)
  * a focal question — the voice it adds to the conversation

DISCLOSURE (Chapter 5, "The Dangerous Myth of Cultural Neutrality"): the roster,
the weights, the tilts, the aggregation rule and the deferral thresholds are all
CURATED. They are not derived from first principles and they do not make the
system culturally neutral. They are put in the open so they can be argued with,
tested, revised and replaced — by people, through the foundation (open, human-governed
revision), or at deployment with Roster.from_json().
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .axes import AXES, FEATURE_KEYS, get_axis

PHILOSOPHICAL = "philosophical"
CULTURAL_RELIGIOUS = "cultural-religious"

# Compact codes used only to keep the default table readable.
_C = {
    "GE": "good_evil", "PW": "power", "AI": "accuracy_intuition",
    "TF": "trust_fear", "HS": "honor_shame", "FB": "freedom_bonding",
    "TS": "thriving_surviving", "MM": "meaningful_meaningless", "ID": "identity",
    "RD": "relational_duty", "ST": "stewardship", "LJ": "lawful_justice",
}


@dataclass(frozen=True)
class Perspective:
    key: str
    name: str
    family: str
    focal_question: str
    weights: Dict[str, float]
    tilt: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for k, w in self.weights.items():
            get_axis(k)
            if w < 0:
                raise ValueError(f"{self.key}: weights are saliences and must be >= 0")
        for k, t in self.tilt.items():
            if not get_axis(k).tiltable:
                raise ValueError(f"{self.key}: axis '{k}' is not a balance axis; it cannot be tilted")
            if abs(t) > 0.5:
                raise ValueError(f"{self.key}: tilt on '{k}' must be within ±0.5")
        if self.family not in (PHILOSOPHICAL, CULTURAL_RELIGIOUS):
            raise ValueError(f"{self.key}: unknown family '{self.family}'")

    def w(self, feature: str) -> float:
        return float(self.weights.get(feature, 0.0))


def _p(key, name, family, q, weights: str, tilt: Optional[Dict[str, float]] = None) -> Perspective:
    ws = {}
    for tok in weights.split():
        code, val = tok[:2], tok[2:]
        ws[_C[code]] = float(val)
    tl = {_C[k]: v for k, v in (tilt or {}).items()}
    return Perspective(key, name, family, q, ws, tl)


# Tilt sign: + moves this perspective's healthy point toward FREEDOM / ACCURACY,
#            - moves it toward BONDING / INTUITION.
DEFAULT_PERSPECTIVES: List[Perspective] = [
    # ---- Six philosophical frameworks ------------------------------------
    _p("consequentialism", "Consequentialism", PHILOSOPHICAL,
       "What outcomes follow, for everyone affected?",
       "GE3 PW1 AI2 TF2 HS1 FB1 TS3 MM1 ID1 ST1"),
    _p("deontology", "Deontology", PHILOSOPHICAL,
       "Are persons respected as ends, never merely as means? Are duties kept?",
       "GE3 PW2 AI1 TF2 HS3 FB2 ID1 RD1 LJ2", {"FB": 0.2}),
    _p("virtue", "Virtue ethics", PHILOSOPHICAL,
       "What character does this choice express — and cultivate?",
       "GE2 PW1 AI2 TF1 HS2 FB1 TS2 MM2 ID3"),
    _p("care", "Care ethics", PHILOSOPHICAL,
       "What happens to relationships, and to those who depend on us?",
       "GE1 PW2 AI1 TF3 HS2 FB3 TS1 MM1 ID1 RD2", {"FB": -0.2}),
    _p("pragmatism", "Pragmatism", PHILOSOPHICAL,
       "What actually works here, including the unintended consequences?",
       "GE1 PW1 AI3 TF2 HS1 FB1 TS2 MM1 ID1 ST1", {"AI": 0.1}),
    _p("existentialism", "Existentialism", PHILOSOPHICAL,
       "Does it honor agency, authenticity and personal responsibility?",
       "GE1 PW2 AI1 TF1 HS1 FB3 TS1 MM3 ID3", {"FB": 0.35}),
    # ---- Eleven cultural-religious traditions ----------------------------
    _p("christian_agape", "Christian agape", CULTURAL_RELIGIOUS,
       "Does it express self-giving love, especially toward the least?",
       "GE3 PW3 TF2 HS3 FB2 TS1 MM2 ID1 ST1", {"FB": -0.1}),
    _p("confucian_ren", "Confucian ren", CULTURAL_RELIGIOUS,
       "Does it honor relationships and the duties of each role?",
       "GE2 PW1 AI1 TF2 HS3 FB2 TS1 MM1 ID1 RD3", {"FB": -0.35}),
    _p("buddhist_karuna", "Buddhist karuṇā", CULTURAL_RELIGIOUS,
       "Does it relieve suffering — and avoid causing it?",
       "GE3 PW1 AI1 TF3 HS1 FB1 TS3 MM1 ID1 ST1"),
    _p("islamic_adl", "Islamic adl", CULTURAL_RELIGIOUS,
       "Is it just — does each receive what is due within a rightful order?",
       "GE3 PW3 AI1 TF1 HS2 FB1 TS1 MM1 RD2 ST1 LJ3", {"FB": -0.1}),
    _p("ubuntu", "Ubuntu", CULTURAL_RELIGIOUS,
       "Does it strengthen our shared humanity — 'I am because we are'?",
       "GE1 PW2 TF2 HS3 FB3 TS2 MM1 ID2 RD2", {"FB": -0.4}),
    _p("indigenous_stewardship", "Indigenous stewardship", CULTURAL_RELIGIOUS,
       "Does it keep faith with land, community and the generations to come?",
       "GE1 PW1 AI1 TF1 HS1 FB2 TS2 MM2 ID2 RD2 ST3", {"FB": -0.2, "AI": -0.2}),
    _p("hindu_dharma", "Hindu dharma", CULTURAL_RELIGIOUS,
       "Does each party act rightly according to their duty and station?",
       "GE2 PW1 AI1 TF1 HS2 FB1 TS1 MM2 ID2 RD3 ST1 LJ1", {"FB": -0.2}),
    _p("taoist_wu_wei", "Taoist wu wei", CULTURAL_RELIGIOUS,
       "Does it move with the grain of things, without forcing?",
       "GE1 PW3 AI2 TF1 FB2 TS2 MM1 ID1 ST2", {"AI": -0.2, "FB": 0.1}),
    _p("sikh_seva", "Sikh seva", CULTURAL_RELIGIOUS,
       "Does it serve others selflessly and uphold their equal dignity?",
       "GE2 PW3 TF1 HS3 FB1 TS2 MM2 ID1 RD1", {"FB": -0.1}),
    _p("jewish_talmudic", "Jewish Talmudic tradition", CULTURAL_RELIGIOUS,
       "What do law, argument and the repair of the world (tikkun olam) require?",
       "GE3 PW2 AI2 TF1 HS3 FB1 TS1 MM2 ID1 RD2 ST1 LJ3"),
    _p("secular_humanism", "Secular humanism", CULTURAL_RELIGIOUS,
       "Does it advance human welfare and freedom through reason and evidence?",
       "GE2 PW2 AI3 TF1 HS2 FB2 TS3 MM1 ID2", {"FB": 0.25, "AI": 0.1}),
]


@dataclass
class Roster:
    perspectives: List[Perspective]
    version: str = "collab-1.1-default"
    curated_by: str = "eDNA Collaboration defaults (heuristic; replace with your governed roster)"
    disclosure: str = (
        "Curated, not derived. The roster, how much each perspective counts (salience weights and "
        "balance-axis tilts), how their views are combined (weighted zone utilities; a perspective "
        "objects outright when one of its central, salience-3 concerns is in danger) and the point "
        "at which the AI defers are contestable choices, made in the open and revised by people. "
        "Perspectives are heuristic proxies over a shared feature vector, not independent "
        "reasoners and not spokespeople for living traditions. If the shared features are "
        "mis-measured, all seventeen inherit the same error."
    )

    def __post_init__(self) -> None:
        keys = [p.key for p in self.perspectives]
        if len(keys) != len(set(keys)):
            raise ValueError("perspective keys must be unique")
        if len(self.perspectives) < 3:
            raise ValueError("an ensemble needs at least three perspectives")

    def __iter__(self):
        return iter(self.perspectives)

    def __len__(self) -> int:
        return len(self.perspectives)

    def get(self, key: str) -> Perspective:
        for p in self.perspectives:
            if p.key == key:
                return p
        raise KeyError(key)

    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "curated_by": self.curated_by,
            "disclosure": self.disclosure,
            "features": list(FEATURE_KEYS),
            "perspectives": [
                {"key": p.key, "name": p.name, "family": p.family,
                 "focal_question": p.focal_question,
                 "weights": dict(p.weights), "tilt": dict(p.tilt)}
                for p in self.perspectives
            ],
        }

    def fingerprint(self) -> str:
        """Stable hash recorded with every deliberation, so the audit trail shows which roster judged it."""
        blob = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False).encode()
        return hashlib.sha256(blob).hexdigest()[:16]

    def to_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: Dict) -> "Roster":
        ps = [Perspective(p["key"], p["name"], p["family"], p["focal_question"],
                          {k: float(v) for k, v in p["weights"].items()},
                          {k: float(v) for k, v in p.get("tilt", {}).items()})
              for p in d["perspectives"]]
        kw = {k: d[k] for k in ("version", "curated_by", "disclosure") if k in d}
        return cls(ps, **kw)

    @classmethod
    def from_json(cls, path: str) -> "Roster":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    @classmethod
    def default(cls) -> "Roster":
        return cls(list(DEFAULT_PERSPECTIVES))


def _self_check() -> None:
    r = Roster.default()
    fams = [p.family for p in r]
    assert len(r) == 17 and fams.count(PHILOSOPHICAL) == 6 and fams.count(CULTURAL_RELIGIOUS) == 11
    for k in AXES:
        assert any(p.w(k) > 0 for p in r), f"no perspective attends to {k}"


_self_check()
