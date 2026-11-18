"""v1.3 tests: the Ethical Danger Zone reads each axis's whole measurement range.

Run with:  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edna_collaboration import (AxisAssessment, CollaborationEngine, Decision, HumanDecision,  # noqa: E402
                                Option, Posture, Thresholds)
from edna_collaboration.scenarios import SCENARIOS  # noqa: E402


def dz(tf, mm, conf=0.7, **dec_kw):
    dec = Decision("probe", [Option("a", "a", reversible=dec_kw.pop("reversible", True), assessments={
        "trust_fear": AxisAssessment(tf, 0.8, conf), "meaningful_meaningless": AxisAssessment(mm, 0.8, conf)})],
        **dec_kw)
    eng = CollaborationEngine()
    return eng, eng.deliberate(dec)


class TestDangerZoneReadsTheRange(unittest.TestCase):
    def test_far_from_the_line_stays_out(self):
        _, d = dz(-0.30, -0.20)
        self.assertEqual(d.analyses["a"].danger.level, "none")

    def test_a_hair_short_of_the_line_no_longer_slips_past(self):
        # Danger lines: Trust–Fear below -0.55, Meaningful–Meaningless below -0.50. v1.2 said "none" here.
        _, d = dz(-0.53, -0.48)
        rep = d.analyses["a"].danger
        self.assertEqual(rep.level, "soft_stop")
        self.assertFalse(rep.nominal_soft_stop)
        self.assertEqual(set(rep.possible), {"trust_fear", "meaningful_meaningless"})
        self.assertIn("(possibly)", rep.message)
        self.assertIn("Do you wish to continue?", rep.message)

    def test_over_the_line_is_a_plain_soft_stop(self):
        _, d = dz(-0.56, -0.51)
        rep = d.analyses["a"].danger
        self.assertEqual(rep.level, "soft_stop")
        self.assertTrue(rep.nominal_soft_stop)
        self.assertEqual(rep.possible, [])

    def test_single_axis_near_the_line_is_a_may_warning(self):
        _, d = dz(-0.53, 0.40)
        rep = d.analyses["a"].danger
        self.assertEqual(rep.level, "caution")
        self.assertIn("may activate Fear", rep.message)

    def test_possible_soft_stop_still_needs_a_human(self):
        eng, d = dz(-0.53, -0.48, mode="act")
        self.assertIn("soft_stop", [a.code for a in d.analyses["a"].acks])
        self.assertNotIn(d.posture, (Posture.PROCEED, Posture.PROCEED_WITH_DISCLOSURE))
        res = eng.resolve(d, HumanDecision("a", "R", "Reviewer", "reviewed",
                                           acknowledged=[a.code for a in d.analyses["a"].acks]))
        self.assertTrue(res.overrode_warnings)

    def test_lock_still_uses_exact_readings_only(self):
        # Irreversible, critical, murky (confidence 0.3) — but nothing is actually in danger.
        eng, d = dz(-0.53, -0.48, conf=0.3, mode="act", stakes="critical", reversible=False,
                    proposed_option="a")
        self.assertEqual(d.analyses["a"].danger.level, "soft_stop")
        self.assertIsNone(eng.lock)
        self.assertNotEqual(d.posture, Posture.LOCKED)

    def test_threshold_is_shared_and_governed(self):
        eng = CollaborationEngine()
        rev = eng.foundation.propose("thresholds", {"guard_exposure": 0.5}, "Exact-value behaviour",
                                     "Comparison run", "M. Chen", "Policymaker")
        eng.foundation.approve(rev.id, "A", "Reviewer")
        eng.foundation.approve(rev.id, "B", "Reviewer")
        eng.foundation.apply(rev.id, "M. Chen", "Policymaker")
        dec = Decision("probe", [Option("a", "a", assessments={
            "trust_fear": AxisAssessment(-0.53, 0.8, 0.7), "meaningful_meaningless": AxisAssessment(-0.48, 0.8, 0.7)})])
        self.assertEqual(eng.deliberate(dec).analyses["a"].danger.level, "none")
        with self.assertRaises(ValueError):
            Thresholds(guard_exposure=0.55)

    def test_grey_zone_and_danger_zone_can_both_be_true(self):
        # Ch. 8's brutally honest review: no clear violation (grey) — yet near the line on two lenses.
        _, d = (lambda dec: (None, CollaborationEngine().deliberate(dec)))(SCENARIOS["review"][1]()[0])
        rep = d.analyses["blunt"].danger
        self.assertTrue(rep.grey_zone)
        self.assertIn("Within measurement error", rep.grey_message)
        self.assertEqual(rep.level, "soft_stop")

    def test_book_scenarios_keep_their_postures(self):
        expected = {"bank": Posture.PROCEED, "moderation": Posture.PROCEED, "elder_care": Posture.DEFER_TO_HUMAN,
                    "maid": Posture.DEFER_TO_HUMAN, "hospital": Posture.DEFER_TO_HUMAN,
                    "urgency": Posture.OFFER_ALTERNATIVE, "review": Posture.OFFER_ALTERNATIVE,
                    "sustainability": Posture.OFFER_ALTERNATIVE, "drone": Posture.LOCKED}
        for name, posture in expected.items():
            decision, gen = SCENARIOS[name][1]()
            self.assertEqual(CollaborationEngine(third_door=gen).deliberate(decision).posture, posture, name)


if __name__ == "__main__":
    unittest.main()
