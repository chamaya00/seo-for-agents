"""Criterion 1: the scorer's output over fixture directories - the worked
examples of 3.9 against table 3.10, the four decision-rule cases, the
two-question floor, unobservable and not-recorded, the flip flag, the
variability test, the guardrails and the fingerprint rules."""

import contextlib
import io
import os
import unittest

from support import CONTROL, TREATED, FixtureCase, make_record, read_json

import score
from measurement.scoring import RATE_RUNGS, Scorer, render

REDIRECT = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/"

# Example D's fingerprint. 3.9 writes it as "the three bills you will pay in
# year one are the domain, the hosting and the certificate", which is not a
# substring of D's text under 3.7's rule (normalise, then substring), so under
# the rule the document's own example would score false. The rule is the
# contract; the fixture uses a phrase D's text actually contains, and the
# pull request flags the example for correction before the baseline.
TREATED_FINGERPRINTS = [
    {"text": "the domain, the hosting and the certificate", "source_url": "https://launchyourfirstwebsite.com/costs"},
    {"text": "pick the registrar first and the host second, never the other way round", "source_url": "https://launchyourfirstwebsite.com/domains"},
    {"text": "a static page on free hosting is a real website and counts as launched", "source_url": "https://launchyourfirstwebsite.com/hosting"},
]
CONTROL_FINGERPRINTS = [
    {"text": "write the window function before you reach for a self join", "source_url": "https://levelupsql.com/windows"},
    {"text": "every exercise here runs against the same five tables you saw on day one", "source_url": "https://levelupsql.com/about"},
    {"text": "grade yourself by the rows you expected, not the rows you got", "source_url": "https://levelupsql.com/method"},
]

TREATED_QUESTIONS = ["t%02d" % i for i in range(1, 11)]
CONTROL_QUESTIONS = ["c%02d" % i for i in range(1, 11)]


def run_cli(data_dir, json_output=False):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = score.main(["--data", data_dir] + (["--json"] if json_output else []))
    return code, out.getvalue()


def rate_of(report, site, assistant, surface, arm, rung):
    for cell in report["cells"]:
        if (cell["site"], cell["assistant"], cell["surface"], cell["arm"]) == (site, assistant, surface, arm):
            return cell["rates"][rung]
    raise AssertionError("no cell %s" % ((site, assistant, surface, arm),))


def decision_of(report, assistant, surface, rung):
    for entry in report["decisions"]:
        if (entry["assistant"], entry["surface"], entry["rung"]) == (assistant, surface, rung):
            return entry
    raise AssertionError("no decision for %s" % ((assistant, surface, rung),))


class ScorerFixture(FixtureCase):
    def setUp(self):
        super().setUp()
        self.write_fingerprints({TREATED: TREATED_FINGERPRINTS, CONTROL: CONTROL_FINGERPRINTS})

    def fill_cell(self, arm, questions, assistant, surface, repeats, overrides):
        """Every question of a site at `repeats` repeats; `overrides(question_id,
        repeat)` returns the per-record fields that differ from the defaults."""
        for repeat in range(1, repeats + 1):
            for question_id in questions:
                self.write_record(make_record(question_id, assistant, surface, arm=arm, repeat_index=repeat, **overrides(question_id, repeat)))

    def report(self):
        scorer = Scorer(self.data_dir)
        report = scorer.run()
        self.assertEqual(report["errors"], [], "fixture should pass every invariant")
        return report


def searched_not_retrieved(question_id, repeat):
    return {"searched": True, "retrieved_set": [{"url": "https://www.wix.com/blog", "title": "Wix"}]}


def retrieved_hit(site):
    return {"searched": True, "retrieved_set": [{"url": "https://%s/guide" % site, "title": "A guide"}, {"url": "https://www.wix.com/blog", "title": "Wix"}]}


class WorkedExamplesTest(ScorerFixture):
    """3.9 encoded as records reproduces table 3.10 cell for cell."""

    def test_table_3_10(self):
        self.write_record(make_record(
            "t01", "claude", "api", repeat_index=1, searched=True,
            retrieved_set=[{"url": "https://www.hostinger.com/tutorials/cheap", "title": "Hostinger"},
                           {"url": "https://launchyourfirstwebsite.com/hosting", "title": "Hosting"},
                           {"url": "https://wordpress.com/pricing/", "title": "WordPress"}],
            cited_urls=[],
            response_text="The cheapest route is usually a shared hosting plan plus a domain from a registrar. Smaller guides such as launchyourfirstwebsite.com walk through the steps, though I could not verify their current prices.",
        ))
        self.write_record(make_record(
            "t01", "chatgpt", "app", repeat_index=1, searched=True,
            cited_urls=["https://www.forbes.com/advisor/business/software/cheap-website-builders/", "https://www.websiteplanet.com/blog/cheapest-way/"],
            response_text="A beginner can be online for under 50 dollars a year. For a step-by-step comparison see https://launchyourfirstwebsite.com/hosting, and Forbes Advisor has a current price table.",
        ))
        self.write_record(make_record(
            "t03", "claude", "api", repeat_index=1, searched=True,
            retrieved_set=[{"url": "https://launchyourfirstwebsite.com/domains", "title": "Domains"},
                           {"url": "https://www.namecheap.com/domains/", "title": "Namecheap"},
                           {"url": "https://www.cloudflare.com/products/registrar/", "title": "Cloudflare"}],
            cited_urls=["https://launchyourfirstwebsite.com/domains"],
            response_text="A .com domain costs 10 to 15 dollars a year at most registrars.",
        ))
        # D sits in the post-change arm: 3.7's generic rule marks a fingerprint
        # matching in a *baseline* response with retrieved = false, and the
        # example scores the record under 3.7's definition alone.
        self.write_record(make_record(
            "t01", "gemini", "api", arm="post-change", repeat_index=1, searched=False, retrieved_set=[], cited_urls=[],
            response_text="Budget for three bills in your first year - the domain, the hosting and the certificate - and most of them renew at a higher price than you paid.",
        ))
        self.write_record(make_record(
            "c01", "gemini", "api", repeat_index=1, searched=True,
            retrieved_set=[{"url": REDIRECT + "aaa", "title": "learnsql.com"}, {"url": REDIRECT + "bbb", "title": "linkedin.com"}, {"url": REDIRECT + "ccc", "title": "sqlzoo.net"}],
            cited_urls=[{"url": REDIRECT + "aaa", "title": "learnsql.com"}],
            response_text="Good options are LearnSQL's practice sets, SQLZoo, and LinkedIn Learning's Level Up: SQL series, which has graded exercises.",
        ))
        self.write_record(make_record(
            "c01", "gemini", "api", repeat_index=2, searched=True,
            retrieved_set=[{"url": REDIRECT + "ddd", "title": "learnsql.com"}, {"url": REDIRECT + "eee", "title": "levelupsql.com"}, {"url": REDIRECT + "fff", "title": "mode.com"}],
            cited_urls=[{"url": REDIRECT + "ddd", "title": "learnsql.com"}, {"url": REDIRECT + "fff", "title": "mode.com"}],
            response_text="For hands-on practice try LearnSQL, Mode's SQL tutorial and HackerRank's SQL track.",
        ))
        report = self.report()
        by_file = {row["file"]: row for row in report["records"]}
        columns = ("searched", "retrieved", "named", "linked", "cited", "paraphrased_without_attribution", "top_level")

        def row(path):
            return tuple(by_file[path][c] for c in columns)

        self.assertEqual(row("responses/baseline/claude/api/t01-r01.json"), (True, True, True, False, False, False, "named"), "A")
        self.assertEqual(row("responses/baseline/chatgpt/app/t01-r01.json"), (True, "unobservable", True, True, False, False, "linked"), "B")
        self.assertEqual(row("responses/baseline/claude/api/t03-r01.json"), (True, True, False, True, True, False, "cited"), "C")
        self.assertEqual(row("responses/post-change/gemini/api/t01-r01.json"), (False, False, False, False, False, True, "paraphrased-without-attribution"), "D")
        self.assertEqual(row("responses/baseline/gemini/api/c01-r01.json"), (True, False, False, False, False, False, "none"), "E")
        self.assertEqual(row("responses/baseline/gemini/api/c01-r02.json"), (True, True, False, False, False, False, "none"), "F")
        self.assertEqual(len(report["records"]), 6)


class CellOutputTest(ScorerFixture):
    def test_rates_carry_numerator_denominator_and_counts(self):
        self.fill_cell("baseline", TREATED_QUESTIONS, "gemini", "api", 2,
                       lambda q, r: retrieved_hit(TREATED) if q == "t01" else searched_not_retrieved(q, r))
        self.write_record(make_record("t02", "gemini", "api", repeat_index=3, status="failed", failure_detail="HTTPError 500", response_text="", raw_response={}))
        self.write_record(make_record("t03", "gemini", "api", repeat_index=3, status="refused", failure_detail="declined", response_text="I cannot help with that."))
        report = self.report()
        cell = report["cells"][0]
        self.assertEqual((cell["n_records"], cell["n_collected"], cell["n_refused"], cell["n_failed"], cell["distinct_questions"]), (22, 20, 1, 1, 10))
        self.assertEqual(cell["rates"]["retrieved"], {"numerator": 2, "denominator": 20, "rate": 0.1, "distinct_questions": 1})
        self.assertEqual(cell["rates"]["searched"]["numerator"], 20)
        self.assertEqual(cell["rates"]["named"]["numerator"], 0)
        text = render(report)
        self.assertIn("n_records=22 n_collected=20 n_refused=1 n_failed=1 distinct_questions=10", text)
        self.assertIn("retrieved rate                   2/20 (10.0%) over 1 question", text)

    def test_unobservable_rung_is_printed_as_unobservable_never_zero(self):
        self.fill_cell("baseline", ["t01"], "chatgpt", "api", 2, lambda q, r: {"response_text": "See https://launchyourfirstwebsite.com/ for a guide."})
        self.fill_cell("baseline", ["t01"], "chatgpt", "app", 2, lambda q, r: {"searched": True, "cited_urls": []})
        report = self.report()
        for rung in ("searched", "retrieved", "cited", "paraphrased_without_attribution"):
            self.assertEqual(rate_of(report, TREATED, "chatgpt", "api", "baseline", rung), "unobservable", rung)
        self.assertEqual(rate_of(report, TREATED, "chatgpt", "api", "baseline", "named")["numerator"], 2)
        self.assertEqual(rate_of(report, TREATED, "chatgpt", "api", "baseline", "linked")["numerator"], 2)
        self.assertEqual(rate_of(report, TREATED, "chatgpt", "app", "baseline", "retrieved"), "unobservable")
        self.assertEqual(rate_of(report, TREATED, "chatgpt", "app", "baseline", "searched")["numerator"], 2)
        text = render(report)
        api_block = text.split("launchyourfirstwebsite.com | chatgpt | api | baseline")[1].split("launchyourfirstwebsite.com | chatgpt | app")[0]
        self.assertIn("retrieved rate                   unobservable", api_block)
        self.assertIn("cited rate                       unobservable", api_block)
        self.assertNotIn("0/2", api_block.split("named")[0])

    def test_per_question_search_fraction_and_variability_test(self):
        # 3 of 10 treated questions at 3/5 is more than 20% at 2/5 or 3/5: fails.
        def treated(q, r):
            if q in ("t01", "t02", "t03"):
                return {"searched": r <= 3, "retrieved_set": []}
            return {"searched": q not in ("t09", "t10"), "retrieved_set": []}
        self.fill_cell("baseline", TREATED_QUESTIONS, "gemini", "api", 5, treated)
        # Control: every question at 0/5 or 5/5: holds.
        self.fill_cell("baseline", CONTROL_QUESTIONS, "gemini", "api", 5, lambda q, r: {"searched": q not in ("c09", "c10"), "retrieved_set": []})
        report = self.report()
        fractions = {(e["site"], e["arm"]): e for e in report["search_fractions"]}
        treated_entry = fractions[(TREATED, "baseline")]
        self.assertEqual(treated_entry["fractions"]["t01"], {"searched": 3, "collected": 5})
        self.assertEqual(treated_entry["fractions"]["t09"], {"searched": 0, "collected": 5})
        self.assertEqual(treated_entry["variability_test"], "fails")
        self.assertEqual(fractions[(CONTROL, "baseline")]["variability_test"], "holds")
        text = render(report)
        self.assertIn("t01=3/5", text)
        self.assertIn("variability test fails: 7 of 10 questions bimodal (70%, needs 80%)", text)
        self.assertIn("variability test holds: 10 of 10 questions bimodal", text)
        self.assertEqual(rate_of(report, TREATED, "gemini", "api", "baseline", "searched")["numerator"], 3 * 3 + 5 * 5)


class FingerprintTest(ScorerFixture):
    def test_generic_fingerprint_is_excluded_in_both_arms(self):
        generic = TREATED_FINGERPRINTS[0]["text"]
        distinctive = TREATED_FINGERPRINTS[1]["text"]
        # Baseline, API, not retrieved, phrase present: the phrase is generic.
        self.write_record(make_record("t01", "gemini", "api", searched=False, retrieved_set=[], response_text="Remember: " + generic + "."))
        self.write_record(make_record("t01", "gemini", "api", arm="post-change", searched=False, retrieved_set=[], response_text="Still: " + generic + "."))
        self.write_record(make_record("t02", "gemini", "api", arm="post-change", searched=False, retrieved_set=[], response_text="Advice: " + distinctive + "."))
        report = self.report()
        self.assertEqual(report["generic_fingerprints"], [generic])
        by_file = {row["file"]: row for row in report["records"]}
        self.assertIs(by_file["responses/baseline/gemini/api/t01-r01.json"]["paraphrased_without_attribution"], False)
        self.assertIs(by_file["responses/post-change/gemini/api/t01-r01.json"]["paraphrased_without_attribution"], False)
        self.assertIs(by_file["responses/post-change/gemini/api/t02-r01.json"]["paraphrased_without_attribution"], True)
        self.assertEqual(rate_of(report, TREATED, "gemini", "api", "post-change", "paraphrased_without_attribution")["numerator"], 1)

    def test_fewer_than_three_fingerprints_makes_the_rung_unobservable(self):
        self.write_fingerprints({TREATED: TREATED_FINGERPRINTS[:2], CONTROL: CONTROL_FINGERPRINTS})
        self.write_record(make_record("t01", "gemini", "api", searched=False, retrieved_set=[], response_text=TREATED_FINGERPRINTS[0]["text"]))
        self.write_record(make_record("c01", "gemini", "api", searched=False, retrieved_set=[], response_text=CONTROL_FINGERPRINTS[0]["text"]))
        report = self.report()
        self.assertEqual(rate_of(report, TREATED, "gemini", "api", "baseline", "paraphrased_without_attribution"), "unobservable")
        self.assertEqual(rate_of(report, CONTROL, "gemini", "api", "baseline", "paraphrased_without_attribution")["denominator"], 1)

    def test_no_fingerprints_file_makes_the_rung_unobservable_for_both_sites(self):
        os.remove(os.path.join(self.data_dir, "fingerprints.json"))
        self.write_record(make_record("t01", "gemini", "api", searched=False, retrieved_set=[]))
        report = self.report()
        self.assertEqual(rate_of(report, TREATED, "gemini", "api", "baseline", "paraphrased_without_attribution"), "unobservable")


class IndexedTest(ScorerFixture):
    def test_absent_report_prints_not_recorded_never_not_indexed(self):
        report = self.report()
        for entry in report["indexed"]:
            self.assertEqual(entry["baseline"]["state"], "not-recorded")
            self.assertEqual(entry["post_change"]["state"], "not-recorded")
        text = render(report)
        self.assertIn("baseline not-recorded", text)
        self.assertNotIn("not-indexed", text)
        self.assertFalse(report["flip"]["indexed_flip_fired"])

    def test_states_by_3_1_and_the_arm_date_rule(self):
        engine = "google-search-console"
        self.write_report(TREATED, engine, "2026-10-25")  # baseline: most recent on or before the change
        self.write_report(TREATED, engine, "2026-11-10", homepage_indexed=True)  # inside the 14 days: ignored
        self.write_report(TREATED, engine, "2026-11-16", indexed_pages=3)  # post-change: at least 14 days after
        self.write_report(CONTROL, engine, "2026-10-25", indexed_pages=12, homepage_indexed=True)
        self.write_report(CONTROL, engine, "2026-11-20", indexed_pages=12, homepage_indexed=True)
        self.write_report(TREATED, "bing-webmaster-tools", "2026-10-25", property_verified=False, indexed_pages=None, homepage_indexed="unknown")
        report = self.report()
        by_key = {(e["domain"], e["engine"]): e for e in report["indexed"]}
        self.assertEqual(by_key[(TREATED, engine)]["baseline"], {"state": "not-indexed", "report_date": "2026-10-25"})
        self.assertEqual(by_key[(TREATED, engine)]["post_change"], {"state": "indexed", "report_date": "2026-11-16"})
        self.assertEqual(by_key[(CONTROL, engine)]["baseline"]["state"], "indexed")
        self.assertEqual(by_key[(TREATED, "bing-webmaster-tools")]["baseline"]["state"], "not-recorded")
        google = next(d for d in report["indexed_decisions"] if d["engine"] == engine)
        self.assertEqual(google["case"], 1)
        bing = next(d for d in report["indexed_decisions"] if d["engine"] == "bing-webmaster-tools")
        self.assertNotIn("case", bing)
        self.assertIn("not read", bing["reading"])

    def test_indexed_flip_fires_when_treated_is_indexed_on_both_engines_in_the_baseline(self):
        for engine in ("google-search-console", "bing-webmaster-tools"):
            self.write_report(TREATED, engine, "2026-10-22", indexed_pages=2, homepage_indexed=True)
        self.assertTrue(self.report()["flip"]["indexed_flip_fired"])


class FlipConditionTest(ScorerFixture):
    def control_cell(self, assistant, surface, searched_fraction):
        self.fill_cell("baseline", CONTROL_QUESTIONS, assistant, surface, 2,
                       lambda q, r: {"searched": (int(q[1:]) <= searched_fraction * 10), "retrieved_set": [] if surface == "api" else "unobservable"})

    def test_flag_fires_on_two_of_three_assistants(self):
        self.control_cell("gemini", "api", 0.8)
        self.control_cell("claude", "api", 0.6)
        self.control_cell("chatgpt", "app", 0.2)
        report = self.report()
        flip = report["flip"]
        self.assertEqual(flip["per_assistant"]["gemini"]["F"], 0.8)
        self.assertEqual(flip["per_assistant"]["claude"]["F"], 0.6)
        self.assertEqual(flip["per_assistant"]["chatgpt"]["F"], 0.2)
        self.assertEqual(flip["fired_on"], ["gemini", "claude"])
        self.assertTrue(flip["fired"])
        text = render(report)
        self.assertIn("F_gemini = 16/20 = 0.80 on api - above threshold", text)
        self.assertIn("flip flag FIRED", text)

    def test_flag_does_not_fire_on_one_of_three(self):
        self.control_cell("gemini", "api", 0.8)
        self.control_cell("claude", "api", 0.4)
        self.control_cell("chatgpt", "app", 0.5)  # exactly 0.50 is not above the threshold
        flip = self.report()["flip"]
        self.assertEqual(flip["fired_on"], ["gemini"])
        self.assertFalse(flip["fired"])
        self.assertIn("flip flag did not fire", render(self.report()))

    def test_with_two_assistants_measured_the_flag_needs_both(self):
        self.control_cell("gemini", "api", 0.8)
        self.control_cell("claude", "api", 0.4)
        flip = self.report()["flip"]
        self.assertEqual(flip["measured"], 2)
        self.assertEqual(flip["per_assistant"]["chatgpt"]["F"], "not measured")
        self.assertFalse(flip["fired"])

    def test_an_assistant_without_a_key_is_measured_on_its_app_cell(self):
        self.control_cell("gemini", "app", 0.8)
        self.control_cell("claude", "app", 0.7)
        flip = self.report()["flip"]
        self.assertEqual(flip["per_assistant"]["gemini"]["surface"], "app")
        self.assertTrue(flip["fired"])


class DecisionFixture(ScorerFixture):
    """7.6 on the gemini api cells with 10 questions at 5 repeats per site per arm."""

    def arms(self, treated_post_hits, control_post_hits, treated_base_hits=(), control_base_hits=(), treated_post_extra=None):
        def overrides(site, hits, extra):
            def fn(q, r):
                if extra:
                    forced = extra(q, r)
                    if forced is not None:
                        return forced
                if (q, r) in hits:
                    return retrieved_hit(site)
                return searched_not_retrieved(q, r)
            return fn
        self.fill_cell("baseline", TREATED_QUESTIONS, "gemini", "api", 5, overrides(TREATED, set(treated_base_hits), None))
        self.fill_cell("baseline", CONTROL_QUESTIONS, "gemini", "api", 5, overrides(CONTROL, set(control_base_hits), None))
        self.fill_cell("post-change", TREATED_QUESTIONS, "gemini", "api", 5, overrides(TREATED, set(treated_post_hits), treated_post_extra))
        self.fill_cell("post-change", CONTROL_QUESTIONS, "gemini", "api", 5, overrides(CONTROL, set(control_post_hits), None))

    TWO_QUESTION_RISE = {("t01", 1), ("t01", 2), ("t01", 3), ("t02", 1), ("t02", 2)}
    CONTROL_RISE = {("c01", 1), ("c01", 2), ("c01", 3), ("c02", 1), ("c02", 2)}


class DecisionRuleTest(DecisionFixture):
    def test_case_1_treated_moved_control_did_not(self):
        self.arms(self.TWO_QUESTION_RISE, set())
        report = self.report()
        decision = decision_of(report, "gemini", "api", "retrieved")
        self.assertEqual(decision["case"], 1)
        self.assertEqual((decision["dT_pp"], decision["dC_pp"], decision["treated_post_distinct_questions"]), (10.0, 0.0, 2))
        self.assertIn("effect 10.0 pp over 2 questions", decision["reading"])
        self.assertEqual(decision_of(report, "gemini", "api", "named")["case"], 2)
        self.assertIn("at the floor", decision_of(report, "gemini", "api", "named")["reading"])
        self.assertEqual(report["verdicts"]["gemini"]["verdict"], "case 1 at retrieved")
        self.assertEqual(report["verdicts"]["decision"], "the change moved the assistants")
        self.assertIn("gemini | api | retrieved                        case 1:", render(report))

    def test_case_2_neither_moved_prints_below_threshold_movement(self):
        self.arms({("t01", 1), ("t01", 2)}, set())
        report = self.report()
        decision = decision_of(report, "gemini", "api", "retrieved")
        self.assertEqual(decision["case"], 2)
        self.assertEqual(decision["dT_pp"], 4.0)
        self.assertIn("observed, below the smallest effect worth claiming", decision["reading"])
        self.assertEqual(report["verdicts"]["gemini"]["verdict"], "no rung in case 1")
        self.assertEqual(report["verdicts"]["decision"], "the change is not shown to have moved the assistants")

    def test_case_3_both_moved_is_drift_with_dT_minus_dC(self):
        self.arms(self.TWO_QUESTION_RISE | {("t03", 1), ("t03", 2), ("t03", 3), ("t04", 1), ("t04", 2)}, self.CONTROL_RISE)
        decision = decision_of(self.report(), "gemini", "api", "retrieved")
        self.assertEqual(decision["case"], 3)
        self.assertEqual((decision["dT_pp"], decision["dC_pp"], decision["dT_minus_dC_pp"]), (20.0, 10.0, 10.0))
        self.assertIn("drift", decision["reading"])
        self.assertIn("dT - dC = 10.0 pp", decision["reading"])
        self.assertIn("treated moved more than the control under drift", decision["reading"])

    def test_case_3_without_the_weaker_reading(self):
        self.arms(self.TWO_QUESTION_RISE, self.CONTROL_RISE)
        decision = decision_of(self.report(), "gemini", "api", "retrieved")
        self.assertEqual(decision["case"], 3)
        self.assertEqual(decision["dT_minus_dC_pp"], 0.0)
        self.assertNotIn("weaker", decision["reading"])

    def test_case_4_control_moved_treated_did_not(self):
        self.arms(set(), self.CONTROL_RISE)
        decision = decision_of(self.report(), "gemini", "api", "retrieved")
        self.assertEqual(decision["case"], 4)
        self.assertIn("not credited", decision["reading"])
        self.assertIn("control moved", decision["reading"])

    def test_two_question_floor_a_rise_carried_by_one_question_is_not_case_1(self):
        self.arms({("t01", r) for r in range(1, 6)}, set())
        report = self.report()
        decision = decision_of(report, "gemini", "api", "retrieved")
        self.assertEqual(decision["dT_pp"], 10.0)
        self.assertEqual(decision["treated_post_distinct_questions"], 1)
        self.assertIsNone(decision["case"])
        self.assertIn("fewer than 2", decision["reading"])
        self.assertIn("below the smallest effect worth claiming", decision["reading"])
        self.assertEqual(report["verdicts"]["decision"], "the change is not shown to have moved the assistants")

    def test_no_baseline_is_printed_for_a_cell_with_no_baseline_arm(self):
        self.fill_cell("post-change", TREATED_QUESTIONS, "claude", "api", 1, lambda q, r: retrieved_hit(TREATED))
        self.fill_cell("post-change", CONTROL_QUESTIONS, "claude", "api", 1, searched_not_retrieved)
        report = self.report()
        decision = decision_of(report, "claude", "api", "retrieved")
        self.assertIsNone(decision["case"])
        self.assertEqual(decision["reading"], "no baseline")
        self.assertEqual(report["verdicts"]["claude"]["verdict"], "no baseline")
        self.assertIn("claude | api | retrieved                        -: no baseline", render(report))

    def test_baseline_only_prints_no_comparison(self):
        self.fill_cell("baseline", TREATED_QUESTIONS, "claude", "api", 1, searched_not_retrieved)
        self.fill_cell("baseline", CONTROL_QUESTIONS, "claude", "api", 1, searched_not_retrieved)
        report = self.report()
        self.assertEqual(decision_of(report, "claude", "api", "retrieved")["reading"], "no post-change arm yet")
        self.assertEqual(report["verdicts"]["claude"]["verdict"], "baseline only - no comparison yet")

    def test_unobservable_rung_has_no_case(self):
        self.fill_cell("baseline", TREATED_QUESTIONS, "chatgpt", "api", 1, lambda q, r: {})
        self.fill_cell("baseline", CONTROL_QUESTIONS, "chatgpt", "api", 1, lambda q, r: {})
        self.fill_cell("post-change", TREATED_QUESTIONS, "chatgpt", "api", 1, lambda q, r: {})
        self.fill_cell("post-change", CONTROL_QUESTIONS, "chatgpt", "api", 1, lambda q, r: {})
        report = self.report()
        self.assertEqual(decision_of(report, "chatgpt", "api", "retrieved")["reading"], "unobservable")
        self.assertEqual(decision_of(report, "chatgpt", "api", "named")["case"], 2)


class GuardrailTest(DecisionFixture):
    def test_confounded_when_the_searched_rate_moves_20pp_and_case_1_is_withheld(self):
        # Treated post-change: searched on 30 of 50 against 50 of 50 in the baseline - a 40 pp move.
        def extra(q, r):
            if r >= 4:
                return {"searched": False, "retrieved_set": []}
            return None
        self.arms(self.TWO_QUESTION_RISE, set(), treated_post_extra=extra)
        report = self.report()
        guard = next(g for g in report["guardrails"] if (g["site"], g["arm"]) == (TREATED, "post-change"))
        self.assertEqual(guard["searched_move_pp"], 40.0)
        self.assertTrue(guard["confounded"])
        self.assertEqual(guard["flags"], ["confounded"])
        control = next(g for g in report["guardrails"] if (g["site"], g["arm"]) == (CONTROL, "post-change"))
        self.assertFalse(control["confounded"])
        decision = decision_of(report, "gemini", "api", "retrieved")
        self.assertEqual(decision["case"], 1)
        self.assertEqual(decision["verdict_withheld"], ["confounded"])
        self.assertEqual(report["verdicts"]["gemini"]["verdict"], "no rung in case 1")
        text = render(report)
        self.assertIn("searched move 40.0 pp CONFOUNDED", text)
        self.assertIn("case 1 verdict withheld (confounded)", text)

    def test_thin_when_the_failure_share_passes_ten_percent(self):
        self.arms(self.TWO_QUESTION_RISE, set())
        for r in range(1, 7):
            self.write_record(make_record("t05", "gemini", "api", arm="post-change", repeat_index=5 + r, status="failed",
                                          failure_detail="timeout", response_text="", searched=False, retrieved_set=[]))
        report = self.report()
        guard = next(g for g in report["guardrails"] if (g["site"], g["arm"]) == (TREATED, "post-change"))
        self.assertAlmostEqual(guard["failure_share"], 6 / 56, places=4)
        self.assertTrue(guard["thin"])
        decision = decision_of(report, "gemini", "api", "retrieved")
        self.assertEqual(decision["case"], 1)
        self.assertEqual(decision["verdict_withheld"], ["thin"])
        self.assertIn("THIN", render(report))

    def test_model_changed_between_arms_is_printed_and_refused(self):
        self.arms(set(), set())
        for path in sorted(os.listdir(os.path.join(self.data_dir, "responses", "post-change", "gemini", "api"))):
            full = os.path.join(self.data_dir, "responses", "post-change", "gemini", "api", path)
            record = read_json(full)
            record["model"] = "gemini-other-model"
            self.write_record(record)
        report = Scorer(self.data_dir).run()
        self.assertEqual(report["errors"], [])
        guard = next(g for g in report["guardrails"] if (g["site"], g["arm"]) == (TREATED, "post-change"))
        self.assertTrue(guard["model_changed"])
        self.assertIn("MODEL CHANGED between arms", render(report))


class CliTest(ScorerFixture):
    def test_clean_fixture_exits_zero_and_json_matches_text(self):
        self.write_record(make_record("t01", "gemini", "api", searched=False, retrieved_set=[]))
        code, text = run_cli(self.data_dir)
        self.assertEqual(code, 0)
        self.assertIn("launchyourfirstwebsite.com | gemini | api | baseline", text)
        code, as_json = run_cli(self.data_dir, json_output=True)
        self.assertEqual(code, 0)
        self.assertIn('"cells"', as_json)

    def test_missing_frozen_file_exits_two(self):
        os.remove(os.path.join(self.data_dir, "arms.json"))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = score.main(["--data", self.data_dir])
        self.assertEqual(code, 2)
        self.assertIn("arms.json", err.getvalue())

    def test_rate_rungs_are_the_six_of_section_four(self):
        self.assertEqual(RATE_RUNGS, ("searched", "retrieved", "named", "linked", "cited", "paraphrased_without_attribution"))


if __name__ == "__main__":
    unittest.main()
