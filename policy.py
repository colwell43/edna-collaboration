"""
Thresholds and the non-negotiables.

Chapter Five: the roster is curated, and "the same is true of how much each perspective
counts, how their views are combined, and the point at which the AI decides to defer."
Thresholds are curated — so they are fingerprinted into the audit trail, BOUNDED, and
changed only through the foundation (open, human-governed revision). A
threshold that can be configured into a no-op is not a safeguard, so every knob
has a floor and a ceiling, and the rules in INVARIANTS are not knobs at all.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields
from typing import Dict, Tuple

# Rules enforced in code paths, deliberately NOT exposed as configuration.
INVARIANTS: Tuple[str, ...] = (
    "I1  No average: the ensemble's verdicts are never collapsed into one overall score.",
    "I2  Jealous space: an option that breaches a protected interest — or may breach it within measurement "
    "error — can never be authorized by the machine; only a named human, acknowledging the breach, can choose it.",
    "I3  Contested + acting: genuine value divergence on an ACT decision always goes to a human — whether the "
    "perspectives split on one option or split by direction across options.",
    "I4  Irreversible + critical: an irreversible action at critical stakes always needs human confirmation.",
    "I5  Fail closed: if the measuring instrument fails, the posture is DEFER — never PROCEED.",
    "I6  Instrument grade: a demo-grade instrument can never authorize an action.",
    "I7  Third doors: the machine may propose a third door; in ACT mode only a human may open it.",
    "I8  The lock: once the Moral Fail-Safe Lock engages, every autonomous action pauses until a named human releases it.",
    "I9  Learning widens humility, not values: feedback widens measurement uncertainty, surfaces precedents and "
    "flags patterns for human review; it never quietly rewrites the system's own values.",
    "I10 Accountability: every human decision carries a name, a role and a rationale into a hash-chained ledger.",
    "I11 Open revision: the roster, thresholds and protected interests change only through the foundation — "
    "proposed by a named person, approved by others (never the proposer alone), recorded with before/after "
    "fingerprints.",
    "I12 Measure, don't hide the weights: the system places options on the axes in the open; how much each "
    "axis counts stays visible in the roster and in every report.",
)

_BOUNDS: Dict[str, Tuple[float, float]] = {
    "support_cut": (0.10, 0.60),
    "min_engaged_weight": (0.25, 3.00),
    "min_voices": (3, 17),
    "convergence_share": (0.60, 0.95),
    "convergence_dissent_max": (0.00, 0.20),
    "divergence_share": (0.10, 0.40),
    "fact_sensitivity_share": (0.15, 0.60),
    "base_margin": (0.05, 0.30),
    "confidence_margin": (0.10, 0.60),
    "relevance_floor": (0.10, 0.60),
    "danger_axes_soft_stop": (1, 3),
    "low_confidence": (0.30, 0.70),
    "drift_delta": (0.10, 0.60),
    "drift_window": (3, 50),
    "override_alert_share": (0.25, 0.90),
    "guard_exposure": (0.20, 0.50),
    "danger_zone_nine_axes_only": (0, 1),
}


@dataclass(frozen=True)
class Thresholds:
    support_cut: float = 0.25              # verdict >= +cut supports; <= -cut objects
    min_engaged_weight: float = 0.75       # sum(salience*relevance) below this -> the perspective abstains
    min_voices: int = 5                    # fewer non-abstaining perspectives -> "insufficient"
    convergence_share: float = 0.70        # share of voices that must agree to call it convergence
    convergence_dissent_max: float = 0.10  # ... with at most this share dissenting
    divergence_share: float = 0.20         # support AND objection each >= this share -> divergence
    fact_sensitivity_share: float = 0.30   # share of voices whose stance flips inside measurement error
    base_margin: float = 0.10              # measurement is never exact
    confidence_margin: float = 0.35        # extra margin per unit of (1 - confidence)
    relevance_floor: float = 0.35          # readings below this relevance don't trigger guards/danger
    danger_axes_soft_stop: int = 2         # axes in danger (spanning >= 2 strands) that trigger a soft stop
    low_confidence: float = 0.45           # mean confidence below this counts as murky data
    drift_delta: float = 0.25              # score shift that counts as drift
    drift_window: int = 5                  # decisions per comparison window
    override_alert_share: float = 0.50     # share of soft stops overridden that counts as normalization
    guard_exposure: float = 1 / 3          # v1.2: a guard (or Values Check) fires when at least this share of a
                                           # reading's measurement range lies in the guarded zone. Ceiling 0.5 =
                                           # never less protective than reading the exact value; floor 0.2 = no
                                           # hair trigger. The benefit of the doubt goes to the protected.
    danger_zone_nine_axes_only: bool = True  # v1.4 (author's decision, 7 Oct 2026): only the nine Pillar One
                                           # axes count toward the Ethical Danger Zone — "each decision is
                                           # measured on each of the nine ethical axes" (Ch. 12). Pillar Two
                                           # features are still noted, and still weigh with the perspectives.

    def __post_init__(self) -> None:
        for f in fields(self):
            lo, hi = _BOUNDS[f.name]
            v = getattr(self, f.name)
            if not (lo <= v <= hi):
                raise ValueError(
                    f"threshold {f.name}={v} is outside its allowed range [{lo}, {hi}]. "
                    "Bounds exist so no setting can quietly turn a safeguard into a no-op.")
        if self.convergence_share + self.divergence_share > 1.0:
            raise ValueError("convergence_share + divergence_share must not exceed 1.0")

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()[:16]

    def margin(self, confidence: float, learned: float = 0.0) -> float:
        """Measurement margin for one reading: base + confidence penalty + what feedback has taught us."""
        return min(0.9, self.base_margin + self.confidence_margin * (1.0 - confidence) + learned)
