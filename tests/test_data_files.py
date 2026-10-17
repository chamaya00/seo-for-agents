"""Criterion 5: the four frozen data files and the manual template agree with
the framework document."""

import copy
import os
import re
import unittest

from support import DATA, FRAMEWORK_DOC, SETTINGS, read_json

from measurement import records


def section_six_rows():
    """The twenty (id, text) rows of the two tables in section 6 of the framework,
    read from the markdown itself so the JSON cannot vouch for itself."""
    with open(FRAMEWORK_DOC, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    rows = []
    in_section = False
    for line in lines:
        if line.startswith("## "):
            in_section = line.startswith("## 6.")
            continue
        if not in_section or not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or not re.match(r"^[tc]\d\d$", cells[0]):
            continue
        rows.append({"id": cells[0], "site_code": cells[1], "class": cells[2], "text": cells[4]})
    return rows


class QuestionSetTest(unittest.TestCase):
    def setUp(self):
        self.rows = read_json(os.path.join(DATA, "question-set.json"))
        self.doc_rows = section_six_rows()

    def test_twenty_rows_with_every_field(self):
        self.assertEqual(len(self.rows), 20)
        for row in self.rows:
            self.assertEqual(
                sorted(row), ["class_reason", "question_class", "question_id", "site", "site_role", "text"], row
            )

    def test_ids_and_text_match_the_two_tables_in_section_six(self):
        self.assertEqual(len(self.doc_rows), 20, "section 6 should hold twenty question rows")
        self.assertEqual([r["question_id"] for r in self.rows], [r["id"] for r in self.doc_rows])
        self.assertEqual({r["question_id"]: r["text"] for r in self.rows}, {r["id"]: r["text"] for r in self.doc_rows})

    def test_site_and_class_match_the_tables(self):
        code = {"T": "launchyourfirstwebsite.com", "C": "levelupsql.com"}
        role = {"T": "treated", "C": "control"}
        by_id = {r["id"]: r for r in self.doc_rows}
        for row in self.rows:
            doc = by_id[row["question_id"]]
            self.assertEqual(row["site"], code[doc["site_code"]], row["question_id"])
            self.assertEqual(row["site_role"], role[doc["site_code"]], row["question_id"])
            self.assertEqual(row["question_class"], doc["class"], row["question_id"])

    def test_counts_per_site_and_class(self):
        for site, prefix in (("launchyourfirstwebsite.com", "t"), ("levelupsql.com", "c")):
            mine = [r for r in self.rows if r["site"] == site]
            self.assertEqual(len(mine), 10)
            self.assertTrue(all(r["question_id"].startswith(prefix) for r in mine))
            self.assertEqual(sum(r["question_class"] == "search-triggering" for r in mine), 8)
            self.assertEqual(sum(r["question_class"] == "informational" for r in mine), 2)

    def test_no_text_names_a_site_i13(self):
        for row in self.rows:
            self.assertNotRegex(row["text"].lower(), r"levelupsql|launchyourfirstwebsite", row["question_id"])
            self.assertNotRegex(row["class_reason"].lower(), r"levelupsql|launchyourfirstwebsite", row["question_id"])

    def test_loader_accepts_the_file(self):
        questions = records.load_question_set(os.path.join(DATA, "question-set.json"))
        self.assertEqual(len(questions), 20)


class CollectionSettingsTest(unittest.TestCase):
    def test_every_assistant_and_surface_has_a_row_with_the_row_fields(self):
        for assistant in records.ASSISTANTS:
            for surface in records.SURFACES:
                row = SETTINGS[assistant][surface]
                self.assertEqual(sorted(row), sorted(("model",) + records.SETTINGS_ROW_FIELDS), (assistant, surface))

    def test_api_rows_are_pinned_and_app_rows_are_not(self):
        # Section 8: one exact model id per API cell, chosen before the baseline
        # and never changed between arms. An app's model cannot be pinned, so
        # the app rows stay null and the recorder writes what the app shows.
        for assistant in records.ASSISTANTS:
            api = SETTINGS[assistant]["api"]
            self.assertIsInstance(api["model"], str, assistant)
            self.assertTrue(api["model"].strip(), assistant)
            app = SETTINGS[assistant]["app"]
            self.assertIsNone(app["model"], assistant)
            self.assertIsNone(app["tool_version"], assistant)
        # Gemini's tool is named by `web_tool`, so its `tool_version` stays null;
        # the other two vendors name the tool by a type string.
        self.assertIsNone(SETTINGS["gemini"]["api"]["tool_version"])
        self.assertEqual(SETTINGS["claude"]["api"]["tool_version"], "web_search_20250305")
        self.assertIsInstance(SETTINGS["chatgpt"]["api"]["tool_version"], str)

    def test_section_eight_values(self):
        gemini = SETTINGS["gemini"]["api"]
        self.assertEqual(gemini["web_tool"], "google_search")
        self.assertIsNone(gemini["dynamic_threshold"])
        self.assertIsNone(gemini["system_prompt"])
        self.assertIsNone(gemini["temperature"])
        claude = SETTINGS["claude"]["api"]
        self.assertEqual(claude["web_tool"], "web_search")
        self.assertEqual(claude["max_uses"], 5)
        self.assertIsNone(claude["system_prompt"])
        self.assertIsNone(claude["temperature"])
        openai = SETTINGS["chatgpt"]["api"]
        self.assertEqual(openai["web_tool"], "web_search")
        self.assertIsNone(openai["system_prompt"])
        chatgpt_app = SETTINGS["chatgpt"]["app"]
        self.assertIs(chatgpt_app["logged_in"], True)
        self.assertIs(chatgpt_app["temporary_chat"], True)
        self.assertIs(chatgpt_app["search_forced"], False)
        for assistant in ("gemini", "claude"):
            self.assertIs(SETTINGS[assistant]["app"]["logged_in"], True)
            self.assertIs(SETTINGS[assistant]["app"]["search_forced"], False)

    def test_loader_accepts_the_file(self):
        records.load_settings(os.path.join(DATA, "collection-settings.json"))


class ArmsTest(unittest.TestCase):
    def test_shape_of_11_9_with_every_date_null(self):
        arms = read_json(os.path.join(DATA, "arms.json"))
        self.assertEqual(
            arms,
            {
                "change_applied_on": None,
                "baseline": {"opened": None, "closed": None},
                "post_change": {"opens": None, "closed": None},
            },
        )
        records.load_arms(os.path.join(DATA, "arms.json"))


class ResponseTemplateTest(unittest.TestCase):
    def setUp(self):
        self.template = read_json(os.path.join(DATA, "templates", "response-template.json"))

    def test_carries_every_field_of_11_1_and_the_app_constants(self):
        fields = [k for k in self.template if k != "$comment"]
        self.assertEqual(fields, list(records.RECORD_FIELD_NAMES))
        self.assertEqual(self.template["surface"], "app")
        self.assertEqual(self.template["collector"], "owner")
        self.assertEqual(self.template["retrieved_set"], "unobservable")
        self.assertEqual(self.template["screenshots"], [])
        self.assertEqual(self.template["searched_evidence"], "visible-indicator")
        self.assertEqual(self.template["settings"]["region"]["source"], "owner")
        for name, _ in records.SETTINGS_FIELDS:
            self.assertIn(name, self.template["settings"])

    def filled_copy(self):
        filled = copy.deepcopy(self.template)
        del filled["$comment"]
        filled.update(
            {
                "arm": "baseline",
                "site": "levelupsql.com",
                "site_role": "control",
                "question_id": "c01",
                "question_text": "What is the best site to practise SQL with real exercises?",
                "question_class": "search-triggering",
                "assistant": "chatgpt",
                "repeat_index": 1,
                "collected_at": "2026-10-20T09:00:00Z",
                "model": "unknown",
                "status": "collected",
                "response_text": "Try LearnSQL and SQLZoo.",
                "searched": True,
                "cited_urls": ["https://learnsql.com/"],
                "raw_response": "Try LearnSQL and SQLZoo.",
                "screenshots": ["c01-r01-1.png"],
            }
        )
        filled["settings"]["logged_in"] = True
        filled["settings"]["temporary_chat"] = True
        filled["settings"]["region"]["value"] = "GB"
        return filled

    def test_a_filled_copy_parses_into_the_shape_the_scorer_reads(self):
        filled = self.filled_copy()
        records.check_fields(filled, "c01-r01.json")
        self.assertEqual(records.record_key(filled), ("baseline", "chatgpt", "app", "c01", 1))

    def test_a_copy_missing_a_field_is_refused_with_the_field_named(self):
        for field in ("cited_urls", "searched", "collected_at", "settings"):
            filled = self.filled_copy()
            del filled[field]
            with self.assertRaises(records.RecordError) as caught:
                records.check_fields(filled, "c01-r01.json")
            self.assertEqual(caught.exception.invariant, "I2")
            self.assertIn("missing field %s" % field, str(caught.exception))
            self.assertIn("c01-r01.json", str(caught.exception))

    def test_a_copy_still_holding_a_fill_marker_is_refused(self):
        filled = self.filled_copy()
        filled["searched"] = "FILL"
        with self.assertRaises(records.RecordError) as caught:
            records.check_fields(filled, "c01-r01.json")
        self.assertIn("searched", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
