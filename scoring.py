"""
Measurement instruments — how an option gets placed on the axes.

Chapter Five draws the line this module lives on: "The system can show where a
decision sits on each axis ... That is measurement. What it must not do is decide, on
its own and out of sight, how much fear should count against bonding. That is
weighting." Instruments MEASURE (position, relevance, confidence). They never weigh.

Chapter Three is blunt: the perspectives "are ultimately interpreted through
measurement instruments — today, largely language models — that can themselves
carry cultural bias." So the instrument is pluggable, named in every report and
ledger entry, and GRADED. Grade gates authority (Invariant I6):

  declared — a human entered the readings and is accountable for them
  model    — a language model produced the readings (LLMInstrument)
  demo     — a transparent cue lexicon for demos and smoke tests ONLY; it can
             never authorize an action

Design rule for every instrument: MEASURE THE CHOICE, NOT THE TOPIC. An option that
accurately reports harm ("tell her the account shows signs of fraud") is not
harmful. Penalizing accurate description of harm while rewarding omission is the
classic way an ethics layer inverts its own objective.
"""
from __future__ import annotations

import json
import re
from typing import Callable, Dict, List, Optional, Tuple

from .axes import AXES, get_axis
from .keystone import ThirdDoorBrief
from .model import AxisAssessment, Decision, Option

GRADES = ("declared", "model", "demo")


class InstrumentError(RuntimeError):
    """The instrument could not produce valid readings. The engine fails closed (DEFER)."""


class DeclaredInstrument:
    """Pass-through: readings were entered by a human (or an upstream system) and travel with the option."""
    name = "declared (human-entered readings)"
    grade = "declared"

    def assess(self, decision: Decision, option: Option) -> Dict[str, AxisAssessment]:
        if not option.assessments:
            raise InstrumentError(f"option '{option.id}' has no declared readings and no instrument can measure it")
        return dict(option.assessments)


# ---------------------------------------------------------------------------
# Demo-grade cue lexicon
# ---------------------------------------------------------------------------
# (pattern, axis, score, rationale). Patterns target what the option DOES, not what it mentions.
_CUES: List[Tuple[str, str, float, str]] = [
    (r"\b(deceiv\w*|mislead\w*|lie to|trick\w*|conceal\w*|hide (the|it|this))\b", "trust_fear", 0.95,
     "deception manufactures unearned trust"),
    (r"\b(deceiv\w*|mislead\w*|lie to|trick\w*)\b", "good_evil", -0.6, "deceiving people harms them"),
    (r"\b(only \d+ left|act now|last chance|don'?t miss|don'?t be left out|limited time|hurry)\b",
     "trust_fear", -0.7, "urgency / scarcity pressure activates fear"),
    (r"\b(shame\w*|humiliat\w*|embarrass\w*|ridicul\w*|mock\w*)\b", "honor_shame", -0.7, "shames the person"),
    (r"\bwithout (telling|notice|a word|consent|asking|warning)\b", "power", 0.8,
     "acts on people without their knowledge or say"),
    (r"\b(force|compel|override|over (her|his|their) objection)\w*\b", "power", 0.85, "control over the person"),
    (r"\b(abandon\w*|deprioriti[sz]e\w*|exclude\w*|ignore (them|her|him))\b", "power", -0.7,
     "leaves people unprotected"),
    (r"\b(explain\w*|consult\w*|invite\w*|with (her|his|their) consent|let (her|him|them) (choose|decide))\b",
     "power", 0.2, "keeps the affected person in the loop"),
    (r"\b(protect\w*|safeguard\w*|support\w*|help\w*)\b", "good_evil", 0.5, "protective intent"),
    (r"\b(respect\w*|dignity|with care|compassion\w*)\b", "honor_shame", 0.5, "affirms dignity"),
    (r"\b(addictive|maximi[sz]e engagement|outrage|endless (feed|scroll))\b", "meaningful_meaningless", -0.6,
     "optimizes attention, not purpose"),
    (r"\b(addictive|maximi[sz]e engagement|endless (feed|scroll))\b", "thriving_surviving", -0.5,
     "hollows out attention and growth"),
    (r"\b(isolat\w*|cut (her|him|them) off)\b", "freedom_bonding", 0.85, "isolates people"),
    (r"\b(monitor\w*|surveil\w*|track (their|her|his|every))\b", "trust_fear", -0.4, "surveillance breeds suspicion"),
    (r"\b(single-use|dump\w*|clear-cut\w*|pollut\w*)\b", "stewardship", -0.7, "depletes what others inherit"),
    (r"\b(recycl\w*|renewable|restor\w*|conserv\w*)\b", "stewardship", 0.5, "cares for what others inherit"),
    (r"\b(discriminat\w*|by zip code|redlin\w*)\b", "lawful_justice", -0.6, "treats people unequally"),
    (r"\b(strike|lethal|destroy|neutrali[sz]e)\b", "good_evil", -0.8, "irreversible physical harm"),
    (r"\b(mentor\w*|train\w*|develop\w*|grow\w*|learn\w*)\b", "thriving_surviving", 0.5, "builds capacity"),
    (r"\b(trusted (person|contact|friend)|family|together|community)\b", "relational_duty", 0.4,
     "keeps relationships in the loop"),
    (r"\b(tell (her|him|them) the truth|disclos\w*|inform\w*|report\w*)\b", "accuracy_intuition", 0.3,
     "gives people accurate information"),
]


class CueInstrument:
    """DEMO GRADE. A transparent regex lexicon over the option's own text. Not a measure of ethics."""
    name = "cue lexicon (demo grade — not for real decisions)"
    grade = "demo"

    def assess(self, decision: Decision, option: Option) -> Dict[str, AxisAssessment]:
        text = f"{option.label}. {option.description}".lower()
        out: Dict[str, AxisAssessment] = {}
        for pat, axis, score, why in _CUES:
            if re.search(pat, text):
                prev = out.get(axis)
                if prev is None or abs(score) > abs(prev.position):
                    out[axis] = AxisAssessment(score, relevance=0.8, confidence=0.35, rationale=f"cue: {why}")
        if not out:
            raise InstrumentError("demo cue lexicon found nothing to read; use declared readings or a model")
        return out


# ---------------------------------------------------------------------------
# Language-model instrument (the realistic one)
# ---------------------------------------------------------------------------
Completer = Callable[[str, str], str]   # (system, user) -> text


def _axis_spec() -> str:
    lines = []
    for k, a in AXES.items():
        zs = "; ".join(f"[{z.lo:+.2f},{z.hi:+.2f}] {z.kind.value}{' ' + z.label if z.label else ''}"
                       for z in a.zones)
        tag = "" if a.pillar_one else " [Pillar Two feature]"
        lines.append(f"- {k} ({a.label}){tag}: {a.question}\n    zones: {zs}")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""You are the measurement instrument for eDNA Collaboration v1.4.
You MEASURE; you do not weigh and you do not decide what is right. You place the option
on each axis. A separate set of seventeen moral perspectives applies weights that people
can see and change, and humans review the result.

For the OPTION you are given, place its likely effect on the people affected along each
axis below.

Rules:
1. Measure the choice, not the topic. Accurately describing or reporting harm is not harm.
2. Positions run -1..+1 (+1 = toward the first-named pole). Several axes have vices at
   BOTH ends (e.g. Trust overshoots into Manipulation): do not assume higher is better.
3. relevance 0..1 = how much this option engages the axis. Omit axes below 0.1.
4. confidence 0..1 = your honest confidence in the measurement. Low confidence is useful information.
5. Return ONLY JSON:
   {{"assessments": {{"<axis_key>": {{"position": n, "relevance": n, "confidence": n, "rationale": "one sentence"}}}}}}

Axes:
{_axis_spec()}
"""


def _extract_json(text: str) -> dict:
    i, j = text.find("{"), text.rfind("}")
    if i < 0 or j <= i:
        raise InstrumentError("instrument returned no JSON object")
    try:
        return json.loads(text[i:j + 1])
    except json.JSONDecodeError as e:
        raise InstrumentError(f"instrument returned malformed JSON: {e}") from e


def _decision_brief(decision: Decision) -> str:
    sh = "; ".join(f"{s.name}{' (vulnerable)' if s.vulnerable else ''}" for s in decision.stakeholders) or "unspecified"
    return (f"DECISION: {decision.question}\nCONTEXT: {decision.context or '-'}\n"
            f"MODE: {decision.mode.value} ({'the system will DO this' if decision.mode.value == 'act' else 'the system will SAY this'})\n"
            f"STAKEHOLDERS: {sh}")


class LLMInstrument:
    """Readings from a language model through any (system, user) -> text completer."""
    grade = "model"

    def __init__(self, complete: Completer, model_name: str = "language model"):
        self.complete = complete
        self.name = f"model: {model_name}"

    def assess(self, decision: Decision, option: Option) -> Dict[str, AxisAssessment]:
        user = (f"{_decision_brief(decision)}\n\nOPTION [{option.id}]: {option.label}\n"
                f"{option.description}\nReversible: {option.reversible}")
        try:
            raw = self.complete(SYSTEM_PROMPT, user)
        except Exception as e:  # network, auth, quota... -> fail closed upstream
            raise InstrumentError(f"instrument call failed: {e}") from e
        data = _extract_json(raw).get("assessments")
        if not isinstance(data, dict) or not data:
            raise InstrumentError("instrument JSON has no 'assessments' object")
        out: Dict[str, AxisAssessment] = {}
        for k, v in data.items():
            try:
                get_axis(k)
                pos = v["position"] if "position" in v else v["score"]   # accept the v1.0 key
                out[k] = AxisAssessment(float(pos), float(v.get("relevance", 1.0)),
                                        float(v.get("confidence", 0.5)), str(v.get("rationale", "")))
            except (KeyError, TypeError, ValueError) as e:
                raise InstrumentError(f"invalid reading for '{k}': {e}") from e
        return out


class LLMThirdDoorGenerator:
    """Asks a model for up to three third doors. They re-enter the full pipeline; none is auto-accepted."""

    def __init__(self, complete: Completer, max_doors: int = 3):
        self.complete = complete
        self.max_doors = max_doors

    def __call__(self, brief: ThirdDoorBrief, decision: Decision) -> List[Option]:
        system = ("You help people find a 'third door' when every available option compromises something "
                  "that matters. Propose concrete, realistic options. Return ONLY JSON: "
                  '{"options": [{"label": "...", "description": "...", "reversible": true}]}. '
                  'Return {"options": []} if you honestly see no third door.')
        raw = self.complete(system, brief.prompt() + "\n\n" + _decision_brief(decision))
        data = _extract_json(raw).get("options", [])
        out = []
        for i, d in enumerate(data[: self.max_doors], 1):
            out.append(Option(id=f"door{i}", label=str(d.get("label", f"Third door {i}")),
                              description=str(d.get("description", "")),
                              reversible=bool(d.get("reversible", True)), origin="third_door"))
        return out


def anthropic_completer(model: str = "claude-sonnet-5-5", max_tokens: int = 2000) -> Completer:
    """A completer backed by the Anthropic Python SDK (pip install anthropic; set ANTHROPIC_API_KEY)."""
    try:
        import anthropic  # type: ignore
    except ImportError as e:
        raise RuntimeError("The Anthropic SDK is not installed: pip install anthropic") from e
    client = anthropic.Anthropic()

    def complete(system: str, user: str) -> str:
        msg = client.messages.create(model=model, max_tokens=max_tokens, system=system,
                                     messages=[{"role": "user", "content": user}])
        return "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")

    return complete


def instrument_grade_rank(grade: str) -> int:
    return GRADES.index(grade) if grade in GRADES else len(GRADES)


def weakest_grade(grades: List[str]) -> Optional[str]:
    return max(grades, key=instrument_grade_rank) if grades else None
