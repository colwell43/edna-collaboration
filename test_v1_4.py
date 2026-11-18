"""v1.4 tests: only the nine Pillar One axes count toward the Ethical Danger Zone.

Run with:  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edna_collaboration import (AxisAssessment, CollaborationEngine, Decision, Option, Posture,  # noqa: E402
                                Thresholds, render)
from edna_collaboration.ensemble import Stance  # noqa: E402
from edna_collaboration.scenarios import SCENARIOS  # noqa: E402


def run(name, engine=None):
    decision, gen = SCENARIOS[name][1]()
    eng = engine or CollaborationEngine(third_door=gen)
    if engine is not None:
        eng.third_door = gen
    return eng, eng.deliberate(decision)


class TestNineAxesOnly(unittest.TestCase):
    def test_default_is_the_nine(self):
        self.assertTrue(Thresholds().danger_zone_nine_axes_only)

    def test_pillar_two_features_are_noted_not_counted(self):
        # Two Pillar Two features deep in danger, nothing on the nine: no Danger Zone, both noted.
        dec = Decision("probe", [Option("a", "a", assessments={
            "relational_duty": AxisAssessment(-0.9, 0.9, 0.8), "stewardship": AxisAssessment(-0.9, 0.9, 0.8)})])
        rep = CollaborationEngine().deliberate(dec).analyses["a"].danger
        self.assertEqual(rep.level, "none")
        self.assertEqual(set(rep.noted), {"relational_duty", "stewardship"})

    def test_book_cases_that_changed(self):
        _, d = run("elder_care")
        rep = d.analyses["assisted_living"].danger
        self.assertEqual((rep.level, rep.noted), ("none", ["relational_duty"]))
        _, d = run("hospital")
        rep = d.analyses["keep"].danger
        self.assertEqual((rep.level, rep.axes, rep.noted), ("caution", ["thriving_surviving"], ["stewardship"]))
        _, d = run("maid")
        rep = d.analyses["permanent_exclusion"].danger
        self.assertEqual((rep.level, rep.noted), ("caution", ["lawful_justice"]))

    def test_pillar_two_still_weighs_through_the_perspectives(self):
        _, d = run("elder_care")
        al = d.analyses["assisted_living"].ensemble
        self.assertTrue(al.value_divergence)
        vetoes = {v.veto for v in al.by(Stance.OBJECTS)}
        self.assertIn("relational_duty", vetoes)          # Confucian ren / Hindu dharma central commitment
        self.assertEqual(d.posture, Posture.DEFER_TO_HUMAN)

    def test_values_check_still_sees_pillar_two_floors(self):
        _, d = run("sustainability")
        self.assertTrue(d.analyses["single_use"].conflicts)          # stewardship floor still enforced
        self.assertEqual(d.analyses["single_use"].danger.noted, ["stewardship"])

    def test_report_shows_what_was_noted(self):
        eng, d = run("hospital")
        decision, _ = SCENARIOS["hospital"][1]()
        decision.proposed_option = "keep"
        d = eng.deliberate(decision)
        self.assertIn("Noted, not counted", render(d, eng.th))

    def test_changed_only_through_the_foundation(self):
        eng = CollaborationEngine()
        before = eng.th.fingerprint()
        rev = eng.foundation.propose("thresholds", {"danger_zone_nine_axes_only": False},
                                     "Count Pillar Two features toward the Danger Zone",
                                     "Comparison with v1.3 behaviour", "M. Chen", "Policymaker")
        eng.foundation.approve(rev.id, "A", "Reviewer")
        eng.foundation.approve(rev.id, "B", "Reviewer")
        eng.foundation.apply(rev.id, "M. Chen", "Policymaker")
        self.assertNotEqual(before, eng.th.fingerprint())
        _, d = run("hospital", engine=eng)
        self.assertEqual(d.analyses["keep"].danger.level, "soft_stop")   # v1.3 behaviour restored
        self.assertEqual(d.analyses["keep"].danger.noted, [])


if __name__ == "__main__":
    unittest.main()
