"""The scorer: a directory of records in the layout of 11.2 to the framework's
report - per-cell rates (section 4), the indexed state (3.1), the per-question
search fractions (7.4), the flip condition (7.7), the guardrails (10), the
four-case decision rule (7.6) and the invariants of section 9.

Nothing is stored back. Every number is recomputed from the records on every
run, so a committed record never changes and a number computed today
reproduces tomorrow (11.1).
"""

import datetime
import os
import re
from collections import OrderedDict, defaultdict

from . import records as R
from .records import UNOBSERVABLE, RecordError

# Section 7.5 and 7.6.
SMALLEST_EFFECT_PP = 10.0
MIN_DISTINCT_QUESTIONS = 2
# Section 10.
SEARCHED_GUARDRAIL_PP = 20.0
FAILURE_SHARE_MAX = 0.10
# Section 7.7.
FLIP_THRESHOLD = 0.50
# Section 7.4: a question is bimodal when its search fraction is at or below
# 0.2 or at or above 0.8 - with 5 repeats exactly the 0/5, 1/5, 4/5, 5/5 the
# document names; the same bounds carry to 10 repeats.
BIMODAL_LOW, BIMODAL_HIGH, BIMODAL_SHARE = 0.2, 0.8, 0.80
# Section 3.1 and 7.2: the post-change indexing report is the most recent one
# dated at least this many days after the change.
INDEXING_LAG_DAYS = 14

# Per-response rungs, bottom up. `searched` is the guardrail, not an outcome
# (7.5); the decision rule runs over OUTCOME_RUNGS.
RATE_RUNGS = ("searched", "retrieved", "named", "linked", "cited", "paraphrased_without_attribution")
OUTCOME_RUNGS = RATE_RUNGS[1:]
# 3.8's order, strongest first, extended downward with `retrieved` for the
# overall verdict (7.6: "the highest rung in case 1").
RUNG_STRENGTH = ("cited", "linked", "named", "paraphrased_without_attribution", "retrieved")

INDEXING_REPORT_FIELDS = (
    "schema_version", "record_type", "domain", "engine", "report_date", "property_verified",
    "indexed_pages", "not_indexed_pages", "homepage_indexed", "last_crawl", "sitemap_submitted",
    "sitemap_discovered_urls", "screenshots", "recorded_by", "notes",
)

_FILE_NAME = re.compile(r"^([tc]\d\d)-r(\d\d)\.json$")
_SCHEME_URL = re.compile(r"https?://[^\s<>\"'()\[\]]+", re.IGNORECASE)
_WWW_URL = re.compile(r"(?<![\w/.@])www\.[^\s<>\"'()\[\]]+", re.IGNORECASE)
_MARKDOWN_TARGET = re.compile(r"\]\(\s*<?([^)\s>]+)>?\s*\)")
_TRAILING_PUNCTUATION = ".,;:!?'\""
_NON_WORD = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")


# --- matching rules, sections 3.3 to 3.7 -------------------------------------


def host_matches(host, domain):
    """3.3: the host equals the domain or ends in `.` + the domain."""
    if not host:
        return False
    host = host.lower().rstrip(".")
    return host == domain or host.endswith("." + domain)


def url_host(url):
    """The host of a URL written with a scheme, with `www.`, or bare."""
    if not isinstance(url, str):
        return None
    text = url.strip().rstrip(_TRAILING_PUNCTUATION)
    text = re.sub(r"^[a-z][a-z0-9+.-]*://", "", text, flags=re.IGNORECASE)
    host = re.split(r"[/?#]", text, 1)[0]
    host = host.rsplit("@", 1)[-1].split(":", 1)[0]
    return host.lower() or None


def item_matches(item, domain, assistant):
    """One retrieved_set or cited_urls item against a domain. The title rule is
    Gemini's (3.3): its `uri` may be a vendor redirect, so a `title` equal to
    the domain also counts."""
    if isinstance(item, str):
        return host_matches(url_host(item), domain)
    if host_matches(url_host(item.get("url")), domain):
        return True
    title = item.get("title")
    return assistant == "gemini" and isinstance(title, str) and title.strip().lower() == domain


def is_named(text, domain):
    """3.4: the unbroken domain token, case-insensitive, with or without www.
    and .com. A spaced rendering never counts."""
    token = domain.split(".")[0]
    return re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(token), text, re.IGNORECASE) is not None


def linked_hosts_in_text(text):
    """Every host offered as a link in prose: a scheme URL, a www. URL or a
    Markdown link target. A bare domain with none of those is not a link."""
    hosts = []
    for match in _SCHEME_URL.finditer(text):
        hosts.append(url_host(match.group(0)))
    for match in _WWW_URL.finditer(text):
        hosts.append(url_host(match.group(0)))
    for match in _MARKDOWN_TARGET.finditer(text):
        hosts.append(url_host(match.group(1)))
    return [h for h in hosts if h]


def is_linked(text, cited_urls, domain, assistant):
    """3.5: a link in the text, or a source the assistant attached."""
    if any(host_matches(host, domain) for host in linked_hosts_in_text(text)):
        return True
    if isinstance(cited_urls, list):
        return any(item_matches(item, domain, assistant) for item in cited_urls)
    return False


def is_cited(cited_urls, domain, assistant):
    """3.6 from the stored `cited_urls`, which the collector filled from the
    surface's own citation mechanism."""
    if cited_urls == UNOBSERVABLE:
        return UNOBSERVABLE
    return any(item_matches(item, domain, assistant) for item in cited_urls)


def is_retrieved(retrieved_set, domain, assistant):
    if retrieved_set == UNOBSERVABLE:
        return UNOBSERVABLE
    return any(item_matches(item, domain, assistant) for item in retrieved_set)


def normalise(text):
    """3.7: case-insensitive, whitespace collapsed, punctuation stripped."""
    text = _NON_WORD.sub(" ", text.lower())
    return _WHITESPACE.sub(" ", text).strip()


def fingerprint_matches(text, fingerprint):
    return normalise(fingerprint) in normalise(text)


def score_record(record, fingerprints, generic):
    """The per-response levels of 3.2 to 3.8 for one record.

    `fingerprints` is the site's list from data/fingerprints.json (or None),
    `generic` the set of fingerprint texts excluded by 3.7."""
    domain = record["site"]
    assistant = record["assistant"]
    text = record["response_text"]
    scored = OrderedDict()
    scored["searched"] = record["searched"]
    scored["retrieved"] = is_retrieved(record["retrieved_set"], domain, assistant)
    scored["named"] = is_named(text, domain)
    scored["linked"] = is_linked(text, record["cited_urls"], domain, assistant)
    scored["cited"] = is_cited(record["cited_urls"], domain, assistant)
    if fingerprints is None or len(fingerprints) < 3 or scored["cited"] == UNOBSERVABLE:
        # Fewer than three fingerprints makes the rung unobservable for the
        # site (3.7, 11.6); so does a surface where `cited` cannot be read,
        # since the rung is defined as "and cited is false".
        scored["paraphrased_without_attribution"] = UNOBSERVABLE
        scored["fingerprints_matched"] = []
    else:
        matched = [fp["text"] for fp in fingerprints if fp["text"] not in generic and fingerprint_matches(text, fp["text"])]
        scored["fingerprints_matched"] = matched
        scored["paraphrased_without_attribution"] = bool(matched) and not scored["named"] and not scored["linked"] and scored["cited"] is False
    scored["top_level"] = top_level(scored)
    return scored


def top_level(scored):
    """3.8: cited > linked > named > paraphrased-without-attribution > none."""
    if scored["cited"] is True:
        return "cited"
    if scored["linked"] is True:
        return "linked"
    if scored["named"] is True:
        return "named"
    if scored["paraphrased_without_attribution"] is True:
        return "paraphrased-without-attribution"
    return "none"


# --- the scorer --------------------------------------------------------------


def _date(value):
    return datetime.date.fromisoformat(value)


def _collected_date(record):
    return _date(record["collected_at"][:10])


def _rate(numerator, denominator, questions):
    return OrderedDict(
        numerator=numerator,
        denominator=denominator,
        rate=(numerator / denominator) if denominator else None,
        distinct_questions=len(questions),
    )


def _pp(a, b):
    """b - a in percentage points, or None when either rate is undefined."""
    if a is None or b is None:
        return None
    return round((b - a) * 100.0, 4)


class Scorer:
    """Reads one data directory. `run()` returns the report; `errors` holds
    every refusal found, each a RecordError naming the file and the invariant."""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.errors = []
        self.warnings = []
        self.questions = R.load_question_set(os.path.join(data_dir, "question-set.json"))
        self.settings = R.load_settings(os.path.join(data_dir, "collection-settings.json"))
        self.arms = R.load_arms(os.path.join(data_dir, "arms.json"))
        fingerprints_path = os.path.join(data_dir, "fingerprints.json")
        self.fingerprints = self._load_fingerprints(fingerprints_path) if os.path.exists(fingerprints_path) else {}
        self.records = []  # (where, record)
        self.reports = []  # (where, report)
        self.generic = set()

    # -- loading -----------------------------------------------------------

    def _load_fingerprints(self, path):
        raw = R.load_json(path)
        if not isinstance(raw, dict):
            raise ValueError("%s: expected an object keyed by site" % path)
        fingerprints = {}
        for site, items in raw.items():
            if site not in R.SITES:
                raise ValueError("%s: %r is not a site of this framework" % (path, site))
            if not isinstance(items, list) or not all(isinstance(i, dict) and isinstance(i.get("text"), str) for i in items):
                raise ValueError('%s: %s must be an array of {"text", "source_url"}' % (path, site))
            fingerprints[site] = items
        return fingerprints

    def _refuse(self, invariant, where, message):
        self.errors.append(RecordError(invariant, where, message))

    def load(self):
        responses = os.path.join(self.data_dir, "responses")
        if os.path.isdir(responses):
            for arm in sorted(os.listdir(responses)):
                for assistant in sorted(os.listdir(os.path.join(responses, arm))):
                    for surface in sorted(os.listdir(os.path.join(responses, arm, assistant))):
                        directory = os.path.join(responses, arm, assistant, surface)
                        if not os.path.isdir(directory):
                            continue
                        for name in sorted(os.listdir(directory)):
                            if name.endswith(".json"):
                                self._load_record(os.path.join(directory, name), arm, assistant, surface, name)
        indexing = os.path.join(self.data_dir, "indexing")
        if os.path.isdir(indexing):
            for domain in sorted(os.listdir(indexing)):
                for engine in sorted(os.listdir(os.path.join(indexing, domain))):
                    directory = os.path.join(indexing, domain, engine)
                    if not os.path.isdir(directory):
                        continue
                    for name in sorted(os.listdir(directory)):
                        if name.endswith(".json"):
                            self._load_report(os.path.join(directory, name), domain, engine, name)
        self._check_duplicates()
        self._check_settings_identical()
        return self

    def _load_record(self, path, arm, assistant, surface, name):
        where = os.path.relpath(path, self.data_dir)
        try:
            record = R.load_json(path)
        except ValueError as error:
            self._refuse("I2", where, "not valid JSON: %s" % error)
            return
        try:
            R.check_fields(record, where)
        except RecordError as error:
            self.errors.append(error)
            return
        if (record["arm"], record["assistant"], record["surface"]) != (arm, assistant, surface):
            self._refuse("I2", where, "arm, assistant and surface must match the directory the record is stored in")
            return
        match = _FILE_NAME.match(name)
        if not match or record["question_id"] != match.group(1) or record["repeat_index"] != int(match.group(2)):
            self._refuse("I1", where, "file name must be <question_id>-r<NN>.json for this record's question_id %s and repeat_index %d, "
                         "or the directory holds two records for one key" % (record["question_id"], record["repeat_index"]))
            return
        ok = True
        # I10 runs before I5: a site in a `searched = false` set is I10's case,
        # and I5 would otherwise name the same record for the emptier reason.
        for check in (self._check_i3, self._check_i4, self._check_i10, self._check_i5, self._check_i6, self._check_i9, self._check_i8):
            if not check(record, where):
                ok = False
        if ok:
            self.records.append((where, record))

    def _check_i3(self, record, where):
        question = self.questions.get(record["question_id"])
        if question is None:
            self._refuse("I3", where, "question_id %s is not in the frozen set" % record["question_id"])
            return False
        for field, expected in (("question_text", question["text"]), ("site", question["site"]),
                                ("site_role", question["site_role"]), ("question_class", question["question_class"])):
            if record[field] != expected:
                self._refuse("I3", where, "%s disagrees with the frozen set for %s: %r != %r" % (field, record["question_id"], record[field], expected))
                return False
        return True

    def _check_i4(self, record, where):
        if record["status"] != "collected" and record["failure_detail"] is None:
            self._refuse("I4", where, "status %r requires a non-null failure_detail" % record["status"])
            return False
        if record["status"] == "collected" and record["response_text"] == "":
            self._refuse("I4", where, "status collected requires a non-empty response_text")
            return False
        return True

    def _check_i5(self, record, where):
        if record["surface"] == "app" and record["retrieved_set"] != UNOBSERVABLE:
            self._refuse("I5", where, 'surface app requires retrieved_set "unobservable"')
            return False
        if record["surface"] == "api" and record["assistant"] in ("claude", "gemini"):
            if not isinstance(record["retrieved_set"], list):
                self._refuse("I5", where, "surface api on %s requires retrieved_set to be an array" % record["assistant"])
                return False
            if record["searched"] is False and record["retrieved_set"]:
                self._refuse("I5", where, "retrieved_set must be empty when searched is false")
                return False
        return True

    def _check_i6(self, record, where):
        if record["assistant"] == "claude" and record["surface"] == "api" and record["settings"]["system_prompt"] is not None:
            self._refuse("I6", where, "claude api requires settings.system_prompt null - no system prompt is sent on this surface")
            return False
        return True

    def _check_i9(self, record, where):
        if record["status"] not in R.STATUSES:
            self._refuse("I9", where, "status %r is none of collected, refused, failed, so the cell's counts would not add up" % record["status"])
            return False
        return True

    def _check_i10(self, record, where):
        if record["surface"] == "api" and record["searched"] is False and isinstance(record["retrieved_set"], list):
            if any(item_matches(item, record["site"], record["assistant"]) for item in record["retrieved_set"]):
                self._refuse("I10", where, "the site is in the retrieved set although searched is false")
                return False
        return True

    def _check_i8(self, record, where):
        collected = _collected_date(record)
        if record["arm"] == "baseline":
            applied = self.arms["change_applied_on"]
            if applied is not None and collected >= _date(applied):
                self._refuse("I8", where, "baseline record collected_at %s is not before change_applied_on %s" % (record["collected_at"], applied))
                return False
        else:
            opens = self.arms["post_change"]["opens"]
            if opens is None:
                self._refuse("I8", where, "post-change record but arms.post_change.opens is not set")
                return False
            if collected < _date(opens):
                self._refuse("I8", where, "post-change record collected_at %s is before post_change.opens %s" % (record["collected_at"], opens))
                return False
        return True

    def _check_duplicates(self):
        seen = {}
        kept = []
        for where, record in self.records:
            key = R.record_key(record)
            if key in seen:
                self._refuse("I1", where, "duplicates %s for (arm, assistant, surface, question_id, repeat_index) = %s" % (seen[key], key))
                continue
            seen[key] = where
            kept.append((where, record))
        self.records = kept

    def _check_settings_identical(self):
        first = {}
        for where, record in self.records:
            group = (record["assistant"], record["surface"], record["arm"])
            signature = (record["model"], record["settings"])
            if group not in first:
                first[group] = (where, signature)
                continue
            first_where, first_signature = first[group]
            if signature != first_signature:
                if record["surface"] == "api":
                    self._refuse("I7", where, "model or settings differ from %s within %s/%s %s" % (first_where, group[0], group[1], group[2]))
                else:
                    self.warnings.append("settings-drift: %s differs from %s within %s/%s %s" % (where, first_where, group[0], group[1], group[2]))
        if self.errors:
            bad = {e.where for e in self.errors}
            self.records = [(w, r) for w, r in self.records if w not in bad]

    def _load_report(self, path, domain, engine, name):
        where = os.path.relpath(path, self.data_dir)
        try:
            report = R.load_json(path)
        except ValueError as error:
            self._refuse("I14", where, "not valid JSON: %s" % error)
            return
        if not isinstance(report, dict):
            self._refuse("I14", where, "report is not a JSON object")
            return
        for field in INDEXING_REPORT_FIELDS:
            if field not in report:
                self._refuse("I14", where, "missing field %s" % field)
                return
        if report["record_type"] != "indexing-report":
            self._refuse("I14", where, 'record_type must be "indexing-report"')
            return
        if report["domain"] != domain or report["engine"] != engine or name != "%s.json" % report["report_date"]:
            self._refuse("I14", where, "domain, engine and report_date must match the file's path")
            return
        if domain not in R.SITES or engine not in R.ENGINES:
            self._refuse("I14", where, "domain or engine is not one of this framework's")
            return
        try:
            _date(report["report_date"])
        except ValueError:
            self._refuse("I14", where, "report_date must be YYYY-MM-DD")
            return
        self.reports.append((where, report))

    # -- scoring -----------------------------------------------------------

    def run(self):
        self.load()
        self._mark_generic()
        scored = []
        for where, record in self.records:
            site = record["site"]
            levels = score_record(record, self.fingerprints.get(site), self.generic)
            self._check_i11(levels, where)
            row = OrderedDict(file=where)
            for key in ("arm", "site", "assistant", "surface", "question_id", "question_class", "repeat_index", "status", "model"):
                row[key] = record[key]
            row.update(levels)
            scored.append(row)
        report = OrderedDict()
        report["errors"] = ["%s" % e for e in self.errors]
        report["warnings"] = list(self.warnings)
        report["generic_fingerprints"] = sorted(self.generic)
        report["records"] = scored
        report["cells"] = self._cells(scored)
        report["search_fractions"] = self._search_fractions(scored)
        report["flip"] = self._flip(scored)
        report["indexed"] = self._indexed()
        report["guardrails"] = self._guardrails(report["cells"])
        report["decisions"] = self._decisions(report["cells"], report["guardrails"])
        report["verdicts"] = self._verdicts(report["decisions"], scored)
        report["indexed_decisions"] = self._indexed_decisions(report["indexed"])
        return report

    def _mark_generic(self):
        """3.7: a fingerprint matching in a baseline API response where the
        site was not retrieved is generic and excluded in both arms."""
        for _, record in self.records:
            if record["arm"] != "baseline" or record["surface"] != "api" or record["status"] != "collected":
                continue
            if is_retrieved(record["retrieved_set"], record["site"], record["assistant"]) is not False:
                continue
            for fingerprint in self.fingerprints.get(record["site"], []):
                if fingerprint_matches(record["response_text"], fingerprint["text"]):
                    self.generic.add(fingerprint["text"])

    def _check_i11(self, levels, where):
        check_i11(levels, where, self.errors)

    def _cells(self, scored):
        groups = OrderedDict()
        for row in scored:
            key = (row["site"], row["assistant"], row["surface"], row["arm"])
            groups.setdefault(key, []).append(row)
        cells = []
        for (site, assistant, surface, arm), rows in sorted(groups.items()):
            cell = OrderedDict(site=site, assistant=assistant, surface=surface, arm=arm)
            cell["n_records"] = len(rows)
            cell["n_collected"] = sum(r["status"] == "collected" for r in rows)
            cell["n_refused"] = sum(r["status"] == "refused" for r in rows)
            cell["n_failed"] = sum(r["status"] == "failed" for r in rows)
            cell["distinct_questions"] = len({r["question_id"] for r in rows if r["status"] == "collected"})
            collected = [r for r in rows if r["status"] == "collected"]
            rates = OrderedDict()
            for rung in RATE_RUNGS:
                observable = [r for r in collected if r[rung] != UNOBSERVABLE]
                if collected and not observable:
                    rates[rung] = UNOBSERVABLE
                    continue
                hits = [r for r in observable if r[rung] is True]
                rates[rung] = _rate(len(hits), len(observable), {r["question_id"] for r in hits})
            cell["rates"] = rates
            cell["by_class"] = OrderedDict()
            for klass in ("search-triggering", "informational"):
                subset = [r for r in collected if r["question_class"] == klass]
                klass_rates = OrderedDict()
                for rung in RATE_RUNGS:
                    observable = [r for r in subset if r[rung] != UNOBSERVABLE]
                    if subset and not observable:
                        klass_rates[rung] = UNOBSERVABLE
                        continue
                    hits = [r for r in observable if r[rung] is True]
                    klass_rates[rung] = _rate(len(hits), len(observable), {r["question_id"] for r in hits})
                cell["by_class"][klass] = klass_rates
            top = OrderedDict((level, 0) for level in ("cited", "linked", "named", "paraphrased-without-attribution", "none"))
            for r in collected:
                top[r["top_level"]] += 1
            cell["top_level"] = top
            cell["models"] = sorted({r["model"] for r in rows})
            cells.append(cell)
        return cells

    def _search_fractions(self, scored):
        """7.4: per question on each API cell, searched out of collected."""
        out = []
        groups = OrderedDict()
        for row in scored:
            if row["surface"] != "api" or row["status"] != "collected":
                continue
            groups.setdefault((row["site"], row["assistant"], row["arm"]), []).append(row)
        for (site, assistant, arm), rows in sorted(groups.items()):
            entry = OrderedDict(site=site, assistant=assistant, surface="api", arm=arm)
            observable = [r for r in rows if r["searched"] != UNOBSERVABLE]
            if not observable:
                entry["fractions"] = UNOBSERVABLE
                entry["variability_test"] = UNOBSERVABLE
                out.append(entry)
                continue
            per_question = OrderedDict()
            for question_id in sorted({r["question_id"] for r in observable}):
                mine = [r for r in observable if r["question_id"] == question_id]
                per_question[question_id] = OrderedDict(searched=sum(r["searched"] is True for r in mine), collected=len(mine))
            entry["fractions"] = per_question
            bimodal = sum(1 for q in per_question.values() if (q["searched"] / q["collected"]) <= BIMODAL_LOW or (q["searched"] / q["collected"]) >= BIMODAL_HIGH)
            share = bimodal / len(per_question)
            entry["bimodal_questions"] = bimodal
            entry["questions"] = len(per_question)
            entry["bimodal_share"] = round(share, 4)
            entry["variability_test"] = "holds" if share >= BIMODAL_SHARE else "fails"
            out.append(entry)
        return out

    def _measured_surface(self, scored, assistant, arm=None):
        """The assistant's primary surface (section 8), or the other surface if
        only that one was collected - an assistant with no key is collected by
        hand as its own app cell. `arm` restricts the search to one arm."""
        primary = R.PRIMARY_SURFACE[assistant]
        surfaces = {r["surface"] for r in scored if r["assistant"] == assistant and (arm is None or r["arm"] == arm)}
        if primary in surfaces:
            return primary
        if surfaces:
            return sorted(surfaces)[0]
        return None

    def _flip(self, scored):
        """7.7: F_a over the control site's questions in the baseline on each
        assistant's measured surface; the flag, and the indexed flip."""
        per_assistant = OrderedDict()
        fired_on = []
        measured = 0
        for assistant in R.ASSISTANTS:
            surface = self._measured_surface(scored, assistant, arm="baseline")
            entry = OrderedDict(surface=surface)
            if surface is None:
                entry["F"] = "not measured"
                per_assistant[assistant] = entry
                continue
            rows = [r for r in scored if r["assistant"] == assistant and r["surface"] == surface and r["arm"] == "baseline"
                    and self.questions[r["question_id"]]["site_role"] == "control" and r["status"] == "collected"
                    and r["searched"] != UNOBSERVABLE]
            if not rows:
                entry["F"] = UNOBSERVABLE if any(
                    r["assistant"] == assistant and r["surface"] == surface and r["arm"] == "baseline" for r in scored
                ) else "not measured"
                per_assistant[assistant] = entry
                continue
            measured += 1
            searched = sum(r["searched"] is True for r in rows)
            entry["searched"] = searched
            entry["collected"] = len(rows)
            entry["F"] = round(searched / len(rows), 4)
            entry["above_threshold"] = entry["F"] > FLIP_THRESHOLD
            if entry["above_threshold"]:
                fired_on.append(assistant)
            per_assistant[assistant] = entry
        if measured >= 3:
            fired = len(fired_on) >= 2
        else:
            fired = measured > 0 and len(fired_on) == measured
        indexed = self._indexed()
        treated_states = [entry["baseline"]["state"] for entry in indexed if entry["site_role"] == "treated"]
        indexed_flip = len(treated_states) == len(R.ENGINES) and all(s == "indexed" for s in treated_states)
        return OrderedDict(threshold=FLIP_THRESHOLD, per_assistant=per_assistant, measured=measured,
                           fired_on=fired_on, fired=fired, indexed_flip_fired=indexed_flip)

    def _indexed(self):
        """3.1: the state per domain per engine per arm, by the arm-date rule."""
        applied = self.arms["change_applied_on"]
        out = []
        for domain, role in R.SITES.items():
            for engine in R.ENGINES:
                mine = sorted((r for _, r in self.reports if r["domain"] == domain and r["engine"] == engine), key=lambda r: r["report_date"])
                entry = OrderedDict(domain=domain, site_role=role, engine=engine)
                if applied is None:
                    baseline = mine[-1] if mine else None
                    post = None
                else:
                    before = [r for r in mine if _date(r["report_date"]) <= _date(applied)]
                    after = [r for r in mine if _date(r["report_date"]) >= _date(applied) + datetime.timedelta(days=INDEXING_LAG_DAYS)]
                    baseline = before[-1] if before else None
                    post = after[-1] if after else None
                entry["baseline"] = self._indexed_state(baseline)
                entry["post_change"] = self._indexed_state(post)
                out.append(entry)
        return out

    @staticmethod
    def _indexed_state(report):
        if report is None:
            return OrderedDict(state="not-recorded", report_date=None)
        state = indexed_state(report)
        return OrderedDict(state=state, report_date=report["report_date"])

    def _guardrails(self, cells):
        """Section 10, per cell and per cell pair across arms."""
        by_key = {(c["site"], c["assistant"], c["surface"], c["arm"]): c for c in cells}
        out = []
        for cell in cells:
            share = (cell["n_refused"] + cell["n_failed"]) / cell["n_records"] if cell["n_records"] else 0.0
            entry = OrderedDict(site=cell["site"], assistant=cell["assistant"], surface=cell["surface"], arm=cell["arm"])
            entry["failure_share"] = round(share, 4)
            entry["thin"] = share > FAILURE_SHARE_MAX
            other_arm = "post-change" if cell["arm"] == "baseline" else "baseline"
            other = by_key.get((cell["site"], cell["assistant"], cell["surface"], other_arm))
            if other is None:
                entry["searched_move_pp"] = None
                entry["confounded"] = False
                entry["model_changed"] = False
            else:
                a, b = cell["rates"]["searched"], other["rates"]["searched"]
                if a == UNOBSERVABLE or b == UNOBSERVABLE:
                    entry["searched_move_pp"] = UNOBSERVABLE
                    entry["confounded"] = False
                else:
                    move = _pp(a["rate"], b["rate"])
                    entry["searched_move_pp"] = None if move is None else abs(move)
                    entry["confounded"] = move is not None and abs(move) >= SEARCHED_GUARDRAIL_PP
                entry["model_changed"] = cell["surface"] == "api" and cell["models"] != other["models"]
            entry["flags"] = [f for f in ("thin", "confounded", "model_changed") if entry[f]]
            out.append(entry)
        return out

    def _decisions(self, cells, guardrails):
        """7.6, per rung, per (assistant, surface): dT against dC."""
        by_key = {(c["site"], c["assistant"], c["surface"], c["arm"]): c for c in cells}
        flags = {(g["site"], g["assistant"], g["surface"], g["arm"]): g["flags"] for g in guardrails}
        pairs = sorted({(c["assistant"], c["surface"]) for c in cells})
        treated = next(d for d, role in R.SITES.items() if role == "treated")
        control = next(d for d, role in R.SITES.items() if role == "control")
        out = []
        for assistant, surface in pairs:
            four = {
                "T_base": by_key.get((treated, assistant, surface, "baseline")),
                "T_post": by_key.get((treated, assistant, surface, "post-change")),
                "C_base": by_key.get((control, assistant, surface, "baseline")),
                "C_post": by_key.get((control, assistant, surface, "post-change")),
            }
            withheld = sorted({f for key in four if four[key] for f in flags.get((four[key]["site"], assistant, surface, four[key]["arm"]), [])})
            for rung in OUTCOME_RUNGS:
                entry = OrderedDict(assistant=assistant, surface=surface, rung=rung)
                missing = [k for k, v in four.items() if v is None]
                if "T_base" in missing or "C_base" in missing:
                    entry["case"] = None
                    entry["reading"] = "no baseline" + (" (control)" if "T_base" not in missing else "")
                    out.append(entry)
                    continue
                if missing:
                    entry["case"] = None
                    entry["reading"] = "no post-change arm yet"
                    out.append(entry)
                    continue
                rates = {k: v["rates"][rung] for k, v in four.items()}
                if any(r == UNOBSERVABLE for r in rates.values()):
                    entry["case"] = None
                    entry["reading"] = UNOBSERVABLE
                    out.append(entry)
                    continue
                if any(r["rate"] is None for r in rates.values()):
                    entry["case"] = None
                    entry["reading"] = "a cell has no collected records"
                    out.append(entry)
                    continue
                dT = _pp(rates["T_base"]["rate"], rates["T_post"]["rate"])
                dC = _pp(rates["C_base"]["rate"], rates["C_post"]["rate"])
                questions = rates["T_post"]["distinct_questions"]
                entry["dT_pp"] = dT
                entry["dC_pp"] = dC
                entry["treated_post_distinct_questions"] = questions
                E, Q = SMALLEST_EFFECT_PP, MIN_DISTINCT_QUESTIONS
                all_zero = all(r["numerator"] == 0 for r in rates.values())
                if dT >= E and abs(dC) < E:
                    if questions >= Q:
                        entry["case"] = 1
                        entry["reading"] = "the change moved this rung on this assistant and surface: effect %.1f pp over %d questions" % (dT, questions)
                    else:
                        entry["case"] = None
                        entry["reading"] = "observed, below the smallest effect worth claiming: %.1f pp but the numerator spans %d question, fewer than %d" % (dT, questions, Q)
                elif abs(dT) < E and abs(dC) < E:
                    entry["case"] = 2
                    if all_zero:
                        entry["reading"] = "no detectable effect: at the floor in both arms (7.3 applies)"
                    elif dT == 0 and dC == 0:
                        entry["reading"] = "no detectable effect at this interval"
                    else:
                        entry["reading"] = "no detectable effect; observed, below the smallest effect worth claiming: dT %.1f pp, dC %.1f pp" % (dT, dC)
                elif dT >= E and dC >= E:
                    entry["case"] = 3
                    net = round(dT - dC, 4)
                    entry["dT_minus_dC_pp"] = net
                    reading = "drift - both moved, the change is not credited; dT - dC = %.1f pp" % net
                    if net >= E and questions >= Q:
                        reading += "; treated moved more than the control under drift (weaker claim)"
                    entry["reading"] = reading
                elif abs(dT) < E and abs(dC) >= E:
                    entry["case"] = 4
                    entry["reading"] = "not credited - the control moved (%.1f pp) and the treated site did not (%.1f pp): a finding about drift or the control's questions" % (dC, dT)
                else:
                    entry["case"] = None
                    entry["reading"] = "outside the four cases of 7.6: dT %.1f pp, dC %.1f pp - reported, not credited" % (dT, dC)
                if entry["case"] == 1 and withheld:
                    entry["verdict_withheld"] = withheld
                    entry["reading"] = "case 1 verdict withheld (%s): " % ", ".join(withheld) + entry["reading"]
                out.append(entry)
        return out

    def _verdicts(self, decisions, scored):
        """7.6: per assistant, the highest rung in case 1 on its measured
        surface with guardrails intact; and the one-line answer."""
        out = OrderedDict()
        moved = False
        for assistant in R.ASSISTANTS:
            surface = self._measured_surface(scored, assistant)
            entry = OrderedDict(surface=surface)
            if surface is None:
                entry["verdict"] = "not measured"
                out[assistant] = entry
                continue
            mine = [d for d in decisions if d["assistant"] == assistant and d["surface"] == surface]
            credited = [d["rung"] for d in mine if d.get("case") == 1 and not d.get("verdict_withheld")]
            if credited:
                highest = next(r for r in RUNG_STRENGTH if r in credited)
                entry["verdict"] = "case 1 at %s" % highest
                entry["highest_rung"] = highest
                moved = True
            elif all(d.get("reading", "").startswith("no baseline") for d in mine) and mine:
                entry["verdict"] = "no baseline"
            elif all(d.get("reading") == "no post-change arm yet" for d in mine) and mine:
                entry["verdict"] = "baseline only - no comparison yet"
            else:
                entry["verdict"] = "no rung in case 1"
            out[assistant] = entry
        out["decision"] = "the change moved the assistants" if moved else "the change is not shown to have moved the assistants"
        return out

    def _indexed_decisions(self, indexed):
        """7.6's indexed paragraph, per engine."""
        out = []
        for engine in R.ENGINES:
            treated = next(e for e in indexed if e["engine"] == engine and e["site_role"] == "treated")
            control = next(e for e in indexed if e["engine"] == engine and e["site_role"] == "control")
            entry = OrderedDict(engine=engine)
            states = [treated["baseline"]["state"], treated["post_change"]["state"], control["baseline"]["state"], control["post_change"]["state"]]
            if "not-recorded" in states:
                entry["reading"] = "not read - a report is missing on one side"
                out.append(entry)
                continue
            t_flip = states[0] == "not-indexed" and states[1] == "indexed"
            c_flip = states[2] == "not-indexed" and states[3] == "indexed"
            if t_flip and not c_flip and states[2] == states[3]:
                entry["case"] = 1
                entry["reading"] = "the treated domain flipped to indexed while the control's state was unchanged"
            elif not t_flip and not c_flip:
                entry["case"] = 2
                entry["reading"] = "neither domain flipped"
            elif t_flip and c_flip:
                entry["case"] = 3
                entry["reading"] = "both domains flipped - the engine found both; not credited to the change"
            else:
                entry["case"] = 4
                entry["reading"] = "not credited - the control flipped or changed and the treated domain did not"
            out.append(entry)
        return out


def indexed_state(report):
    """3.1: `indexed` when homepage_indexed is true or indexed_pages is at least
    1; `not-indexed` when the property is verified and both say otherwise. An
    unverified property's console has recorded nothing, so `not-recorded`."""
    if report["homepage_indexed"] is True or (isinstance(report["indexed_pages"], int) and report["indexed_pages"] >= 1):
        return "indexed"
    if report["property_verified"] is True:
        return "not-indexed"
    return "not-recorded"


def check_i11(levels, where, errors):
    """I11: paraphrased_without_attribution is never true beside a true named,
    linked or cited. The scorer derives all four, so a stored record cannot
    violate this; the check guards the scorer's own derivation."""
    if levels["paraphrased_without_attribution"] is True and any(levels[k] is True for k in ("named", "linked", "cited")):
        errors.append(RecordError("I11", where, "paraphrased_without_attribution is true beside a true named, linked or cited"))
        return False
    return True


# --- rendering ---------------------------------------------------------------


def _fmt_rate(value):
    if value == UNOBSERVABLE:
        return "unobservable"
    if value["denominator"] == 0:
        return "no collected records"
    return "%d/%d (%.1f%%) over %d question%s" % (
        value["numerator"], value["denominator"], value["rate"] * 100.0, value["distinct_questions"],
        "" if value["distinct_questions"] == 1 else "s",
    )


def render(report):
    """The report as text for a person. Counts and rates only - never a
    response text, so a log of this can be read anywhere."""
    lines = []
    if report["errors"]:
        lines.append("REFUSED - %d record(s) or report(s) fail an invariant of section 9:" % len(report["errors"]))
        lines.extend("  " + e for e in report["errors"])
        lines.append("")
    for warning in report["warnings"]:
        lines.append("warning: " + warning)
    if report["generic_fingerprints"]:
        lines.append("generic fingerprints excluded in both arms (3.7): %d" % len(report["generic_fingerprints"]))
    lines.append("== Cells (site, assistant, surface, arm) - section 4 ==")
    if not report["cells"]:
        lines.append("  no records")
    for cell in report["cells"]:
        lines.append("%s | %s | %s | %s" % (cell["site"], cell["assistant"], cell["surface"], cell["arm"]))
        lines.append("  n_records=%d n_collected=%d n_refused=%d n_failed=%d distinct_questions=%d" % (
            cell["n_records"], cell["n_collected"], cell["n_refused"], cell["n_failed"], cell["distinct_questions"]))
        for rung, value in cell["rates"].items():
            lines.append("  %-32s %s" % (rung + " rate", _fmt_rate(value)))
        lines.append("  top_level: " + ", ".join("%s=%d" % kv for kv in cell["top_level"].items()))
        lines.append("  model(s): " + ", ".join(cell["models"]))
    lines.append("")
    lines.append("== Indexed state per domain per engine per arm - 3.1 ==")
    for entry in report["indexed"]:
        lines.append("%s | %s: baseline %s (%s), post-change %s (%s)" % (
            entry["domain"], entry["engine"], entry["baseline"]["state"], entry["baseline"]["report_date"] or "-",
            entry["post_change"]["state"], entry["post_change"]["report_date"] or "-"))
    for entry in report["indexed_decisions"]:
        lines.append("  %s: %s" % (entry["engine"], entry["reading"]))
    lines.append("")
    lines.append("== Per-question search fraction on API cells - 7.4 ==")
    if not report["search_fractions"]:
        lines.append("  no API cells")
    for entry in report["search_fractions"]:
        if entry["fractions"] == UNOBSERVABLE:
            lines.append("%s | %s | api | %s: searched unobservable on this surface" % (entry["site"], entry["assistant"], entry["arm"]))
            continue
        fractions = " ".join("%s=%d/%d" % (q, v["searched"], v["collected"]) for q, v in entry["fractions"].items())
        lines.append("%s | %s | api | %s: %s" % (entry["site"], entry["assistant"], entry["arm"], fractions))
        lines.append("  variability test %s: %d of %d questions bimodal (%.0f%%, needs %.0f%%)" % (
            entry["variability_test"], entry["bimodal_questions"], entry["questions"], entry["bimodal_share"] * 100, BIMODAL_SHARE * 100))
    lines.append("")
    flip = report["flip"]
    lines.append("== Flip condition - 7.7 (threshold F_a > %.2f) ==" % flip["threshold"])
    for assistant, entry in flip["per_assistant"].items():
        if isinstance(entry["F"], float):
            lines.append("  F_%s = %d/%d = %.2f on %s%s" % (assistant, entry["searched"], entry["collected"], entry["F"], entry["surface"],
                                                           " - above threshold" if entry["above_threshold"] else ""))
        else:
            lines.append("  F_%s = %s" % (assistant, entry["F"]))
    lines.append("  flip flag %s (%d assistant(s) measured, above threshold on: %s)" % (
        "FIRED" if flip["fired"] else "did not fire", flip["measured"], ", ".join(flip["fired_on"]) or "none"))
    lines.append("  indexed flip (treated domain indexed on both engines in the baseline) %s" % ("FIRED" if flip["indexed_flip_fired"] else "did not fire"))
    lines.append("")
    lines.append("== Guardrails - section 10 ==")
    for entry in report["guardrails"]:
        move = entry["searched_move_pp"]
        move_text = "no other arm" if move is None else ("unobservable" if move == UNOBSERVABLE else "%.1f pp" % move)
        lines.append("%s | %s | %s | %s: failure share %.1f%%%s; searched move %s%s%s" % (
            entry["site"], entry["assistant"], entry["surface"], entry["arm"], entry["failure_share"] * 100,
            " THIN" if entry["thin"] else "", move_text, " CONFOUNDED" if entry["confounded"] else "",
            "; MODEL CHANGED between arms" if entry["model_changed"] else ""))
    lines.append("")
    lines.append("== Decision rule per rung per (assistant, surface) - 7.6 ==")
    if not report["decisions"]:
        lines.append("  no cells")
    for entry in report["decisions"]:
        case = "case %d" % entry["case"] if entry.get("case") else "-"
        lines.append("%s | %s | %-32s %s: %s" % (entry["assistant"], entry["surface"], entry["rung"], case, entry["reading"]))
    lines.append("")
    lines.append("== Overall verdict per assistant ==")
    for assistant in R.ASSISTANTS:
        entry = report["verdicts"][assistant]
        lines.append("  %s (%s): %s" % (assistant, entry["surface"] or "-", entry["verdict"]))
    lines.append("  " + report["verdicts"]["decision"])
    return "\n".join(lines) + "\n"
