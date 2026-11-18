"""Tests for eDNA Collaboration v1.1 — run with:  python -m unittest discover -s tests -v"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edna_collaboration import (AXES, PILLAR_ONE_KEYS, AcknowledgementRequired, AxisAssessment,  # noqa: E402
                                CollaborationEngine, CueInstrument, Decision, EngineLocked, HumanDecision,
                                InstrumentError, LLMInstrument, MoralLedger, Option, OutcomeFeedback, Posture,
                                Roster, Stakeholder, Strand, Thresholds, ZoneKind, render)
from edna_collaboration.axes import get_axis  # noqa: E402
from edna_collaboration.ensemble import Stance, read_option  # noqa: E402
from edna_collaboration.scenarios import SCENARIOS, news_drift_series  # noqa: E402


def run(name, **kw):
    decision, gen = SCENARIOS[name][1]()
    eng = CollaborationEngine(third_door=gen, **kw)
    return eng, eng.deliberate(decision)


def A(s, rel=0.8, conf=0.7):
    return AxisAssessment(s, rel, conf)


class TestPillarOne(unittest.TestCase):
    def test_nine_tensions_three_strands(self):
        self.assertEqual(len(PILLAR_ONE_KEYS), 9)
        for strand in (Strand.HEAD, Strand.HEART, Strand.HORIZON):
            self.assertEqual(sum(1 for k in PILLAR_ONE_KEYS if AXES[k].strand == strand), 3)

    def test_vices_at_both_ends(self):
        # Chapter 8: Power — Domination or Helplessness; Trust — Manipulation or Cowardice/Fear
        p = get_axis("power")
        self.assertEqual(p.zone_of(0.95).label, "Domination")
        self.assertEqual(p.zone_of(-0.95).label, "Helplessness")
        self.assertEqual(p.zone_of(0.2).kind, ZoneKind.HEALTHY)
        t = get_axis("trust_fear")
        self.assertEqual(t.zone_of(0.95).label, "Manipulation")
        self.assertEqual(t.zone_of(-0.9).kind, ZoneKind.DANGER)
        self.assertEqual(get_axis("good_evil").zone_of(0.95).label, "Self-righteousness")

    def test_bands_never_overlap(self):
        for a in AXES.values():
            for i in range(-100, 101):
                s = i / 100
                u, k = a.utility(s), a.zone_of(s).kind
                if k == ZoneKind.HEALTHY:
                    self.assertGreaterEqual(u, 0.6 - 1e-9)
                elif k == ZoneKind.DRIFT:
                    self.assertTrue(-0.6 - 1e-9 <= u <= -0.2 + 1e-9)
                elif k == ZoneKind.DANGER:
                    self.assertLessEqual(u, -0.7 + 1e-9)

    def test_utility_range_brackets_utility(self):
        for a in AXES.values():
            for s in (-0.9, -0.3, 0.0, 0.4, 0.8):
                lo, hi = a.utility_range(s - 0.2, s + 0.2)
                self.assertLessEqual(lo, a.utility(s) + 1e-9)
                self.assertGreaterEqual(hi, a.utility(s) - 1e-9)


class TestPillarTwo(unittest.TestCase):
    def test_seventeen_perspectives(self):
        r = Roster.default()
        fams = [p.family for p in r]
        self.assertEqual(len(r), 17)
        self.assertEqual(fams.count("philosophical"), 6)
        self.assertEqual(fams.count("cultural-religious"), 11)

    def test_roster_round_trip_and_fingerprint(self):
        r = Roster.default()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "roster.json")
            r.to_json(path)
            r2 = Roster.from_json(path)
        self.assertEqual(r.fingerprint(), r2.fingerprint())

    def test_tilt_only_on_balance_axes(self):
        from edna_collaboration.perspectives import Perspective
        with self.assertRaises(ValueError):
            Perspective("x", "X", "philosophical", "?", {"good_evil": 1}, {"good_evil": 0.2})

    def test_abstains_when_nothing_it_cares_about_is_engaged(self):
        o = Option("o", "o", assessments={"stewardship": A(0.5, rel=0.9)})
        er = read_option(o, o.assessments, Roster.default(), Thresholds(), {})
        existentialism = next(v for v in er.voices if v.key == "existentialism")
        self.assertEqual(existentialism.stance, Stance.ABSTAINS)


class TestNoAverage(unittest.TestCase):
    def test_no_single_overall_score_anywhere(self):
        _, d = run("elder_care")
        summary = json.dumps(d.summary())
        for banned in ('"score":', '"overall"', '"mean"', '"average"'):
            self.assertNotIn(banned, summary)
        for an in d.analyses.values():
            self.assertFalse(hasattr(an.ensemble, "mean"))


class TestBookScenarios(unittest.TestCase):
    def test_bank_third_door_on_the_table_proceeds(self):
        _, d = run("bank")
        self.assertEqual(d.posture, Posture.PROCEED)
        self.assertEqual(d.recommended, "hold_and_call")
        self.assertTrue(d.analyses["freeze"].guards)            # jealous space guards the vulnerable
        self.assertEqual(d.analyses["freeze"].danger.level, "soft_stop")

    def test_tri_lens_moderation(self):
        _, d = run("moderation")
        self.assertIn(d.posture, (Posture.PROCEED, Posture.PROCEED_WITH_DISCLOSURE))
        self.assertEqual(d.recommended, "warn")

    def test_elder_care_value_divergence_defers(self):
        _, d = run("elder_care")
        self.assertEqual(d.posture, Posture.DEFER_TO_HUMAN)
        al = d.analyses["assisted_living"].ensemble
        self.assertTrue(al.value_divergence)
        objectors = {v.key for v in al.by(Stance.OBJECTS)}
        self.assertTrue({"confucian_ren", "ubuntu"} & objectors)
        self.assertIn("existentialism", {v.key for v in al.by(Stance.SUPPORTS)})
        self.assertIsNotNone(d.third_door)                      # the brief is still handed over

    def test_hospital_third_door_needs_a_human(self):
        _, d = run("hospital")
        self.assertEqual(d.recommended, "phased_conversion")
        self.assertEqual(d.posture, Posture.DEFER_TO_HUMAN)     # I7
        self.assertEqual(d.analyses["phased_conversion"].option.origin, "third_door")
        self.assertIn("third_door", [a.code for a in d.analyses["phased_conversion"].acks])

    def test_urgency_pauses_and_offers(self):
        _, d = run("urgency")
        self.assertEqual(d.posture, Posture.OFFER_ALTERNATIVE)
        self.assertEqual(d.recommended, "value")
        self.assertIn("activates Fear", d.analyses["urgency"].danger.message)

    def test_review_grey_zone(self):
        _, d = run("review")
        self.assertEqual(d.posture, Posture.OFFER_ALTERNATIVE)
        self.assertTrue(d.analyses["blunt"].danger.grey_zone)
        # No clear violation (no exact reading in danger) ...
        self.assertFalse(d.analyses["blunt"].danger.nominal_soft_stop)
        # ... but since v1.3 the measurement range reaches the unhealthy end on two lenses at once.
        self.assertEqual(d.analyses["blunt"].danger.level, "soft_stop")
        self.assertEqual(set(d.analyses["blunt"].danger.possible), {"accuracy_intuition", "honor_shame"})

    def test_sustainability_values_override(self):
        _, d = run("sustainability")
        conflicts = d.analyses["single_use"].conflicts
        self.assertTrue(conflicts)
        self.assertIn("misalign with your Sustainability goals", conflicts[0].message())
        self.assertEqual(d.recommended, "recyclable")

    def test_drone_engages_lock_and_pauses_everything(self):
        eng, d = run("drone")
        self.assertEqual(d.posture, Posture.LOCKED)
        self.assertEqual(d.recommended, "hold")
        harmless = eng.deliberate(SCENARIOS["moderation"][1]()[0])
        self.assertEqual(harmless.posture, Posture.LOCKED)       # I8
        with self.assertRaises(EngineLocked):
            eng.resolve(d, HumanDecision("hold", "Reviewer R", "Reviewer", "hold"))
        eng.resolve(d, HumanDecision("hold", "Reviewer R", "Reviewer", "hold", release_lock=True,
                                     acknowledged=[a.code for a in d.analyses["hold"].acks]))
        self.assertIsNone(eng.lock)
        self.assertIn(eng.deliberate(SCENARIOS["moderation"][1]()[0]).posture,
                      (Posture.PROCEED, Posture.PROCEED_WITH_DISCLOSURE))

    def test_every_scenario_renders(self):
        for name in SCENARIOS:
            eng, d = run(name)
            text = render(d, eng.th)
            self.assertIn("What kind of world does this choice create?", text)
            self.assertIn("SEVENTEEN-PERSPECTIVE CHECK", text)
            self.assertIn("THROUGH THE ARCH", text)


class TestInvariants(unittest.TestCase):
    def test_thresholds_cannot_be_configured_into_a_noop(self):
        for bad in ({"divergence_share": 0.9}, {"convergence_share": 0.3}, {"min_voices": 1},
                    {"relevance_floor": 0.99}, {"danger_axes_soft_stop": 9}):
            with self.assertRaises(ValueError):
                Thresholds(**bad)

    def test_contested_act_always_defers_even_with_loosest_thresholds(self):
        decision, _ = SCENARIOS["elder_care"][1]()
        loose = Thresholds(divergence_share=0.4, convergence_share=0.6, support_cut=0.6)
        d = CollaborationEngine(thresholds=loose).deliberate(decision)
        self.assertNotIn(d.posture, (Posture.PROCEED, Posture.PROCEED_WITH_DISCLOSURE))

    def test_irreversible_critical_needs_a_human(self):
        good = {k: A(0.5) for k in ("good_evil", "trust_fear", "honor_shame", "thriving_surviving")}
        dec = Decision("q", [Option("a", "a", assessments=good, reversible=False)], mode="act",
                       stakes="critical", proposed_option="a")
        d = CollaborationEngine().deliberate(dec)
        self.assertEqual(d.posture, Posture.DEFER_TO_HUMAN)

    def test_demo_instrument_cannot_authorize_action(self):
        dec = Decision("q", [Option("a", "Support and protect the customer with respect and dignity")],
                       mode="act", proposed_option="a")
        d = CollaborationEngine(instrument=CueInstrument()).deliberate(dec)
        self.assertNotIn(d.posture, (Posture.PROCEED, Posture.PROCEED_WITH_DISCLOSURE))

    def test_instrument_failure_fails_closed(self):
        def broken(system, user):
            raise RuntimeError("network down")
        dec = Decision("q", [Option("a", "Do the thing")], mode="act", proposed_option="a")
        d = CollaborationEngine(instrument=LLMInstrument(broken)).deliberate(dec)
        self.assertEqual(d.posture, Posture.DEFER_TO_HUMAN)
        self.assertIn("a", d.instrument_errors)

    def test_vulnerable_stakeholder_tightens_jealous_space(self):
        opt = {"honor_shame": A(-0.3)}                          # drift, not danger
        plain = Decision("q", [Option("a", "a", assessments=dict(opt))])
        vul = Decision("q", [Option("a", "a", assessments=dict(opt))],
                       stakeholders=[Stakeholder("child", vulnerable=True)])
        e = CollaborationEngine()
        self.assertFalse(e.deliberate(plain).analyses["a"].guards)
        self.assertTrue(e.deliberate(vul).analyses["a"].guards)

    def test_learning_never_changes_weights(self):
        eng, d = run("bank")
        before = eng.roster.fingerprint()
        eng.feedback(OutcomeFeedback(d.id, {"trust_fear": -0.7}))
        self.assertEqual(before, eng.roster.fingerprint())
        self.assertGreater(eng.memory.margin_bonus("trust_fear"), 0)


class TestCollaboration(unittest.TestCase):
    def test_choice_through_a_warning_requires_acknowledgement(self):
        eng, d = run("bank")
        with self.assertRaises(AcknowledgementRequired) as cm:
            eng.resolve(d, HumanDecision("freeze", "Pat Lee", "Operator", "fraud is certain"))
        codes = {a.code for a in cm.exception.missing}
        self.assertIn("soft_stop", codes)
        self.assertTrue(any(c.startswith("jealous_space:") for c in codes))
        res = eng.resolve(d, HumanDecision("freeze", "Pat Lee", "Operator", "fraud is certain",
                                           acknowledged=sorted(codes)))
        self.assertTrue(res.overrode_warnings)
        self.assertIn("power", res.willful_tradeoffs)

    def test_human_decision_needs_name_and_rationale(self):
        with self.assertRaises(ValueError):
            HumanDecision("a", " ", "Reviewer", "why")
        with self.assertRaises(ValueError):
            HumanDecision("a", "Name", "Reviewer", "")

    def test_feedback_produces_lessons_and_precedents(self):
        eng, d = run("bank")
        lessons = eng.feedback(OutcomeFeedback(d.id, {"trust_fear": -0.7}, notes="She felt betrayed."))
        self.assertTrue(any("Trust–Fear" in l for l in lessons))
        d2 = eng.deliberate(SCENARIOS["bank"][1]()[0])
        self.assertTrue(d2.precedents)

    def test_run_guarded_only_acts_when_authorized(self):
        calls = []
        eng = CollaborationEngine()
        d, out = eng.run_guarded(SCENARIOS["bank"][1]()[0], lambda o: calls.append(o.id) or "done")
        self.assertEqual(calls, ["hold_and_call"])
        d, out = eng.run_guarded(SCENARIOS["elder_care"][1]()[0], lambda o: calls.append(o.id))
        self.assertIsNone(out)
        self.assertEqual(calls, ["hold_and_call"])


class TestLedger(unittest.TestCase):
    def test_hash_chain_detects_tampering_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.jsonl")
            eng = CollaborationEngine(ledger=MoralLedger(path))
            eng.deliberate(SCENARIOS["bank"][1]()[0])
            eng.deliberate(SCENARIOS["urgency"][1]()[0])
            reloaded = MoralLedger(path)
            self.assertEqual(reloaded.verify(), (True, None))
            reloaded.entries[0]["payload"]["posture"] = "SOMETHING ELSE"
            ok, bad = reloaded.verify()
            self.assertFalse(ok)
            self.assertEqual(bad, 0)


class TestDrift(unittest.TestCase):
    def test_slow_slide_toward_fear_and_override_normalization(self):
        eng = CollaborationEngine()
        kinds = set()
        for dec in news_drift_series():
            d = eng.deliberate(dec)
            alerts = list(d.drift_alerts)
            if d.needs_human:
                res = eng.resolve(d, HumanDecision("mix", "Ops", "Operator", "target",
                                                   acknowledged=[a.code for a in d.analyses["mix"].acks]))
                alerts += res.drift_alerts
            kinds |= {(a.kind, a.axis) for a in alerts}
        self.assertIn(("axis", "trust_fear"), kinds)
        self.assertIn(("override", ""), kinds)


class TestInstruments(unittest.TestCase):
    def test_llm_instrument_parses_and_validates(self):
        def fake(system, user):
            self.assertIn("Measure the choice, not the topic", system)
            return 'Sure: {"assessments": {"trust_fear": {"score": 0.4, "relevance": 0.8, ' \
                   '"confidence": 0.6, "rationale": "honest"}}}'
        out = LLMInstrument(fake).assess(Decision("q", [Option("a", "a")]), Option("a", "a"))
        self.assertAlmostEqual(out["trust_fear"].score, 0.4)

    def test_llm_instrument_rejects_garbage(self):
        for bad in ("no json here", '{"assessments": {"nonsense_axis": {"score": 0.1}}}',
                    '{"assessments": {"trust_fear": {"score": 7}}}'):
            with self.assertRaises(InstrumentError):
                LLMInstrument(lambda s, u, b=bad: b).assess(Decision("q", [Option("a", "a")]), Option("a", "a"))

    def test_cue_instrument_scores_the_choice_not_the_topic(self):
        reporter = Option("r", "Inform her that the account shows signs of fraud and explain her options")
        out = CueInstrument().assess(Decision("q", [reporter]), reporter)
        self.assertFalse(any(a.score < 0 for a in out.values()), out)
        pusher = Option("p", "Only 2 left — act now!")
        out = CueInstrument().assess(Decision("q", [pusher]), pusher)
        self.assertLess(out["trust_fear"].score, -0.5)


if __name__ == "__main__":
    unittest.main()
