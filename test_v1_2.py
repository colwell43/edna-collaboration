"""v1.2 tests: protections read the whole measurement range, not one exact value.

Run with:  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edna_collaboration import (AxisAssessment, CollaborationEngine, Decision, DeclaredValue,  # noqa: E402
                                HumanDecision, Option, OutcomeFeedback, Posture, Stakeholder, Thresholds)
from edna_collaboration.scenarios import SCENARIOS  # noqa: E402


def guards_for(axis, pos, conf=0.7, vulnerable=True, engine=None):
    dec = Decision("probe", [Option("a", "a", assessments={axis: AxisAssessment(pos, 0.8, conf)})],
                   stakeholders=[Stakeholder("x", vulnerable)])
    return (engine or CollaborationEngine()).deliberate(dec).analyses["a"].guards


class TestGuardsReadTheRange(unittest.TestCase):
    def test_boundary_no_longer_a_knife_edge(self):
        # Power drift (Domination) starts at +0.50; margin at confidence 0.7 is about 0.2.
        self.assertEqual(guards_for("power", 0.40), [])
        g45, g49, g50 = guards_for("power", 0.45), guards_for("power", 0.49), guards_for("power", 0.50)
        self.assertEqual(g45[0].certainty, "possible")       # v1.1 missed this: exact value was healthy
        self.assertEqual(g49[0].certainty, "possible")
        self.assertEqual(g50[0].certainty, "likely")
        self.assertLess(g45[0].exposure, g49[0].exposure)
        self.assertLessEqual(g49[0].exposure, g50[0].exposure)

    def test_exposure_rises_monotonically_toward_the_zone(self):
        last = -1.0
        for p in (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80, 0.95):
            g = guards_for("power", p)
            e = g[0].exposure if g else 0.0
            self.assertGreaterEqual(e + 1e-9, last, p)
            last = e

    def test_whole_range_inside_is_certain(self):
        g = guards_for("power", 0.95, conf=0.9)
        self.assertEqual(g[0].certainty, "certain")
        self.assertEqual(g[0].kind, "danger")

    def test_deep_in_the_healthy_band_stays_clear_even_with_wide_margins(self):
        self.assertEqual(guards_for("power", 0.2, conf=0.3), [])

    def test_without_vulnerability_only_danger_is_guarded(self):
        self.assertEqual(guards_for("power", 0.55, vulnerable=False), [])      # drift, not guarded
        g = guards_for("power", 0.70, vulnerable=False)                         # range reaches danger
        self.assertEqual((g[0].certainty, g[0].kind, g[0].tightened), ("possible", "danger", False))

    def test_tightened_only_when_vulnerability_is_the_reason(self):
        self.assertTrue(guards_for("power", 0.55)[0].tightened)                 # drift only
        self.assertFalse(guards_for("power", 0.80)[0].tightened)                # danger fires anyway

    def test_possible_breach_still_needs_a_human(self):
        dec = Decision("probe", [Option("a", "a", assessments={
            "power": AxisAssessment(0.45, 0.8, 0.7), "good_evil": AxisAssessment(0.6, 0.8, 0.7),
            "trust_fear": AxisAssessment(0.5, 0.8, 0.7), "honor_shame": AxisAssessment(0.5, 0.8, 0.7)})],
            mode="act", stakeholders=[Stakeholder("x", True)])
        eng = CollaborationEngine()
        d = eng.deliberate(dec)
        self.assertNotIn(d.posture, (Posture.PROCEED, Posture.PROCEED_WITH_DISCLOSURE))
        self.assertIn("jealous_space:power", [a.code for a in d.analyses["a"].acks])
        self.assertIn("benefit of the doubt", d.analyses["a"].acks[0].message)

    def test_humility_learned_from_feedback_makes_guards_more_protective(self):
        eng = CollaborationEngine()
        self.assertEqual(guards_for("trust_fear", -0.05, engine=eng), [])
        d = eng.deliberate(SCENARIOS["bank"][1]()[0])          # predicted trust +0.5 ...
        eng.feedback(OutcomeFeedback(d.id, {"trust_fear": -0.7}))   # ... observed -0.7: margin widens
        g = guards_for("trust_fear", -0.05, engine=eng)
        self.assertEqual(g[0].certainty, "possible")

    def test_lock_still_counts_only_readings_actually_in_danger(self):
        eng, d = CollaborationEngine(), None
        d = eng.deliberate(SCENARIOS["drone"][1]()[0])
        self.assertEqual(d.posture, Posture.LOCKED)
        self.assertTrue(all(g.nominal_danger for g in d.analyses["strike"].guards))


class TestValuesCheckReadsTheRange(unittest.TestCase):
    def _conflicts(self, pos):
        dec = Decision("probe", [Option("a", "a", assessments={"stewardship": AxisAssessment(pos, 0.9, 0.7)})],
                       declared_values=[DeclaredValue("Sustainability", "promise", {"stewardship": 0.0})])
        return CollaborationEngine().deliberate(dec).analyses["a"].conflicts

    def test_floor_is_not_a_knife_edge(self):
        self.assertEqual(self._conflicts(0.20), [])
        self.assertEqual(self._conflicts(0.05)[0].certainty, "possible")
        self.assertEqual(self._conflicts(-0.05)[0].certainty, "likely")
        self.assertEqual(self._conflicts(-0.6)[0].certainty, "certain")
        self.assertIn("may conflict", self._conflicts(0.05)[0].message())


class TestGuardThresholdIsGoverned(unittest.TestCase):
    def test_bounds(self):
        with self.assertRaises(ValueError):
            Thresholds(guard_exposure=0.6)       # would be less protective than the exact value
        with self.assertRaises(ValueError):
            Thresholds(guard_exposure=0.1)       # hair trigger
        Thresholds(guard_exposure=0.5)

    def test_changed_only_through_the_foundation(self):
        eng = CollaborationEngine()
        rev = eng.foundation.propose("thresholds", {"guard_exposure": 0.25}, "More precaution",
                                     "Vulnerable users", "M. Chen", "Policymaker")
        eng.foundation.approve(rev.id, "A", "Reviewer")
        eng.foundation.approve(rev.id, "B", "Reviewer")
        eng.foundation.apply(rev.id, "M. Chen", "Policymaker")
        self.assertEqual(eng.th.guard_exposure, 0.25)
        self.assertEqual(guards_for("power", 0.40, engine=eng)[0].certainty, "possible")

    def test_resolution_with_possible_breach_is_recorded_as_override(self):
        dec = Decision("probe", [Option("a", "a", assessments={"power": AxisAssessment(0.45, 0.8, 0.7)})],
                       mode="act", stakeholders=[Stakeholder("x", True)])
        eng = CollaborationEngine()
        d = eng.deliberate(dec)
        res = eng.resolve(d, HumanDecision("a", "R", "Reviewer", "reviewed",
                                           acknowledged=[a.code for a in d.analyses["a"].acks]))
        self.assertTrue(res.overrode_warnings)
        self.assertEqual(eng.ledger.verify(), (True, None))


if __name__ == "__main__":
    unittest.main()
