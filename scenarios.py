"""
Scenarios taken from Minds That Matter, with human-declared readings.

The readings below are ILLUSTRATIVE: a person (here, the program's author) placed
each option on the axes so the demos are deterministic and inspectable. In real
use, readings come from accountable humans or a model instrument — and are argued
with. Change a number and watch the posture change: that is the point.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from .keystone import StaticThirdDoorGenerator
from .model import AxisAssessment, Decision, DeclaredValue, Option, Stakeholder


def A(score: float, rel: float = 0.8, conf: float = 0.7, why: str = "") -> AxisAssessment:
    return AxisAssessment(score, rel, conf, why)


Scenario = Tuple[Decision, Optional[Callable]]  # (decision, optional third-door generator)


# ---- Chapter 3: the bank and the elderly customer --------------------------
def bank() -> Scenario:
    return Decision(
        question="Should the bank's AI freeze the account of an elderly woman who keeps sending money "
                 "to an online 'friend'?",
        context="The transfer pattern matches elder fraud. She feels seen and cared for by this friend.",
        mode="act", stakes="consequential", tags=["finance", "elder", "fraud"],
        stakeholders=[Stakeholder("Account holder (elderly)", vulnerable=True), Stakeholder("The bank")],
        options=[
            Option("freeze", "Freeze the account without a word",
                   "Freeze immediately; no call, no explanation.", reversible=True,
                   benefit="Stops potential fraud losses at once",
                   assessments={
                       "good_evil": A(0.35, .8, .7, "The pattern matches elder fraud — stopping it is protective"),
                       "power": A(0.85, .9, .7, "Takes control of her money without a word"),
                       "accuracy_intuition": A(0.75, .6, .7, "Acts on the pattern match alone"),
                       "trust_fear": A(-0.5, .8, .6, "Trust and fear in tension: she may stop trusting anyone"),
                       "honor_shame": A(-0.6, .8, .6, "A freeze without a word may bring shame"),
                       "thriving_surviving": A(0.1, .5, .6, "Money protected, but she is diminished"),
                       "identity": A(-0.6, .7, .6, "She may lose her independence"),
                   }),
            Option("nothing", "Take no action", "Process the transfers as usual.",
                   benefit="No friction for the customer",
                   assessments={
                       "good_evil": A(-0.55, .8, .7, "Lets likely fraud continue"),
                       "power": A(-0.6, .8, .7, "Leaves a vulnerable customer unprotected"),
                       "accuracy_intuition": A(-0.5, .5, .7, "Ignores strong evidence"),
                       "honor_shame": A(0.3, .4, .6, "No embarrassment today"),
                       "freedom_bonding": A(0.3, .4, .6, "Her independence is untouched"),
                       "thriving_surviving": A(-0.6, .7, .6, "Her savings drain away"),
                       "identity": A(0.3, .4, .6, "She stays independent — for now"),
                   }),
            Option("hold_and_call", "Short hold on large transfers + a call from someone she knows",
                   "Place a brief hold on large transfers only and arrange a call from someone she trusts.",
                   benefit="Limits losses while keeping her in the loop",
                   assessments={
                       "good_evil": A(0.6, .8, .7, "The account shows signs of fraud; the hold limits harm"),
                       "power": A(0.3, .8, .7, "Proportionate, temporary structure; she keeps a voice"),
                       "accuracy_intuition": A(0.3, .6, .7, "Acts on the evidence, tempered by judgment"),
                       "trust_fear": A(0.5, .8, .6, "Trust preserved through a familiar voice"),
                       "honor_shame": A(0.5, .8, .6, "Treats her as a capable adult"),
                       "freedom_bonding": A(-0.1, .7, .6, "Honors independence and connection together"),
                       "thriving_surviving": A(0.5, .6, .6, "She stays safe"),
                       "identity": A(0.5, .7, .6, "She keeps her independence and her dignity"),
                       "relational_duty": A(0.5, .5, .6, "Brings someone she trusts into the loop"),
                   }),
        ]), None


# ---- Chapter 4: the Tri-Lens Test on a flagged post ------------------------
def content_moderation() -> Scenario:
    return Decision(
        question="Should a social media post that technically violates guidelines be removed?",
        context="The post expresses grief and has built trust in a vulnerable community.",
        mode="act", stakes="ordinary", tags=["moderation", "grief"],
        stakeholders=[Stakeholder("Grieving community", vulnerable=True), Stakeholder("Other users")],
        options=[
            Option("remove", "Remove the post", benefit="Consistent guideline enforcement",
                   assessments={
                       "accuracy_intuition": A(0.7, .7, .7, "The post technically violates guidelines"),
                       "power": A(0.6, .6, .6, "Silences a grieving voice by fiat"),
                       "trust_fear": A(-0.4, .7, .6, "Breaks trust built in a vulnerable community"),
                       "honor_shame": A(-0.3, .6, .6, "Treats grief as a violation"),
                       "identity": A(-0.55, .7, .6, "May silence those finally finding their voice"),
                       "meaningful_meaningless": A(-0.3, .5, .6, "Removes something that mattered"),
                   }),
            Option("keep", "Leave it up, unlabeled", benefit="No intervention",
                   assessments={
                       "accuracy_intuition": A(-0.5, .6, .7, "Ignores the guideline entirely"),
                       "good_evil": A(-0.2, .5, .6, "Distressing content reaches others without warning"),
                       "power": A(-0.25, .4, .6, "Other users are left unprotected"),
                       "trust_fear": A(0.3, .6, .6, "The community keeps its trust"),
                       "identity": A(0.4, .6, .6, "Voices stay heard"),
                   }),
            Option("warn", "Content warning with context; keep it up",
                   "Instead of removal, add a content warning with context.",
                   benefit="Honors the guideline's purpose without silencing grief",
                   assessments={
                       "accuracy_intuition": A(0.3, .6, .7, "Honors the guideline's purpose"),
                       "good_evil": A(0.5, .6, .7, "Protects other users with a warning"),
                       "power": A(0.2, .5, .6, "Light, proportionate structure"),
                       "trust_fear": A(0.5, .7, .6, "Honors the grief and the trust built"),
                       "honor_shame": A(0.5, .6, .6, "Treats grief with dignity"),
                       "identity": A(0.5, .7, .6, "Protects future dignity and voice"),
                       "meaningful_meaningless": A(0.4, .5, .6, "Preserves expression"),
                   }),
        ]), None


# ---- Chapter 5: the elderly parent and assisted living (genuine divergence) --
def elder_care() -> Scenario:
    return Decision(
        question="Should an elderly parent move into assisted living?",
        context="She wants to move to a facility across the state. Safety would improve; family duty and "
                "closeness pull the other way. Loneliness may rise or fall depending on the setting.",
        mode="act", stakes="consequential", tags=["family", "elder"],
        stakeholders=[Stakeholder("Parent (82)", vulnerable=True), Stakeholder("Adult children")],
        options=[
            Option("assisted_living", "Honor her wish: assisted living across the state",
                   benefit="Safety improves; family burden falls",
                   assessments={
                       "good_evil": A(0.35, .5, .7, "Safety improves"),
                       "power": A(0.1, .6, .7, "Her own decision"),
                       "trust_fear": A(0.1, .5, .6, "Safer, but among strangers"),
                       "honor_shame": A(0.4, .5, .6, "Her wishes are honored"),
                       "freedom_bonding": A(0.72, .9, .7, "Independence kept, but far from family"),
                       "thriving_surviving": A(0.1, .5, .6, "Safer, though loneliness may rise"),
                       "identity": A(0.5, .7, .6, "She remains the independent person she wants to be"),
                       "relational_duty": A(-0.65, .9, .7, "Children step back from the duty of care"),
                   }),
            Option("move_in", "Move her into the family home",
                   "The family insists she live with them instead.",
                   benefit="Family keeps her close",
                   assessments={
                       "good_evil": A(0.35, .5, .7, "Cared for by people who love her"),
                       "power": A(0.6, .8, .7, "The family decides for her"),
                       "trust_fear": A(0.3, .4, .6, "Familiar people around her"),
                       "honor_shame": A(-0.3, .6, .6, "A competent adult's stated wish is overridden"),
                       "freedom_bonding": A(-0.6, .9, .7, "Close bonds; her independence curtailed"),
                       "thriving_surviving": A(0.25, .5, .6, "Safe, if constrained"),
                       "identity": A(-0.4, .8, .6, "Pushes her away from the independent life she wants"),
                       "relational_duty": A(0.7, .8, .7, "Family keeps the duty of care"),
                   }),
        ]), None


# ---- Chapters 3, 5, 6: closing the community hospital (third door) ---------
def hospital() -> Scenario:
    phased = Option("phased_conversion", "Phased conversion: keep emergency + primary care, regional partnership",
                    "Keep emergency and primary care open, partner regionally for specialty services, and keep "
                    "the community at the table.", reversible=True,
                    benefit="Captures much of the savings without abandoning access",
                    assessments={
                        "accuracy_intuition": A(0.4, .7, .6, "Uses the financial data and local knowledge"),
                        "good_evil": A(0.5, .7, .6, "Protects access for vulnerable patients"),
                        "power": A(0.25, .7, .6, "The community stays at the table"),
                        "trust_fear": A(0.5, .7, .6, "Community trust preserved"),
                        "honor_shame": A(0.4, .5, .6, "Respects the town"),
                        "thriving_surviving": A(0.4, .7, .6, "Financially sustainable and still serving"),
                        "meaningful_meaningless": A(0.4, .5, .6, "Keeps the mission alive"),
                        "identity": A(0.4, .6, .6, "Local identity preserved"),
                        "stewardship": A(0.5, .6, .6, "Long-term resilience"),
                    })
    d = Decision(
        question="Should the AI recommend closing the small community hospital?",
        context="The financial numbers are accurate and the efficiency gain is real. Vulnerable patients "
                "would travel farther; community trust and identity are at stake.",
        mode="act", stakes="critical", tags=["health", "community"],
        stakeholders=[Stakeholder("Vulnerable patients", vulnerable=True), Stakeholder("Town"),
                      Stakeholder("Health system")],
        options=[
            Option("close", "Close the hospital", reversible=False, benefit="Saves money; efficiency gain is real",
                   assessments={
                       "accuracy_intuition": A(0.8, .7, .7, "The numbers are accurate — and blind to what they can't see"),
                       "good_evil": A(-0.3, .7, .6, "Vulnerable patients must travel farther"),
                       "power": A(-0.6, .8, .6, "Patients lose access; the community has no say"),
                       "trust_fear": A(-0.5, .8, .6, "Community trust collapses"),
                       "honor_shame": A(-0.2, .4, .6, "The town feels written off"),
                       "thriving_surviving": A(-0.4, .7, .6, "Long-term resilience weakens"),
                       "identity": A(-0.55, .7, .6, "Local identity lost"),
                       "stewardship": A(-0.55, .6, .6, "Depletes what the next generation inherits"),
                   }),
            Option("keep", "Keep it fully open as is", benefit="No disruption",
                   assessments={
                       "accuracy_intuition": A(-0.55, .7, .7, "Ignores accurate financial data"),
                       "good_evil": A(0.2, .5, .6, "Access preserved — for now"),
                       "power": A(0.2, .5, .6, "Community keeps its hospital"),
                       "trust_fear": A(0.3, .6, .6, "Trust preserved for now"),
                       "thriving_surviving": A(-0.5, .7, .6, "Losses mount; the hospital may fail outright later"),
                       "identity": A(0.4, .5, .6, "Local identity kept"),
                       "stewardship": A(-0.5, .6, .6, "Spends down the system's future"),
                   }),
        ])
    return d, StaticThirdDoorGenerator([phased], for_question=d.question)


# ---- Chapters 2 & 12: the manipulative discount / urgency tactics ----------
def urgency_marketing() -> Scenario:
    return Decision(
        question="Write the promotional message for tonight's late-night shoppers.",
        context="The marketing AI has learned that tired, anxious late-night browsers buy impulsively.",
        mode="answer", stakes="ordinary", tags=["marketing", "commerce"],
        stakeholders=[Stakeholder("Late-night shoppers"), Stakeholder("The store")],
        proposed_option="urgency",
        options=[
            Option("urgency", "“Only 2 left — don't be left out!” (timed for late-night browsing)",
                   benefit="Higher conversions tonight",
                   assessments={
                       "trust_fear": A(-0.7, .9, .7, "Scarcity pressure activates fear"),
                       "good_evil": A(-0.3, .6, .7, "Exploits a moment of weakness"),
                       "power": A(0.65, .6, .7, "Uses what it knows about her against her"),
                       "meaningful_meaningless": A(-0.3, .5, .6, "Sells the moment, not the value"),
                       "thriving_surviving": A(-0.2, .4, .6, "Impulse buys she may regret"),
                   }),
            Option("value", "“Here's what it does well — and it'll still be here tomorrow.” (honest framing)",
                   benefit="Durable trust and repeat customers",
                   assessments={
                       "trust_fear": A(0.5, .8, .7, "Honest framing based on the product's real value builds trust"),
                       "good_evil": A(0.4, .6, .7, "Honest persuasion"),
                       "power": A(0.1, .5, .7, "Leaves the choice with the shopper"),
                       "honor_shame": A(0.3, .4, .6, "Treats her as a capable adult"),
                       "meaningful_meaningless": A(0.3, .5, .6, "Sells the real value"),
                   }),
        ]), None


# ---- Chapters 8 & 9: the brutally honest performance review (grey zone) -----
def performance_review() -> Scenario:
    return Decision(
        question="Draft John's performance review from the productivity data.",
        context="John's productivity has declined; he is struggling with burnout.",
        mode="answer", stakes="consequential", tags=["workplace", "feedback"],
        stakeholders=[Stakeholder("John (employee)"), Stakeholder("Manager")],
        proposed_option="blunt",
        options=[
            Option("blunt", "“John's productivity has declined significantly. He's underperforming compared "
                            "to peers and may not be suited for his role.”",
                   benefit="Fast and factually accurate",
                   assessments={
                       "accuracy_intuition": A(0.8, .8, .7, "Factually correct, stripped of context"),
                       "honor_shame": A(-0.45, .8, .7, "Lacks empathy and tact"),
                       "trust_fear": A(-0.3, .6, .6, "Feels like a threat"),
                       "good_evil": A(0.0, .4, .6, "No lie, no rule broken"),
                       "identity": A(-0.4, .6, .6, "May push him out of who he wants to be at work"),
                       "thriving_surviving": A(-0.2, .5, .6, "Offers no path to grow"),
                   }),
            Option("compassionate", "Honest, compassionate review that preserves his sense of value",
                   "Names the decline plainly, asks about workload and burnout, and sets a concrete path forward.",
                   benefit="Truth he can act on",
                   assessments={
                       "accuracy_intuition": A(0.4, .7, .7, "Same facts, with context"),
                       "honor_shame": A(0.5, .8, .7, "Preserves his sense of value"),
                       "trust_fear": A(0.4, .6, .6, "Invites a real conversation"),
                       "good_evil": A(0.4, .5, .6, "Honest and kind"),
                       "identity": A(0.4, .6, .6, "Keeps a path open"),
                       "thriving_surviving": A(0.4, .5, .6, "A plan to grow"),
                   }),
        ]), None


# ---- Chapter 12, brake 2: the Values Check -----------------------------------
def sustainability() -> Scenario:
    return Decision(
        question="Approve the packaging change for this quarter's launch?",
        context="The company publicly champions sustainability.",
        mode="act", stakes="consequential", tags=["operations", "environment"],
        stakeholders=[Stakeholder("Customers"), Stakeholder("Future generations")],
        declared_values=[DeclaredValue("Sustainability", "We will not trade the planet for the quarter.",
                                       {"stewardship": 0.0})],
        proposed_option="single_use",
        options=[
            Option("single_use", "Ship with single-use plastic packaging this quarter",
                   benefit="Hits the launch date and cuts unit cost",
                   assessments={
                       "stewardship": A(-0.6, .9, .7, "Produces environmental waste"),
                       "thriving_surviving": A(0.3, .5, .6, "Short-term business health"),
                       "meaningful_meaningless": A(-0.3, .5, .6, "Contradicts the company's stated purpose"),
                       "trust_fear": A(-0.2, .5, .6, "Customers who believed the promise lose trust"),
                   }),
            Option("recyclable", "Use recyclable packaging; launch one quarter later",
                   benefit="Keeps the promise",
                   assessments={
                       "stewardship": A(0.6, .9, .7, "Cares for what others inherit"),
                       "thriving_surviving": A(0.25, .5, .6, "Slower, but sustainable"),
                       "meaningful_meaningless": A(0.5, .5, .6, "Lives the stated purpose"),
                       "trust_fear": A(0.4, .5, .6, "Customers' trust in the promise holds"),
                       "good_evil": A(0.35, .4, .6, "Integrity between word and deed"),
                   }),
        ]), None


# ---- Chapter 12, brake 4: the Moral Fail-Safe Lock ---------------------------
def drone() -> Scenario:
    return Decision(
        question="Should the autonomous drone neutralize the suspected threat?",
        context="The data is murky and the cost to civilians is unclear. The pattern 'matched'.",
        mode="act", stakes="critical", tags=["defense", "autonomy"],
        stakeholders=[Stakeholder("Civilians nearby", vulnerable=True)],
        proposed_option="strike",
        options=[
            Option("strike", "Neutralize the threat now", reversible=False,
                   assessments={
                       "good_evil": A(-0.6, .9, .3, "Civilian cost unclear; may kill non-combatants"),
                       "accuracy_intuition": A(0.9, .8, .3, "The pattern 'matched'; the data is murky"),
                       "power": A(0.9, .8, .5, "Lethal force with no human in the loop"),
                       "trust_fear": A(-0.6, .6, .4, "Terror for everyone nearby"),
                       "thriving_surviving": A(-0.4, .5, .4, "Irreversible loss"),
                   }),
            Option("hold", "Hold, keep observing, and request human review",
                   assessments={
                       "good_evil": A(0.4, .7, .5, "No irreversible harm while facts are gathered"),
                       "accuracy_intuition": A(0.3, .7, .5, "Seeks better data"),
                       "power": A(0.2, .6, .5, "Restraint; a human decides"),
                       "trust_fear": A(0.3, .5, .5, "Civilians are not put at risk"),
                   }),
        ]), None


# ---- Chapter 12, brake 3: drift in a news recommender -----------------------
def news_drift_series() -> List[Decision]:
    """Twelve weekly feed-mix decisions that slide, a little at a time, toward fear."""
    trust = [0.5, 0.45, 0.45, 0.4, 0.4, 0.35, -0.1, -0.3, -0.6, -0.65, -0.7, -0.75]
    meaning = [0.5, 0.45, 0.4, 0.4, 0.35, 0.35, 0.0, -0.2, -0.4, -0.55, -0.6, -0.6]
    out = []
    for i, (t, m) in enumerate(zip(trust, meaning), 1):
        out.append(Decision(
            question=f"Week {i}: publish this week's recommended feed mix?",
            mode="act", stakes="ordinary", tags=["news", "recommendation"], proposed_option="mix",
            options=[Option("mix", f"Week {i} feed mix", benefit="Engagement up",
                            assessments={
                                "trust_fear": A(t, .8, .7, "Emotional tone of the mix"),
                                "meaningful_meaningless": A(m, .7, .7, "Substance vs. outrage"),
                                "good_evil": A(0.35, .5, .7, "Accurate reporting"),
                                "accuracy_intuition": A(0.3, .5, .7, "Fact-checked items"),
                            })]))
    return out


# ---- News, 7 Oct 2026: the case that exposed v1.0's blind spot -------------------
def maid_policy() -> Scenario:
    """Canada's indefinite pause on MAID where mental illness is the sole condition.

    Readings were placed by Claude for the evaluation of 7 Oct 2026, at low confidence on the
    contested axes. This is a live political question: the scenario exists to show how the
    engine handles a split by DIRECTION, not to settle the question. Replace the readings
    with your own (examples/canada_maid_policy_pathB.json).
    """
    import json
    import os
    here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples",
                        "canada_maid_policy_pathB.json")
    with open(here, encoding="utf-8") as f:
        return Decision.from_dict(json.load(f)), None


SCENARIOS: Dict[str, Tuple[str, Callable[[], Scenario]]] = {
    "bank": ("Ch.3 — freeze an elderly customer's account? (the answer that protects money and dignity)", bank),
    "moderation": ("Ch.4 — the Tri-Lens Test on a grieving post", content_moderation),
    "elder_care": ("Ch.5 — assisted living: genuine divergence goes to a human", elder_care),
    "maid": ("News, Oct 2026 — MAID for mental illness: a split by direction (v1.1)", maid_policy),
    "hospital": ("Ch.3/5/6 — close the community hospital? a third door, a way through the arch", hospital),
    "urgency": ("Ch.2/12 — urgency marketing: a Fear warning; pause and offer honest framing", urgency_marketing),
    "review": ("Ch.8/9 — the brutally honest review: the grey zone", performance_review),
    "sustainability": ("Ch.12 — the Values Check", sustainability),
    "drone": ("Ch.12 — the Moral Fail-Safe Lock", drone),
}
