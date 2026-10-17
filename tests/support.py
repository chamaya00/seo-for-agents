"""Shared paths and the fixture builders every test module uses.

Records are built through `make_record`, which fills every field of 11.1 the
way the collector and the manual template do, so a fixture cannot describe a
shape the system would never produce.
"""

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
DATA = os.path.join(ROOT, "data")
FRAMEWORK_DOC = os.path.join(ROOT, "docs", "measurement", "4-measurement-framework.md")

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

TREATED = "launchyourfirstwebsite.com"
CONTROL = "levelupsql.com"


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


QUESTIONS = {row["question_id"]: row for row in read_json(os.path.join(DATA, "question-set.json"))}
SETTINGS = read_json(os.path.join(DATA, "collection-settings.json"))


def settings_row(assistant, surface, region_source):
    row = {k: v for k, v in SETTINGS[assistant][surface].items() if k != "model"}
    row["region"] = {"source": region_source, "value": "unknown"}
    row["runner_label"] = "ubuntu-latest" if region_source == "actions-runner" else None
    return row


def make_record(question_id, assistant, surface, arm="baseline", repeat_index=1, **overrides):
    """A complete 11.1 record for one response, with sensible per-surface defaults."""
    question = QUESTIONS[question_id]
    api = surface == "api"
    settings = settings_row(assistant, surface, "actions-runner" if api else "owner")
    record = {
        "schema_version": "1",
        "record_type": "response",
        "arm": arm,
        "site": question["site"],
        "site_role": question["site_role"],
        "question_id": question_id,
        "question_text": question["text"],
        "question_class": question["question_class"],
        "assistant": assistant,
        "surface": surface,
        "repeat_index": repeat_index,
        "collected_at": "2026-10-20T10:00:00Z" if arm == "baseline" else "2026-11-20T10:00:00Z",
        "collector": "workflow:1234" if api else "owner",
        "model": "%s-pinned-model" % assistant if api else "unknown",
        "settings": settings,
        "status": "collected",
        "failure_detail": None,
        "response_text": "An answer that mentions no site at all.",
        "searched": False if api else False,
        "searched_evidence": None,
        "retrieved_set": [] if api else "unobservable",
        "cited_urls": [],
        "raw_response": {} if api else "An answer that mentions no site at all.",
        "screenshots": [],
        "notes": None,
    }
    if api and assistant == "chatgpt":
        record["searched"] = "unobservable"
        record["retrieved_set"] = "unobservable"
        record["cited_urls"] = "unobservable"
    record.update(overrides)
    if record["searched"] is True and record["searched_evidence"] is None:
        record["searched_evidence"] = "visible-indicator" if not api else "content[].type == server_tool_use"
    if record["searched"] == "unobservable":
        record["searched_evidence"] = None
    return record


def record_path(data_dir, record):
    return os.path.join(
        data_dir, "responses", record["arm"], record["assistant"], record["surface"],
        "%s-r%02d.json" % (record["question_id"], record["repeat_index"]),
    )


ARMS_WITH_DATES = {
    "change_applied_on": "2026-11-01",
    "baseline": {"opened": "2026-10-20", "closed": "2026-10-26"},
    "post_change": {"opens": "2026-11-15", "closed": None},
}


class FixtureCase(unittest.TestCase):
    """A temporary data directory holding copies of the four frozen files."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="seo-measure-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.data_dir = os.path.join(self.tmp, "data")
        os.makedirs(self.data_dir)
        for name in ("question-set.json", "collection-settings.json"):
            shutil.copy(os.path.join(DATA, name), os.path.join(self.data_dir, name))
        write_json(os.path.join(self.data_dir, "arms.json"), copy.deepcopy(ARMS_WITH_DATES))

    def write_record(self, record):
        path = record_path(self.data_dir, record)
        write_json(path, record)
        return path

    def write_fingerprints(self, fingerprints):
        write_json(os.path.join(self.data_dir, "fingerprints.json"), fingerprints)

    def write_report(self, domain, engine, date, **overrides):
        report = {
            "schema_version": "1",
            "record_type": "indexing-report",
            "domain": domain,
            "engine": engine,
            "report_date": date,
            "property_verified": True,
            "indexed_pages": 0,
            "not_indexed_pages": 4,
            "homepage_indexed": False,
            "last_crawl": None,
            "sitemap_submitted": False,
            "sitemap_discovered_urls": None,
            "screenshots": [],
            "recorded_by": "owner",
            "notes": None,
        }
        report.update(overrides)
        path = os.path.join(self.data_dir, "indexing", domain, engine, "%s.json" % date)
        write_json(path, report)
        return path
