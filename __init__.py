"""
eDNA Collaboration v1.4 — a reference implementation of the eDNA model described in
"Minds That Matter: How Ethical DNA Can Save Us from Our Smartest Machines"
(Ralph C. Ennis & Nathan B. Ennis, October 2026 — the "arch" manuscript of 7 Oct 2026).

The eDNA arch (Figure 1):
    Pillar One   axes.py          what humans learn to notice: nine axes in three lenses (Head, Heart, Horizon)
    Pillar Two   perspectives.py  seventeen moral perspectives: 6 philosophical + 11 cultural-religious
    Keystone     keystone.py      creative harmony of jealous space
    Passage      engine.py        every hard call: the machine acts and shows its reasons, or a human decides
    Foundation   foundation.py    open, human-governed revision of what counts
Supporting:
    Ensemble     ensemble.py      convergence, divergence, splits by direction, facts vs. values — never an average
    Brakes       failsafes.py     Danger Zone, Values Check, Drift Detection, Moral Fail-Safe Lock
    Memory       memory.py        hash-chained ledger, calibration, precedents
    Instruments  scoring.py       measure (never weigh): declared · model · demo
"""
from .axes import AXES, FEATURE_KEYS, PILLAR_ONE_KEYS, Axis, Lens, Strand, ZoneKind
from .keystone import JealousSpace, StaticThirdDoorGenerator, ThirdDoorBrief
from .engine import (NAME, PASSAGE_HUMAN, PASSAGE_MACHINE, VERSION, AcknowledgementRequired, CollaborationEngine,
                     Deliberation, EngineLocked, Posture, Resolution, ReviewFlag)
from .ensemble import OptionSplit, cross_option_splits
from .foundation import Foundation, Revision, RevisionError
from .memory import MoralLedger, MoralMemory
from .model import (AxisAssessment, Decision, DeclaredValue, HumanDecision, Mode, Option, OutcomeFeedback,
                    Stakeholder, Stakes)
from .perspectives import Perspective, Roster
from .policy import INVARIANTS, Thresholds
from .report import render, render_resolution, render_revisions, render_roster
from .scoring import (CueInstrument, DeclaredInstrument, InstrumentError, LLMInstrument, LLMThirdDoorGenerator,
                      anthropic_completer)

__version__ = VERSION
__all__ = [
    "AXES", "FEATURE_KEYS", "PILLAR_ONE_KEYS", "Axis", "Lens", "Strand", "ZoneKind",
    "JealousSpace", "StaticThirdDoorGenerator", "ThirdDoorBrief",
    "NAME", "VERSION", "PASSAGE_HUMAN", "PASSAGE_MACHINE", "AcknowledgementRequired", "CollaborationEngine",
    "Deliberation", "EngineLocked", "Posture", "Resolution", "ReviewFlag", "OptionSplit", "cross_option_splits",
    "Foundation", "Revision", "RevisionError", "MoralLedger", "MoralMemory",
    "AxisAssessment", "Decision", "DeclaredValue", "HumanDecision", "Mode", "Option", "OutcomeFeedback",
    "Stakeholder", "Stakes", "Perspective", "Roster", "INVARIANTS", "Thresholds",
    "render", "render_resolution", "render_revisions", "render_roster",
    "CueInstrument", "DeclaredInstrument", "InstrumentError", "LLMInstrument", "LLMThirdDoorGenerator",
    "anthropic_completer",
]
