"""Criterion 2: one fixture that passes every scorer-enforced invariant of
section 9, then one record or report altered per invariant - I1, I2, I3, I4,
I5, I6, I7, I8, I9, I10, I11, I14 - and the scorer exits non-zero naming the
file and the invariant."""

import contextlib
import io
import os
import shutil
import unittest

from support import CONTROL, TREATED, FixtureCase, make_record, read_json, record_path, write_json

import score
from measurement.records import RecordError
from measurement.scoring import check_i11

HIT = [{"url": "https://launchyourfirstwebsite.com/hosting", "title": "Hosting"}]


class InvariantFixture(FixtureCase):
    """Two claude api records, one gemini api record and one chatgpt app record
    in the baseline, plus an indexing report - enough for every invariant."""

    def setUp(self):
        super().setUp()
        self.claude_1 = self.write_record(make_record("t01", "claude", "api", repeat_index=1, searched=True, retrieved_set=HIT,
                                                      response_text="See launchyourfirstwebsite.com for a guide."))
        self.claude_2 = self.write_record(make_record("t01", "claude", "api", repeat_index=2, searched=False, retrieved_set=[]))
        self.gemini = self.write_record(make_record("c01", "gemini", "api", searched=True, retrieved_set=[{"url": "https://learnsql.com/", "title": "learnsql.com"}]))
        self.chatgpt = self.write_record(make_record("c01", "chatgpt", "app", searched=True, cited_urls=["https://learnsql.com/"]))
        self.report_path = self.write_report(TREATED, "google-search-console", "2026-10-22")

    def run_scorer(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = score.main(["--data", self.data_dir])
        return code, out.getvalue()

    def alter(self, path, **changes):
        record = read_json(path)
        for key, value in changes.items():
            if value is ...:
                del record[key]
            else:
                record[key] = value
        write_json(path, record)
        return record

    def assert_refused(self, invariant, path, message_part=None):
        code, text = self.run_scorer()
        self.assertEqual(code, 1, text)
        relative = os.path.relpath(path, self.data_dir)
        line = next((l for l in text.splitlines() if l.strip().startswith(invariant + ":")), None)
        self.assertIsNotNone(line, "no refusal naming %s in:\n%s" % (invariant, text))
        self.assertIn(relative, line)
        if message_part:
            self.assertIn(message_part, line)
        return text


class CleanPassTest(InvariantFixture):
    def test_the_unaltered_fixture_passes_every_invariant(self):
        code, text = self.run_scorer()
        self.assertEqual(code, 0, text)
        self.assertNotIn("REFUSED", text)
        self.assertIn("n_records=2 n_collected=2", text)


class InvariantTest(InvariantFixture):
    def test_i1_two_records_for_one_key(self):
        duplicate = os.path.join(os.path.dirname(self.claude_1), "t01-r03.json")
        shutil.copy(self.claude_1, duplicate)  # same question_id and repeat_index inside, a second file outside
        self.assert_refused("I1", duplicate, "repeat_index 1")

    def test_i1_duplicate_key_across_two_files(self):
        other = os.path.join(os.path.dirname(self.claude_1), "t01-r02.json")
        self.alter(other, repeat_index=1)
        text = self.assert_refused("I1", other)
        self.assertIn("I1", text)

    def test_i2_missing_field_named(self):
        self.alter(self.gemini, searched_evidence=...)
        self.assert_refused("I2", self.gemini, "missing field searched_evidence")

    def test_i2_null_where_the_field_list_forbids_it(self):
        self.alter(self.gemini, response_text=None)
        self.assert_refused("I2", self.gemini, "response_text")

    def test_i2_unobservable_in_a_field_that_does_not_admit_it(self):
        self.alter(self.gemini, screenshots="unobservable")
        self.assert_refused("I2", self.gemini, "screenshots")

    def test_i3_question_text_disagrees_with_the_frozen_set(self):
        self.alter(self.claude_1, question_text="What is the cheapest way to put a website online?")
        self.assert_refused("I3", self.claude_1, "question_text")

    def test_i3_site_disagrees_with_the_frozen_set(self):
        self.alter(self.claude_2, site=CONTROL, site_role="control")
        self.assert_refused("I3", self.claude_2, "site")

    def test_i4_failed_without_failure_detail(self):
        self.alter(self.claude_2, status="failed", response_text="", failure_detail=None)
        self.assert_refused("I4", self.claude_2, "failure_detail")

    def test_i4_collected_with_empty_response_text(self):
        self.alter(self.claude_2, response_text="")
        self.assert_refused("I4", self.claude_2, "response_text")

    def test_i5_app_record_with_an_array_retrieved_set(self):
        self.alter(self.chatgpt, retrieved_set=[])
        self.assert_refused("I5", self.chatgpt, "unobservable")

    def test_i5_api_record_with_a_non_empty_set_when_not_searched(self):
        self.alter(self.gemini, searched=False, searched_evidence=None, retrieved_set=[{"url": "https://learnsql.com/", "title": "learnsql.com"}])
        self.assert_refused("I5", self.gemini, "empty when searched is false")

    def test_i6_claude_api_with_a_system_prompt(self):
        record = read_json(self.claude_1)
        record["settings"]["system_prompt"] = "Answer briefly."
        write_json(self.claude_1, record)
        record = read_json(self.claude_2)
        record["settings"]["system_prompt"] = "Answer briefly."
        write_json(self.claude_2, record)
        self.assert_refused("I6", self.claude_1, "system_prompt")

    def test_i7_model_differs_within_an_api_cell(self):
        self.alter(self.claude_2, model="claude-some-other-model")
        self.assert_refused("I7", self.claude_2, "model or settings differ")

    def test_i7_settings_differ_within_an_api_cell(self):
        record = read_json(self.claude_2)
        record["settings"]["max_uses"] = 3
        write_json(self.claude_2, record)
        self.assert_refused("I7", self.claude_2)

    def test_i7_on_an_app_surface_is_a_settings_drift_flag_not_a_refusal(self):
        second = make_record("c02", "chatgpt", "app", searched=False, model="gpt-shown-in-app")
        self.write_record(second)
        code, text = self.run_scorer()
        self.assertEqual(code, 0, text)
        self.assertIn("warning: settings-drift", text)

    def test_i8_baseline_record_dated_after_the_change(self):
        self.alter(self.gemini, collected_at="2026-11-01T00:00:00Z")
        self.assert_refused("I8", self.gemini, "change_applied_on")

    def test_i8_post_change_record_dated_before_the_window_opens(self):
        early = make_record("c02", "gemini", "api", arm="post-change", collected_at="2026-11-10T10:00:00Z", searched=False, retrieved_set=[])
        path = self.write_record(early)
        self.assert_refused("I8", path, "post_change.opens")

    def test_i9_status_outside_the_three_so_counts_would_not_add_up(self):
        self.alter(self.gemini, status="pending", failure_detail="still waiting")
        self.assert_refused("I9", self.gemini, "pending")

    def test_i10_site_in_the_retrieved_set_when_not_searched(self):
        self.alter(self.claude_2, searched=False, searched_evidence=None, retrieved_set=HIT)
        self.assert_refused("I10", self.claude_2, "searched is false")

    def test_i11_paraphrased_beside_a_true_named_is_refused(self):
        # The scorer derives all four levels, so no stored record can carry this
        # state; the check guards the derivation and is driven directly.
        errors = []
        levels = {"named": True, "linked": False, "cited": False, "paraphrased_without_attribution": True}
        self.assertFalse(check_i11(levels, "responses/baseline/gemini/api/t01-r01.json", errors))
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], RecordError)
        self.assertEqual(errors[0].invariant, "I11")
        self.assertIn("t01-r01.json", str(errors[0]))
        self.assertTrue(check_i11({"named": False, "linked": False, "cited": False, "paraphrased_without_attribution": True}, "x", []))

    def test_i14_indexing_report_missing_a_field(self):
        report = read_json(self.report_path)
        del report["homepage_indexed"]
        write_json(self.report_path, report)
        self.assert_refused("I14", self.report_path, "missing field homepage_indexed")

    def test_i14_indexing_report_whose_path_disagrees_with_its_fields(self):
        report = read_json(self.report_path)
        report["engine"] = "bing-webmaster-tools"
        write_json(self.report_path, report)
        self.assert_refused("I14", self.report_path)

    def test_a_refused_record_is_left_out_of_the_cells_but_the_rest_still_print(self):
        self.alter(self.gemini, status="pending", failure_detail="still waiting")
        code, text = self.run_scorer()
        self.assertEqual(code, 1)
        self.assertIn("launchyourfirstwebsite.com | claude | api | baseline", text)
        self.assertNotIn("levelupsql.com | gemini | api | baseline", text)


if __name__ == "__main__":
    unittest.main()
