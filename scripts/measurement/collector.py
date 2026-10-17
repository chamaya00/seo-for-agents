"""The API collector - section 11.4's workflow contract.

Runs inside a workflow_dispatch workflow on a GitHub Actions runner (O6):
non-interactive, arguments on the command line, one key read from one named
environment variable, output written only under the directory it is given
(I12). Every request is a fresh single-turn conversation carrying the question
text verbatim and nothing else; collection runs in rounds - repeat 1 of every
question, then repeat 2 (section 8, 11.4).

Failure (I15): no key exits before anything is written and points at the
manual protocol; a first request that cannot reach the host exits with a
different error and writes nothing; once the host has answered, a request that
fails is written as a `failed` record and the run continues, exiting non-zero
at the end. The log carries counts, never a key, a body or a response text.
"""

import datetime
import json
import os
import socket
import urllib.error
import urllib.request

from . import records as R
from .records import UNOBSERVABLE

KEY_VARIABLES = {"gemini": "GEMINI_API_KEY", "claude": "ANTHROPIC_API_KEY", "chatgpt": "OPENAI_API_KEY"}

ENDPOINTS = {
    "claude": "https://api.anthropic.com/v1/messages",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    "chatgpt": "https://api.openai.com/v1/responses",
}
ANTHROPIC_VERSION = "2023-06-01"
# The vendor requires a ceiling on the reply; it is not a setting section 8
# holds constant, so it is a constant here rather than a settings field.
CLAUDE_MAX_TOKENS = 4096
GEMINI_TOOLS = ("google_search", "google_search_retrieval")

# Exit codes. 1 is "ran, some records failed"; the rest wrote nothing.
EXIT_FAILED_RECORDS = 1
EXIT_CONFIG = 2
EXIT_UNREACHABLE = 3
EXIT_KEY_REJECTED = 4


class CollectorError(Exception):
    """A run that stops before writing anything. `name` is the error class the
    log and the exit message carry."""

    def __init__(self, name, exit_code, message):
        super().__init__("%s: %s" % (name, message))
        self.name = name
        self.exit_code = exit_code


class TransportError(Exception):
    """One request that did not come back with a body. `kind` is one of
    `unreachable`, `timeout`, `http`; `status` is set for `http`."""

    def __init__(self, kind, detail, status=None):
        super().__init__("%s: %s" % (kind, detail))
        self.kind = kind
        self.detail = detail
        self.status = status


class UrllibTransport:
    """POST a JSON body and return (status, parsed body). The only place the
    network is touched; tests replace it with a stub."""

    def __init__(self, timeout):
        self.timeout = timeout

    def post(self, url, headers, body):
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                payload = error.read().decode("utf-8", "replace")
            except OSError:
                payload = ""
            raise TransportError("http", "HTTP %d %s: %s" % (error.code, error.reason, payload[:500]), status=error.code)
        except urllib.error.URLError as error:
            reason = error.reason
            if isinstance(reason, (socket.timeout, TimeoutError)):
                raise TransportError("timeout", "request timed out after %ss" % self.timeout)
            raise TransportError("unreachable", "cannot reach host: %s" % reason)
        except (socket.timeout, TimeoutError):
            raise TransportError("timeout", "request timed out after %ss" % self.timeout)
        except (ConnectionError, OSError) as error:
            raise TransportError("unreachable", "cannot reach host: %s" % error)
        except ValueError as error:
            raise TransportError("http", "response body was not JSON: %s" % error, status=200)


# --- one adapter per assistant: request shape in, the 11.1 fields out ---------


def _host_of(url):
    return url.split("//", 1)[-1].split("/", 1)[0]


class ClaudeAdapter:
    assistant = "claude"

    def __init__(self, row):
        self.row = row

    def url(self):
        return ENDPOINTS["claude"]

    def headers(self, key):
        return {"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json"}

    def body(self, text):
        # No `system`, no `user_location`, no `allowed_domains`, no
        # `blocked_domains` (I6, section 8): the trigger is not steered.
        return {
            "model": self.row["model"],
            "max_tokens": CLAUDE_MAX_TOKENS,
            "messages": [{"role": "user", "content": text}],
            "tools": [{"type": self.row["tool_version"], "name": self.row["web_tool"], "max_uses": self.row["max_uses"]}],
        }

    def parse(self, body):
        content = body.get("content") or []
        text = "".join(block.get("text", "") for block in content if block.get("type") == "text")
        searched = any(block.get("type") == "server_tool_use" and block.get("name") == "web_search" for block in content)
        retrieved = []
        for block in content:
            if block.get("type") != "web_search_tool_result":
                continue
            items = block.get("content")
            if not isinstance(items, list):
                continue  # a web_search_tool_result_error object: nothing was returned
            for item in items:
                if item.get("type") == "web_search_result" and isinstance(item.get("url"), str):
                    retrieved.append({"url": item["url"], "title": item.get("title")})
        cited = []
        for block in content:
            if block.get("type") != "text":
                continue
            for citation in block.get("citations") or []:
                if citation.get("type") == "web_search_result_location" and isinstance(citation.get("url"), str):
                    cited.append(citation["url"])
        parsed = {
            "model": body.get("model"),
            "response_text": text,
            "searched": searched,
            "searched_evidence": 'content[].type == "server_tool_use" and name == "web_search"' if searched else None,
            "retrieved_set": retrieved,
            "cited_urls": cited,
        }
        if body.get("stop_reason") == "refusal":
            parsed["status"], parsed["failure_detail"] = "refused", "stop_reason refusal"
        elif not text:
            parsed["status"], parsed["failure_detail"] = "failed", "empty response_text with stop_reason %r" % body.get("stop_reason")
        else:
            parsed["status"], parsed["failure_detail"] = "collected", None
        return parsed


class GeminiAdapter:
    assistant = "gemini"
    REFUSAL_REASONS = ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION")

    def __init__(self, row):
        self.row = row

    def url(self):
        return ENDPOINTS["gemini"].format(model=self.row["model"])

    def headers(self, key):
        return {"x-goog-api-key": key, "content-type": "application/json"}

    def tool(self):
        if self.row["web_tool"] == "google_search":
            return {"google_search": {}}
        return {"google_search_retrieval": {"dynamic_retrieval_config": {"mode": "MODE_DYNAMIC", "dynamic_threshold": self.row["dynamic_threshold"]}}}

    def body(self, text):
        return {"contents": [{"role": "user", "parts": [{"text": text}]}], "tools": [self.tool()]}

    def parse(self, body):
        candidates = body.get("candidates") or []
        candidate = candidates[0] if candidates else {}
        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts if isinstance(part.get("text"), str))
        grounding = candidate.get("groundingMetadata") or {}
        queries = grounding.get("webSearchQueries") or []
        searched = bool(queries)
        chunks = grounding.get("groundingChunks") or []
        retrieved = []
        for chunk in chunks:
            web = chunk.get("web") or {}
            if isinstance(web.get("uri"), str):
                retrieved.append({"url": web["uri"], "title": web.get("title")})
            else:
                retrieved.append({"url": "", "title": web.get("title")})
        referenced = []
        for support in grounding.get("groundingSupports") or []:
            for index in support.get("groundingChunkIndices") or []:
                if isinstance(index, int) and 0 <= index < len(chunks) and index not in referenced:
                    referenced.append(index)
        cited = [retrieved[i] for i in referenced]
        parsed = {
            "model": body.get("modelVersion"),
            "response_text": text,
            "searched": searched,
            "searched_evidence": "candidates[0].groundingMetadata.webSearchQueries" if searched else None,
            "retrieved_set": retrieved,
            "cited_urls": cited,
        }
        block_reason = (body.get("promptFeedback") or {}).get("blockReason")
        finish = candidate.get("finishReason")
        if block_reason or finish in self.REFUSAL_REASONS:
            parsed["status"], parsed["failure_detail"] = "refused", "blockReason %r, finishReason %r" % (block_reason, finish)
        elif not text:
            parsed["status"], parsed["failure_detail"] = "failed", "empty response_text with finishReason %r" % finish
        else:
            parsed["status"], parsed["failure_detail"] = "collected", None
        return parsed


class OpenAIAdapter:
    """The Responses API. Which output item records a search, the retrieved set
    and the URL annotations are unconfirmed (#3, framework 3.2, 16), so the
    three rungs are stored "unobservable" and the body verbatim for re-scoring."""

    assistant = "chatgpt"

    def __init__(self, row):
        self.row = row

    def url(self):
        return ENDPOINTS["chatgpt"]

    def headers(self, key):
        return {"Authorization": " ".join(("Bearer", key)), "content-type": "application/json"}

    def body(self, text):
        return {"model": self.row["model"], "input": text, "tools": [{"type": self.row["tool_version"]}]}

    def parse(self, body):
        text_parts = []
        refusal = None
        for item in body.get("output") or []:
            if item.get("type") != "message":
                continue
            for part in item.get("content") or []:
                if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    text_parts.append(part["text"])
                elif part.get("type") == "refusal":
                    refusal = part.get("refusal") or "refusal"
        text = "".join(text_parts)
        parsed = {
            "model": body.get("model"),
            "response_text": text,
            "searched": UNOBSERVABLE,
            "searched_evidence": None,
            "retrieved_set": UNOBSERVABLE,
            "cited_urls": UNOBSERVABLE,
        }
        if refusal and not text:
            parsed["status"], parsed["failure_detail"] = "refused", "refusal: %s" % refusal
        elif not text:
            parsed["status"], parsed["failure_detail"] = "failed", "empty response_text with status %r" % body.get("status")
        else:
            parsed["status"], parsed["failure_detail"] = "collected", None
        return parsed


ADAPTERS = {"claude": ClaudeAdapter, "gemini": GeminiAdapter, "chatgpt": OpenAIAdapter}


def check_pinned(row, assistant, settings_path):
    """A null the driver has to fill before the baseline (11.8) stops the run
    before any request, naming the field."""
    where = "%s: %s/api/" % (settings_path, assistant)
    if row.get("model") is None:
        raise CollectorError("unpinned-setting", EXIT_CONFIG, where + "model is null - pin the exact model id before the baseline")
    if assistant in ("claude", "chatgpt") and row.get("tool_version") is None:
        raise CollectorError("unpinned-setting", EXIT_CONFIG, where + "tool_version is null - pin the web search tool type string before the baseline")
    if assistant == "gemini":
        if row.get("web_tool") not in GEMINI_TOOLS:
            raise CollectorError("unpinned-setting", EXIT_CONFIG, where + "web_tool must be one of %s" % ", ".join(GEMINI_TOOLS))
        if row["web_tool"] == "google_search_retrieval" and not isinstance(row.get("dynamic_threshold"), (int, float)):
            raise CollectorError("unpinned-setting", EXIT_CONFIG, where + "dynamic_threshold must be a number for google_search_retrieval")


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _redact(text, key):
    return text.replace(key, "<redacted>") if key and text else text


class Collector:
    def __init__(self, question_set_path, settings_path, assistant, repeats, arm, out_dir, env, transport, log=print, clock=utc_now):
        self.assistant = assistant
        self.repeats = repeats
        self.arm = arm
        self.out_dir = out_dir
        self.env = env
        self.transport = transport
        self.log = log
        self.clock = clock
        self.settings_path = settings_path
        self.questions = R.load_question_set(question_set_path)
        settings = R.load_settings(settings_path)
        self.row = settings[assistant]["api"]
        self.adapter = ADAPTERS[assistant](self.row)

    # -- preflight: everything that stops the run before a request -----------

    def preflight(self):
        check_pinned(self.row, self.assistant, self.settings_path)
        variable = KEY_VARIABLES[self.assistant]
        key = self.env.get(variable)
        if not key:
            raise CollectorError(
                "missing-key", EXIT_CONFIG,
                "environment variable %s is not set. Nothing was written. Collect %s by the manual protocol in section 11.3 of %s, "
                "or set the repository secret of that name and re-run." % (variable, self.assistant, R.FRAMEWORK))
        run_id = self.env.get("GITHUB_RUN_ID")
        if not run_id:
            raise CollectorError("missing-run-id", EXIT_CONFIG, "GITHUB_RUN_ID is not set; the collector runs inside a workflow_dispatch workflow (O6) and records collector: workflow:<GITHUB_RUN_ID>")
        for repeat, question in self.plan():
            path = self.path_for(question["question_id"], repeat)
            if os.path.exists(path):
                raise CollectorError("would-overwrite", EXIT_CONFIG, "%s exists; a file is never overwritten (I1). Nothing was written." % path)
        return key, run_id

    def plan(self):
        """Rounds: repeat 1 of every question in file order, then repeat 2."""
        for repeat in range(1, self.repeats + 1):
            for question in self.questions.values():
                yield repeat, question

    def path_for(self, question_id, repeat):
        return os.path.join(self.out_dir, self.assistant, "api", "%s-r%02d.json" % (question_id, repeat))

    def settings_for_record(self):
        settings = {name: self.row[name] for name in R.SETTINGS_ROW_FIELDS}
        settings["region"] = {"source": "actions-runner", "value": self.env.get("RUNNER_REGION") or "unknown"}
        settings["runner_label"] = self.env.get("RUNNER_LABEL") or self.env.get("RUNNER_OS") or None
        return settings

    # -- the run ----------------------------------------------------------------

    def run(self):
        key, run_id = self.preflight()
        total = len(self.questions) * self.repeats
        self.log("collector: assistant=%s arm=%s questions=%d repeats=%d requests=%d out=%s" % (
            self.assistant, self.arm, len(self.questions), self.repeats, total, self.out_dir))
        counts = {"collected": 0, "refused": 0, "failed": 0}
        host_answered = False
        current_round = 0
        round_counts = None
        for repeat, question in self.plan():
            if repeat != current_round:
                if round_counts is not None:
                    self.log("round %d: collected=%d refused=%d failed=%d" % (current_round, round_counts["collected"], round_counts["refused"], round_counts["failed"]))
                current_round, round_counts = repeat, {"collected": 0, "refused": 0, "failed": 0}
            collected_at = self.clock()
            try:
                status, body = self.transport.post(self.adapter.url(), self.adapter.headers(key), self.adapter.body(question["text"]))
                host_answered = True
                parsed = self.adapter.parse(body)
                raw = body
            except TransportError as error:
                if not host_answered:
                    if error.kind == "unreachable":
                        raise CollectorError("unreachable", EXIT_UNREACHABLE, "the first request could not reach %s (%s). Nothing was written; the runner "
                                             "has observed nothing about the assistant." % (_host_of(self.adapter.url()), _redact(error.detail, key)))
                    if error.kind == "http" and error.status in (401, 403):
                        raise CollectorError("key-rejected", EXIT_KEY_REJECTED, "%s rejected %s on the first request (HTTP %d). Nothing was written." % (
                            _host_of(self.adapter.url()), KEY_VARIABLES[self.assistant], error.status))
                if error.kind == "http":
                    host_answered = True
                parsed = self.failed_fields(_redact("%s: %s" % (error.kind, error.detail), key))
                raw = {"error": parsed["failure_detail"]}
            record = self.record(question, repeat, collected_at, run_id, parsed, raw)
            self.write(record)
            counts[record["status"]] += 1
            round_counts[record["status"]] += 1
        if round_counts is not None:
            self.log("round %d: collected=%d refused=%d failed=%d" % (current_round, round_counts["collected"], round_counts["refused"], round_counts["failed"]))
        self.log("done: records=%d collected=%d refused=%d failed=%d under %s" % (total, counts["collected"], counts["refused"], counts["failed"], self.out_dir))
        return EXIT_FAILED_RECORDS if counts["failed"] else 0

    def failed_fields(self, detail):
        unobservable = self.assistant == "chatgpt"
        return {
            "model": None,
            "status": "failed",
            "failure_detail": detail,
            "response_text": "",
            "searched": UNOBSERVABLE if unobservable else False,
            "searched_evidence": None,
            "retrieved_set": UNOBSERVABLE if unobservable else [],
            "cited_urls": UNOBSERVABLE if unobservable else [],
        }

    def record(self, question, repeat, collected_at, run_id, parsed, raw):
        return {
            "schema_version": "1",
            "record_type": "response",
            "arm": self.arm,
            "site": question["site"],
            "site_role": question["site_role"],
            "question_id": question["question_id"],
            "question_text": question["text"],
            "question_class": question["question_class"],
            "assistant": self.assistant,
            "surface": "api",
            "repeat_index": repeat,
            "collected_at": collected_at,
            "collector": "workflow:%s" % run_id,
            "model": parsed["model"] or self.row["model"],
            "settings": self.settings_for_record(),
            "status": parsed["status"],
            "failure_detail": parsed["failure_detail"],
            "response_text": parsed["response_text"],
            "searched": parsed["searched"],
            "searched_evidence": parsed["searched_evidence"],
            "retrieved_set": parsed["retrieved_set"],
            "cited_urls": parsed["cited_urls"],
            "raw_response": raw,
            "screenshots": [],
            "notes": None,
        }

    def write(self, record):
        path = self.path_for(record["question_id"], record["repeat_index"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            raise CollectorError("would-overwrite", EXIT_CONFIG, "%s appeared during the run; a file is never overwritten (I1)" % path)
        with open(path, "x", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
