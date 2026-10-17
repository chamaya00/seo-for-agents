"""The record shape of section 11.1 and the checks a single record must pass.

Nothing here reads the network or scores a rung. It is the part of the
framework a response file has to satisfy before it is counted: every field
present (I2), the right type in each, `null` and `"unobservable"` only where
the field list allows them.
"""

import json
import re

FRAMEWORK = "docs/measurement/4-measurement-framework.md"

ASSISTANTS = ("chatgpt", "gemini", "claude")
SURFACES = ("api", "app")
ARMS = ("baseline", "post-change")
STATUSES = ("collected", "refused", "failed")
SITES = {"launchyourfirstwebsite.com": "treated", "levelupsql.com": "control"}
ENGINES = ("google-search-console", "bing-webmaster-tools")

# The surface each assistant is measured on first (section 8). Used for the
# flip condition (7.7) and the overall verdict (7.6).
PRIMARY_SURFACE = {"gemini": "api", "claude": "api", "chatgpt": "app"}

UNOBSERVABLE = "unobservable"

# Section 11.1, in order. Each entry: (name, checker). A checker returns None
# when the value is acceptable and a short reason otherwise.


def _is_str(v):
    return isinstance(v, str)


def _one_of(*options):
    def check(v):
        return None if v in options else "must be one of %s" % ", ".join(repr(o) for o in options)
    return check


def _string(v):
    return None if _is_str(v) else "must be a string"


def _string_or_null(v):
    return None if v is None or _is_str(v) else "must be a string or null"


def _int_or_null(v):
    return None if v is None or (isinstance(v, int) and not isinstance(v, bool)) else "must be an integer or null"


def _number_or_null(v):
    return None if v is None or (isinstance(v, (int, float)) and not isinstance(v, bool)) else "must be a number or null"


def _bool_or_null(v):
    return None if v is None or isinstance(v, bool) else "must be a boolean or null"


def _positive_int(v):
    if isinstance(v, int) and not isinstance(v, bool) and v >= 1:
        return None
    return "must be an integer of 1 or more"


_ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def _utc_timestamp(v):
    if _is_str(v) and _ISO_UTC.match(v):
        return None
    return "must be an ISO 8601 UTC timestamp ending in Z"


def _collector(v):
    if _is_str(v) and (v == "owner" or v.startswith("workflow:")):
        return None
    return 'must be "owner" or "workflow:<GITHUB_RUN_ID>"'


def _bool_or_unobservable(v):
    return None if isinstance(v, bool) or v == UNOBSERVABLE else 'must be true, false or "unobservable"'


def _retrieved_set(v):
    if v == UNOBSERVABLE:
        return None
    if not isinstance(v, list):
        return 'must be an array or "unobservable"'
    for item in v:
        if not isinstance(item, dict) or not _is_str(item.get("url")):
            return 'every item must be {"url": string, "title": string or null}'
        if "title" in item and item["title"] is not None and not _is_str(item["title"]):
            return 'every item must be {"url": string, "title": string or null}'
    return None


def _cited_urls(v):
    if v == UNOBSERVABLE:
        return None
    if not isinstance(v, list):
        return 'must be an array or "unobservable"'
    for item in v:
        if _is_str(item):
            continue
        if isinstance(item, dict) and _is_str(item.get("url")):
            continue
        return 'every item must be a URL string or {"url": string, "title": string or null}'
    return None


def _raw_response(v):
    return None if isinstance(v, (dict, str, list)) else "must be an object or a string"


def _string_list(v):
    if isinstance(v, list) and all(_is_str(s) for s in v):
        return None
    return "must be an array of strings"


SETTINGS_FIELDS = (
    ("web_tool", _string),
    ("tool_version", _string_or_null),
    ("dynamic_threshold", _number_or_null),
    ("max_uses", _int_or_null),
    ("system_prompt", _string_or_null),
    ("temperature", _number_or_null),
    ("logged_in", _bool_or_null),
    ("temporary_chat", _bool_or_null),
    ("search_forced", _bool_or_null),
    ("region", None),  # checked by _region below
    ("runner_label", _string_or_null),
)

# The settings keys copied from a row of data/collection-settings.json. `region`
# and `runner_label` are added by whoever collects.
SETTINGS_ROW_FIELDS = tuple(name for name, _ in SETTINGS_FIELDS if name not in ("region", "runner_label"))


def _region(v):
    if not isinstance(v, dict):
        return 'must be {"source": "actions-runner" | "owner", "value": string}'
    if v.get("source") not in ("actions-runner", "owner"):
        return 'source must be "actions-runner" or "owner"'
    if not _is_str(v.get("value")):
        return "value must be a string"
    return None


def _settings(v):
    if not isinstance(v, dict):
        return "must be an object"
    for name, checker in SETTINGS_FIELDS:
        if name not in v:
            return "missing settings.%s" % name
        reason = _region(v[name]) if name == "region" else checker(v[name])
        if reason:
            return "settings.%s %s" % (name, reason)
    return None


RECORD_FIELDS = (
    ("schema_version", _one_of("1")),
    ("record_type", _one_of("response")),
    ("arm", _one_of(*ARMS)),
    ("site", _one_of(*SITES)),
    ("site_role", _one_of("treated", "control")),
    ("question_id", _string),
    ("question_text", _string),
    ("question_class", _one_of("search-triggering", "informational")),
    ("assistant", _one_of(*ASSISTANTS)),
    ("surface", _one_of(*SURFACES)),
    ("repeat_index", _positive_int),
    ("collected_at", _utc_timestamp),
    ("collector", _collector),
    ("model", _string),
    ("settings", _settings),
    ("status", _string),  # which of the three it is belongs to I9, so the counts add up
    ("failure_detail", _string_or_null),
    ("response_text", _string),
    ("searched", _bool_or_unobservable),
    ("searched_evidence", _string_or_null),
    ("retrieved_set", _retrieved_set),
    ("cited_urls", _cited_urls),
    ("raw_response", _raw_response),
    ("screenshots", _string_list),
    ("notes", _string_or_null),
)

RECORD_FIELD_NAMES = tuple(name for name, _ in RECORD_FIELDS)


class RecordError(Exception):
    """A record or report that fails an invariant. `invariant` is the id from
    section 9 and `where` names the file."""

    def __init__(self, invariant, where, message):
        super().__init__("%s: %s: %s" % (invariant, where, message))
        self.invariant = invariant
        self.where = where
        self.message = message


def check_fields(record, where):
    """I2: every field of 11.1 present with an admissible value. Raises RecordError."""
    if not isinstance(record, dict):
        raise RecordError("I2", where, "record is not a JSON object")
    for name, checker in RECORD_FIELDS:
        if name not in record:
            raise RecordError("I2", where, "missing field %s" % name)
        reason = checker(record[name])
        if reason:
            raise RecordError("I2", where, "field %s %s" % (name, reason))
    if record["model"] == "unknown" and record["surface"] != "app":
        raise RecordError("I2", where, 'field model may be "unknown" only when surface is "app"')
    if record["searched"] == UNOBSERVABLE and record["searched_evidence"] is not None:
        raise RecordError("I2", where, "field searched_evidence must be null when searched is unobservable")


def record_key(record):
    """I1: the key a repeat must not duplicate."""
    return (record["arm"], record["assistant"], record["surface"], record["question_id"], record["repeat_index"])


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_question_set(path):
    """data/question-set.json as a dict keyed by question_id, in file order."""
    rows = load_json(path)
    if not isinstance(rows, list):
        raise ValueError("%s: expected an array of question rows" % path)
    questions = {}
    for row in rows:
        for field in ("question_id", "site", "site_role", "question_class", "class_reason", "text"):
            if field not in row:
                raise ValueError("%s: question row missing %s" % (path, field))
        if row["site"] not in SITES or SITES[row["site"]] != row["site_role"]:
            raise ValueError("%s: question %s: site %r is not a site of this framework" % (path, row["question_id"], row["site"]))
        if row["question_id"] in questions:
            raise ValueError("%s: duplicate question_id %s" % (path, row["question_id"]))
        questions[row["question_id"]] = row
    return questions


def load_settings(path):
    """data/collection-settings.json: {assistant: {surface: row}}."""
    settings = load_json(path)
    for assistant in ASSISTANTS:
        if assistant not in settings:
            raise ValueError("%s: no row for %s" % (path, assistant))
        for surface in SURFACES:
            row = settings[assistant].get(surface)
            if not isinstance(row, dict):
                raise ValueError("%s: no %s/%s row" % (path, assistant, surface))
            if "model" not in row:
                raise ValueError("%s: %s/%s row has no model field" % (path, assistant, surface))
            for name in SETTINGS_ROW_FIELDS:
                if name not in row:
                    raise ValueError("%s: %s/%s row has no %s field" % (path, assistant, surface, name))
    return settings


def load_arms(path):
    arms = load_json(path)
    for field in ("change_applied_on", "baseline", "post_change"):
        if field not in arms:
            raise ValueError("%s: missing %s" % (path, field))
    for field in ("opened", "closed"):
        if field not in arms["baseline"]:
            raise ValueError("%s: baseline missing %s" % (path, field))
    for field in ("opens", "closed"):
        if field not in arms["post_change"]:
            raise ValueError("%s: post_change missing %s" % (path, field))
    return arms
