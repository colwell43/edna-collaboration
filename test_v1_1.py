"""v1.1 tests: the split across options, the arch, the foundation, and accountable learning.

Run with:  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edna_collaboration import (AXES, PASSAGE_HUMAN, PASSAGE_MACHINE, AxisAssessment, CollaborationEngine,  # noqa: E402
                                Decision, HumanDecision, MoralLedger, Option, OutcomeFeedback, Posture,
                                RevisionError, Stakeholder, render)
from edna_collaboration.ensemble import cross_option_splits  # noqa: E402
from edna_collaboration.report import justification  # noqa: E402
from edna_collaboration.scenarios import SCENARIOS  # noqa: E402


def run(name, **kw):
    decision, gen = SCENARIOS[name][1]()
    eng = CollaborationEngine(third_door=gen, **kw)
    return eng, eng.deliberate(decision)


def A(p, rel=0.8, conf=0.7):
    return AxisAssessment(p, rel, conf)


class TestSplitAcrossOptions(unittest.TestCase):
    """The v1.0 blind spot: different families of perspectives objecting to OPPOSITE options."""

    def test_maid_split_is_detected_and_goes_to_a_human(self):
        eng, d = run("maid")
        self.assertEqual(len(d.splits), 1)
        s = d.splits[0]
        self.assertEqual({s.a, s.b}, {"expand_2027", "permanent_exclusion"})
        self.assertTrue(s.robust)
        objectors_expand = set(s.object_a if s.a == "expand_2027" else s.object_b)
        objectors_exclusion = set(s.object_b if s.a == "expand_2027" else s.object_a)
        self.assertTrue({"care", "ubuntu", "confucian_ren"} <= objectors_expand)
        self.assertTrue({"deontology", "existentialism"} <= objectors_exclusion)
        self.assertFalse(objectors_expand & objectors_exclusion)
        # v1.0 said GATHER BETTER FACTS here; a split by direction is not settled by facts alone.
        self.assertEqual(d.posture, Posture.DEFER_TO_HUMAN)
        self.assertEqual(d.passage, PASSAGE_HUMAN)
        self.assertTrue(any("direction" in r for r in d.reasons))
        self.assertIn("pause_indefinitely", d.unobjected)

    def test_irreversible_option_inside_a_split_needs_contested_ack(self):
        _, d = run("maid")
        codes = [a.code for a in d.analyses["expand_2027"].acks]
        self.assertIn("contested_irreversible", codes)

    def test_no_false_split_where_disagreement_is_within_one_option(self):
        for name in ("bank", "elder_care", "urgency", "review", "sustainability", "drone"):
            _, d = run(name)
            self.assertEqual(d.splits, [], name)

    def test_synthetic_split(self):
        # Option A isolates (freedom extreme) and abandons relational duty; option B controls and alienates.
        a = Option("a", "Let her go it alone", assessments={
            "freedom_bonding": A(0.9, 1.0), "relational_duty": A(-0.7, 1.0), "identity": A(0.5)})
        b = Option("b", "Decide for her", assessments={
            "freedom_bonding": A(-0.9, 1.0), "identity": A(-0.7, 1.0), "relational_duty": A(0.6)})
        eng = CollaborationEngine()
        d = eng.deliberate(Decision("q", [a, b], mode="act"))
        self.assertTrue(cross_option_splits({k: x.ensemble for k, x in d.analyses.items()}, eng.th))
        self.assertEqual(d.posture, Posture.DEFER_TO_HUMAN)

    def test_split_appears_in_report_and_ledger(self):
        eng, d = run("maid")
        text = render(d, eng.th)
        self.assertIn("⇄", text)
        self.assertIn("disagreement about direction", text)
        entry = eng.ledger.of_kind("deliberation")[-1]
        self.assertEqual(len(entry["payload"]["splits"]), 1)


class TestArchAlignment(unittest.TestCase):
    def test_passage_through_the_arch(self):
        _, d = run("bank")
        self.assertEqual(d.passage, PASSAGE_MACHINE)
        _, d = run("elder_care")
        self.assertEqual(d.passage, PASSAGE_HUMAN)

    def test_measurement_uses_position_and_accepts_v10_score(self):
        self.assertEqual(AxisAssessment.from_dict({"position": 0.3}).position, 0.3)
        self.assertEqual(AxisAssessment.from_dict({"score": -0.2}).position, -0.2)
        self.assertEqual(AxisAssessment(0.4).score, 0.4)

    def test_grounding_as_the_book_states_it(self):
        for k in ("honor_shame", "meaningful_meaningless", "identity"):
            self.assertEqual(AXES[k].grounding_tier, "later")
        self.assertEqual(AXES["good_evil"].grounding_tier, "early")
        for k in ("relational_duty", "stewardship", "lawful_justice"):
            self.assertEqual(AXES[k].grounding_tier, "pillar-two")
        self.assertEqual(AXES["trust_fear"].grounding_tier, "unstated")

    def test_plain_words_first_axes_behind(self):
        eng, d = run("bank")
        text = justification(d, d.recommended, eng.th.relevance_floor)
        first, behind = text.split("\n", 1)
        self.assertIn("Want to see the trade-offs I weighed?", first)
        self.assertNotIn("↔", first)
        self.assertIn("↔", behind)

    def test_weights_are_visible_in_every_full_report(self):
        eng, d = run("bank")
        self.assertIn("Weights in use", render(d, eng.th))
        self.assertEqual(len(d.weights), 17)

    def test_values_check_wording(self):
        _, d = run("sustainability")
        msg = d.analyses["single_use"].conflicts[0].message()
        self.assertIn("values your organization has publicly declared", msg)
        self.assertIn("Proceed anyway?", msg)

    def test_static_third_door_is_bound_to_its_decision(self):
        decision, gen = SCENARIOS["hospital"][1]()
        eng = CollaborationEngine(third_door=gen)
        self.assertEqual(eng.deliberate(decision).recommended, "phased_conversion")
        maid, _ = SCENARIOS["maid"][1]()
        d = eng.deliberate(maid)
        self.assertNotIn("phased_conversion", d.analyses)


class TestFoundation(unittest.TestCase):
    def test_what_counts_cannot_be_assigned(self):
        eng = CollaborationEngine()
        with self.assertRaises(AttributeError):
            eng.roster = None
        with self.assertRaises(AttributeError):
            eng.th = None

    def test_governed_threshold_revision(self):
        eng = CollaborationEngine()
        before = eng.th.fingerprint()
        rev = eng.foundation.propose("thresholds", {"base_margin": 0.15}, "more humility", "trust misreadings",
                                     "M. Chen", "Policymaker")
        with self.assertRaises(RevisionError):
            eng.foundation.approve(rev.id, "M. Chen", "Policymaker")          # never the proposer alone
        eng.foundation.approve(rev.id, "A. Rivera", "Executive")
        with self.assertRaises(RevisionError):
            eng.foundation.apply(rev.id, "M. Chen", "Policymaker")            # two approvals required
        eng.foundation.approve(rev.id, "J. Okafor", "Citizen")
        eng.foundation.apply(rev.id, "M. Chen", "Policymaker")
        self.assertEqual(eng.th.base_margin, 0.15)
        self.assertNotEqual(before, eng.th.fingerprint())
        kinds = [e["kind"] for e in eng.ledger.entries]
        for k in ("revision_proposed", "revision_approved", "revision_applied"):
            self.assertIn(k, kinds)
        self.assertEqual(eng.ledger.verify(), (True, None))

    def test_revisions_cannot_breach_bounds_or_empty_jealous_space(self):
        eng = CollaborationEngine()
        with self.assertRaises(ValueError):
            eng.foundation.propose("thresholds", {"divergence_share": 0.9}, "x", "y", "P", "Policymaker")
        with self.assertRaises(RevisionError):
            eng.foundation.propose("protected", {}, "x", "y", "P", "Policymaker")

    def test_roster_revision_changes_what_later_deliberations_record(self):
        eng = CollaborationEngine()
        new = eng.roster.to_dict()
        new["perspectives"][0]["weights"]["stewardship"] = 3.0
        rev = eng.foundation.propose("roster", new, "Consequentialism weighs future generations more",
                                     "Board review", "M. Chen", "Policymaker")
        eng.foundation.approve(rev.id, "A", "Reviewer")
        eng.foundation.approve(rev.id, "B", "Reviewer")
        eng.foundation.apply(rev.id, "M. Chen", "Policymaker")
        d = eng.deliberate(SCENARIOS["bank"][1]()[0])
        self.assertEqual(d.roster_fingerprint, rev.new_fingerprint)
        self.assertIn("+rev.", d.roster_version)

    def test_stale_revision_is_refused(self):
        eng = CollaborationEngine()
        r1 = eng.foundation.propose("thresholds", {"base_margin": 0.12}, "a", "a", "P", "Policymaker")
        r2 = eng.foundation.propose("thresholds", {"base_margin": 0.2}, "b", "b", "Q", "Policymaker")
        for r in (r1, r2):
            eng.foundation.approve(r.id, "X", "Reviewer")
            eng.foundation.approve(r.id, "Y", "Reviewer")
        eng.foundation.apply(r1.id, "P", "Policymaker")
        with self.assertRaises(RevisionError):
            eng.foundation.apply(r2.id, "Q", "Policymaker")


class TestAccountableLearning(unittest.TestCase):
    """Chapter 9: widen uncertainty, surface the case, flag it for people — never rewrite values."""

    def test_outcome_registered_across_perspectives_and_flagged(self):
        eng, d = run("bank")
        before = eng.roster.fingerprint()
        res = eng.feedback(OutcomeFeedback(d.id, {"trust_fear": -0.7, "honor_shame": -0.6}))
        self.assertIsNotNone(res.outcome)
        self.assertEqual(len(res.outcome.voices), 17)
        self.assertEqual(len(res.flags), 1)
        self.assertTrue(any("seventeen perspectives" in line for line in res))
        self.assertEqual(before, eng.roster.fingerprint())
        self.assertEqual(eng.deliberate(SCENARIOS["urgency"][1]()[0]).open_review_flags, 1)
        with self.assertRaises(ValueError):
            eng.close_flag(res.flags[0].id, "M. Chen", "Policymaker", " ")
        eng.close_flag(res.flags[0].id, "M. Chen", "Policymaker", "Reviewed; no change to values.")
        self.assertEqual(eng.review_flags[0].status, "closed")

    def test_repeated_misses_on_an_axis_raise_a_pattern_flag(self):
        eng = CollaborationEngine()
        flags = []
        for _ in range(2):
            d = eng.deliberate(SCENARIOS["bank"][1]()[0])
            flags = eng.feedback(OutcomeFeedback(d.id, {"trust_fear": 0.0})).flags   # healthy predicted, neutral observed
        self.assertTrue(flags and "more than once" in flags[0].reason)

    def test_resolved_drone_with_ledger_file_still_verifies(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            eng = CollaborationEngine(ledger=MoralLedger(path))
            d = eng.deliberate(SCENARIOS["drone"][1]()[0])
            eng.resolve(d, HumanDecision("hold", "R", "Reviewer", "hold", release_lock=True,
                                         acknowledged=[a.code for a in d.analyses["hold"].acks]))
            self.assertEqual(MoralLedger(path).verify(), (True, None))


class TestVulnerabilityStillTightens(unittest.TestCase):
    def test_guard(self):
        opt = {"honor_shame": A(-0.3)}
        vul = Decision("q", [Option("a", "a", assessments=dict(opt))], stakeholders=[Stakeholder("child", True)])
        self.assertTrue(CollaborationEngine().deliberate(vul).analyses["a"].guards)


if __name__ == "__main__":
    unittest.main()
