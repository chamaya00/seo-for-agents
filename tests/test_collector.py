"""Criteria 3 and 4: the collector against a stubbed HTTP layer. No test here
makes a live call; the stub is the only transport, and a test that reached
the network would fail on the stub's request log being empty."""

import contextlib
import copy
import io
import json
import os
import shutil
import tempfile
import unittest

from support import DATA, QUESTIONS, read_json, write_json

import collect
import score
from measurement import records
from measurement.collector import KEY_VARIABLES, TransportError

# A key value used only inside the stub's environment. It is not a credential;
# it is the string the tests look for to prove nothing leaks.
FAKE_KEY = "fake-key-for-stub-only-0000"
RUN_ENV = {"GITHUB_RUN_ID": "987654321", "RUNNER_LABEL": "ubuntu-latest"}
VENDOR_HOST = {"claude": "api.anthropic.com", "gemini": "generativelanguage.googleapis.com", "chatgpt": "api.openai.com"}
ANSWER = "A beginner can be online for under 50 dollars a year with shared hosting."


def claude_body(text=ANSWER):
    return {
        "id": "msg_01", "type": "message", "role": "assistant", "model": "claude-echoed-model-id", "stop_reason": "end_turn",
        "content": [
            {"type": "server_tool_use", "id": "srvtoolu_01", "name": "web_search", "input": {"query": "cheapest website hosting"}},
            {"type": "web_search_tool_result", "tool_use_id": "srvtoolu_01", "content": [
                {"type": "web_search_result", "url": "https://www.hostinger.com/tutorials/cheap", "title": "Hostinger", "encrypted_content": "x", "page_age": None},
                {"type": "web_search_result", "url": "https://launchyourfirstwebsite.com/hosting", "title": "Hosting", "encrypted_content": "y", "page_age": None},
            ]},
            {"type": "text", "text": text, "citations": [
                {"type": "web_search_result_location", "url": "https://www.hostinger.com/tutorials/cheap", "title": "Hostinger", "cited_text": "...", "encrypted_index": "z"},
            ]},
        ],
    }


def gemini_body(text=ANSWER):
    return {
        "candidates": [{
            "content": {"role": "model", "parts": [{"text": text}]},
            "finishReason": "STOP",
            "groundingMetadata": {
                "webSearchQueries": ["cheapest way to host a website"],
                "groundingChunks": [
                    {"web": {"uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc", "title": "hostinger.com"}},
                    {"web": {"uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/def", "title": "launchyourfirstwebsite.com"}},
                ],
                "groundingSupports": [{"segment": {"startIndex": 0, "endIndex": 40, "text": "A beginner"}, "groundingChunkIndices": [1], "confidenceScores": [0.9]}],
            },
        }],
        "modelVersion": "gemini-echoed-model-id",
    }


def openai_body(text=ANSWER):
    return {
        "id": "resp_01", "object": "response", "model": "gpt-echoed-model-id", "status": "completed",
        "output": [
            {"type": "web_search_call", "id": "ws_01", "status": "completed"},
            {"type": "message", "id": "msg_01", "role": "assistant", "content": [{"type": "output_text", "text": text, "annotations": []}]},
        ],
    }


VENDOR_BODY = {"claude": claude_body, "gemini": gemini_body, "chatgpt": openai_body}


class StubTransport:
    """Answers each request from `script`, a list of callables or bodies in
    request order; a TransportError in the list is raised for that request.
    Records every request so tests can read the shape sent."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []

    def post(self, url, headers, body):
        self.requests.append({"url": url, "headers": headers, "body": copy.deepcopy(body)})
        if not self.script:
            raise AssertionError("stub received more requests than scripted")
        item = self.script.pop(0)
        if callable(item):
            item = item(body)
        if isinstance(item, Exception):
            raise item
        return 200, item


class CollectorCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="seo-collect-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.out = os.path.join(self.tmp, "out", "baseline")
        self.question_set = os.path.join(self.tmp, "question-set.json")
        self.settings_path = os.path.join(self.tmp, "collection-settings.json")
        self.write_questions(["t01"])
        settings = read_json(os.path.join(DATA, "collection-settings.json"))
        settings["claude"]["api"]["model"] = "claude-pinned-model-id"
        settings["claude"]["api"]["tool_version"] = "web_search_pinned_type"
        settings["gemini"]["api"]["model"] = "gemini-pinned-model-id"
        settings["chatgpt"]["api"]["model"] = "gpt-pinned-model-id"
        settings["chatgpt"]["api"]["tool_version"] = "web_search_pinned_openai_type"
        self.settings = settings
        write_json(self.settings_path, settings)
        self.previous_cwd = os.getcwd()
        self.cwd = os.path.join(self.tmp, "cwd")
        os.makedirs(self.cwd)
        os.chdir(self.cwd)
        self.addCleanup(os.chdir, self.previous_cwd)

    def write_questions(self, ids):
        write_json(self.question_set, [QUESTIONS[i] for i in ids])

    def env_for(self, assistant, with_key=True, **extra):
        env = dict(RUN_ENV)
        if with_key:
            env[KEY_VARIABLES[assistant]] = FAKE_KEY
        env.update(extra)
        return env

    def run_collector(self, assistant, transport, repeats=1, env=None, arm="baseline", out=None):
        log = io.StringIO()
        argv = ["--question-set", self.question_set, "--assistant", assistant, "--repeats", str(repeats), "--arm", arm,
                "--out", out or self.out, "--settings", self.settings_path]
        env = self.env_for(assistant) if env is None else env
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = collect.main(argv, env=env, transport=transport, log=lambda line: log.write(line + "\n"))
        return code, log.getvalue()

    def files_under(self, root):
        found = []
        for base, _, names in os.walk(root):
            for name in names:
                found.append(os.path.relpath(os.path.join(base, name), root))
        return sorted(found)

    def written(self):
        return self.files_under(self.out) if os.path.isdir(self.out) else []


class FailureExitTest(CollectorCase):
    """Criterion 3."""

    def test_no_key_exits_non_zero_names_the_variable_points_at_11_3_and_writes_nothing(self):
        for assistant, variable in (("claude", "ANTHROPIC_API_KEY"), ("gemini", "GEMINI_API_KEY"), ("chatgpt", "OPENAI_API_KEY")):
            stub = StubTransport([])
            code, log = self.run_collector(assistant, stub, env=self.env_for(assistant, with_key=False))
            self.assertEqual(code, 2, log)
            self.assertIn("missing-key", log)
            self.assertIn(variable, log)
            self.assertIn("section 11.3", log)
            self.assertIn("docs/measurement/4-measurement-framework.md", log)
            self.assertEqual(stub.requests, [], "no request may be made without a key")
            self.assertEqual(self.written(), [])
            self.assertEqual(self.files_under(self.tmp), ["collection-settings.json", "question-set.json"])

    def test_first_request_unreachable_exits_with_a_different_error_and_writes_nothing(self):
        stub = StubTransport([TransportError("unreachable", "cannot reach host: [Errno 111] Connection refused")])
        code, log = self.run_collector("claude", stub)
        self.assertEqual(code, 3, log)
        self.assertIn("unreachable", log)
        self.assertIn("api.anthropic.com", log)
        self.assertNotIn("missing-key", log)
        self.assertEqual(len(stub.requests), 1)
        self.assertEqual(self.written(), [])

    def test_failure_after_the_host_answered_writes_a_failed_record_continues_and_exits_non_zero(self):
        self.write_questions(["t01", "t02", "t03", "t04"])
        stub = StubTransport([
            claude_body(),
            TransportError("http", "HTTP 500 Internal Server Error: {}", status=500),
            TransportError("timeout", "request timed out after 120s"),
            TransportError("http", "HTTP 429 Too Many Requests: rate limited", status=429),
        ])
        code, log = self.run_collector("claude", stub)
        self.assertEqual(code, 1, log)
        self.assertEqual(self.written(), ["claude/api/t01-r01.json", "claude/api/t02-r01.json", "claude/api/t03-r01.json", "claude/api/t04-r01.json"])
        self.assertIn("round 1: collected=1 refused=0 failed=3", log)
        for question_id, detail in (("t02", "HTTP 500"), ("t03", "timed out"), ("t04", "HTTP 429")):
            record = read_json(os.path.join(self.out, "claude", "api", "%s-r01.json" % question_id))
            self.assertEqual(record["status"], "failed")
            self.assertIn(detail, record["failure_detail"])
            self.assertEqual(record["response_text"], "")
            self.assertEqual(record["retrieved_set"], [])
            records.check_fields(record, question_id)
        collected = read_json(os.path.join(self.out, "claude", "api", "t01-r01.json"))
        self.assertEqual(collected["status"], "collected")

    def test_an_unreachable_host_after_the_first_answer_is_a_failed_record_not_an_exit(self):
        self.write_questions(["t01", "t02"])
        stub = StubTransport([gemini_body(), TransportError("unreachable", "cannot reach host")])
        code, log = self.run_collector("gemini", stub)
        self.assertEqual(code, 1, log)
        self.assertEqual(read_json(os.path.join(self.out, "gemini", "api", "t02-r01.json"))["status"], "failed")

    def test_null_model_exits_naming_the_field_and_writes_nothing(self):
        self.settings["gemini"]["api"]["model"] = None
        write_json(self.settings_path, self.settings)
        stub = StubTransport([gemini_body()])
        code, log = self.run_collector("gemini", stub)
        self.assertEqual(code, 2, log)
        self.assertIn("unpinned-setting", log)
        self.assertIn("gemini/api/model is null", log)
        self.assertEqual(stub.requests, [])
        self.assertEqual(self.written(), [])

    def test_null_tool_type_string_exits_naming_the_field(self):
        self.settings["claude"]["api"]["tool_version"] = None
        write_json(self.settings_path, self.settings)
        code, log = self.run_collector("claude", StubTransport([claude_body()]))
        self.assertEqual(code, 2, log)
        self.assertIn("claude/api/tool_version is null", log)
        self.assertEqual(self.written(), [])

    def test_missing_run_id_exits_and_writes_nothing(self):
        env = self.env_for("claude")
        del env["GITHUB_RUN_ID"]
        code, log = self.run_collector("claude", StubTransport([claude_body()]), env=env)
        self.assertEqual(code, 2, log)
        self.assertIn("GITHUB_RUN_ID", log)
        self.assertEqual(self.written(), [])

    def test_key_rejected_on_the_first_request_exits_and_writes_nothing(self):
        stub = StubTransport([TransportError("http", "HTTP 401 Unauthorized: invalid x-api-key", status=401)])
        code, log = self.run_collector("claude", stub)
        self.assertEqual(code, 4, log)
        self.assertIn("key-rejected", log)
        self.assertIn("ANTHROPIC_API_KEY", log)
        self.assertEqual(self.written(), [])


class SuccessTest(CollectorCase):
    """Criterion 4."""

    def collect_one(self, assistant):
        stub = StubTransport([VENDOR_BODY[assistant]()])
        code, log = self.run_collector(assistant, stub)
        self.assertEqual(code, 0, log)
        path = os.path.join(self.out, assistant, "api", "t01-r01.json")
        self.assertEqual(self.written(), ["%s/api/t01-r01.json" % assistant])
        return stub, log, read_json(path)

    def assert_common_fields(self, record, assistant):
        records.check_fields(record, "t01-r01.json")
        self.assertEqual(list(record), list(records.RECORD_FIELD_NAMES))
        self.assertEqual(record["collector"], "workflow:987654321")
        self.assertEqual(record["arm"], "baseline")
        self.assertEqual(record["surface"], "api")
        self.assertEqual(record["assistant"], assistant)
        self.assertEqual(record["question_id"], "t01")
        self.assertEqual(record["question_text"], QUESTIONS["t01"]["text"])
        self.assertEqual(record["site"], QUESTIONS["t01"]["site"])
        self.assertEqual(record["repeat_index"], 1)
        row = self.settings[assistant]["api"]
        for name in records.SETTINGS_ROW_FIELDS:
            self.assertEqual(record["settings"][name], row[name], name)
        self.assertEqual(record["settings"]["region"], {"source": "actions-runner", "value": "unknown"})
        self.assertEqual(record["settings"]["runner_label"], "ubuntu-latest")
        self.assertEqual(record["status"], "collected")
        self.assertEqual(record["response_text"], ANSWER)
        self.assertEqual(record["screenshots"], [])
        self.assertIsNone(record["notes"])

    def test_claude_record_fields_and_request_shape(self):
        stub, log, record = self.collect_one("claude")
        self.assert_common_fields(record, "claude")
        self.assertEqual(record["model"], "claude-echoed-model-id")
        self.assertIs(record["searched"], True)
        self.assertEqual(record["searched_evidence"], 'content[].type == "server_tool_use" and name == "web_search"')
        self.assertEqual(record["retrieved_set"], [
            {"url": "https://www.hostinger.com/tutorials/cheap", "title": "Hostinger"},
            {"url": "https://launchyourfirstwebsite.com/hosting", "title": "Hosting"},
        ])
        self.assertEqual(record["cited_urls"], ["https://www.hostinger.com/tutorials/cheap"])
        self.assertEqual(record["raw_response"], claude_body())
        request = stub.requests[0]
        self.assertEqual(request["url"], "https://api.anthropic.com/v1/messages")
        self.assertEqual(request["headers"]["x-api-key"], FAKE_KEY)
        body = request["body"]
        self.assertEqual(body["model"], "claude-pinned-model-id")
        self.assertEqual(body["messages"], [{"role": "user", "content": QUESTIONS["t01"]["text"]}])
        self.assertEqual(body["tools"], [{"type": "web_search_pinned_type", "name": "web_search", "max_uses": 5}])
        self.assertNotIn("system", body)
        for forbidden in ("user_location", "allowed_domains", "blocked_domains"):
            self.assertNotIn(forbidden, body["tools"][0])
            self.assertNotIn(forbidden, body)

    def test_gemini_record_fields_and_request_shape(self):
        stub, log, record = self.collect_one("gemini")
        self.assert_common_fields(record, "gemini")
        self.assertEqual(record["model"], "gemini-echoed-model-id")
        self.assertIs(record["searched"], True)
        self.assertEqual(record["searched_evidence"], "candidates[0].groundingMetadata.webSearchQueries")
        self.assertEqual(record["retrieved_set"], [
            {"url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc", "title": "hostinger.com"},
            {"url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/def", "title": "launchyourfirstwebsite.com"},
        ])
        self.assertEqual(record["cited_urls"], [{"url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/def", "title": "launchyourfirstwebsite.com"}])
        self.assertEqual(record["raw_response"], gemini_body())
        request = stub.requests[0]
        self.assertEqual(request["url"], "https://generativelanguage.googleapis.com/v1beta/models/gemini-pinned-model-id:generateContent")
        self.assertEqual(request["headers"]["x-goog-api-key"], FAKE_KEY)
        self.assertEqual(request["body"]["tools"], [{"google_search": {}}])
        self.assertEqual(request["body"]["contents"], [{"role": "user", "parts": [{"text": QUESTIONS["t01"]["text"]}]}])
        self.assertNotIn("systemInstruction", request["body"])

    def test_gemini_request_carries_the_retrieval_tool_and_threshold_the_row_names(self):
        self.settings["gemini"]["api"]["web_tool"] = "google_search_retrieval"
        self.settings["gemini"]["api"]["dynamic_threshold"] = 0.3
        write_json(self.settings_path, self.settings)
        stub, log, record = self.collect_one("gemini")
        self.assertEqual(stub.requests[0]["body"]["tools"], [{"google_search_retrieval": {"dynamic_retrieval_config": {"mode": "MODE_DYNAMIC", "dynamic_threshold": 0.3}}}])
        self.assertEqual(record["settings"]["web_tool"], "google_search_retrieval")
        self.assertEqual(record["settings"]["dynamic_threshold"], 0.3)

    def test_openai_record_fields_are_unobservable_and_the_request_shape(self):
        stub, log, record = self.collect_one("chatgpt")
        self.assert_common_fields(record, "chatgpt")
        self.assertEqual(record["model"], "gpt-echoed-model-id")
        self.assertEqual(record["searched"], "unobservable")
        self.assertIsNone(record["searched_evidence"])
        self.assertEqual(record["retrieved_set"], "unobservable")
        self.assertEqual(record["cited_urls"], "unobservable")
        self.assertEqual(record["raw_response"], openai_body())
        request = stub.requests[0]
        self.assertEqual(request["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(request["headers"]["Authorization"].split(" "), ["Bearer", FAKE_KEY])
        self.assertEqual(request["body"], {"model": "gpt-pinned-model-id", "input": QUESTIONS["t01"]["text"], "tools": [{"type": "web_search_pinned_openai_type"}]})

    def test_a_second_run_with_the_same_inputs_refuses_to_overwrite(self):
        self.collect_one("claude")
        before = read_json(os.path.join(self.out, "claude", "api", "t01-r01.json"))
        stub = StubTransport([claude_body("A different answer that must not land.")])
        code, log = self.run_collector("claude", stub)
        self.assertEqual(code, 2, log)
        self.assertIn("would-overwrite", log)
        self.assertIn("I1", log)
        self.assertIn("t01-r01.json", log)
        self.assertEqual(stub.requests, [], "the refusal happens before any request")
        self.assertEqual(read_json(os.path.join(self.out, "claude", "api", "t01-r01.json")), before)

    def test_requests_run_in_rounds_repeat_1_of_every_question_then_repeat_2(self):
        self.write_questions(["t01", "t02"])
        stub = StubTransport([lambda body: gemini_body("Answer to: " + body["contents"][0]["parts"][0]["text"]) for _ in range(4)])
        code, log = self.run_collector("gemini", stub, repeats=2)
        self.assertEqual(code, 0, log)
        asked = [r["body"]["contents"][0]["parts"][0]["text"] for r in stub.requests]
        self.assertEqual(asked, [QUESTIONS["t01"]["text"], QUESTIONS["t02"]["text"], QUESTIONS["t01"]["text"], QUESTIONS["t02"]["text"]])
        self.assertEqual(self.written(), ["gemini/api/t01-r01.json", "gemini/api/t01-r02.json", "gemini/api/t02-r01.json", "gemini/api/t02-r02.json"])
        self.assertEqual(read_json(os.path.join(self.out, "gemini", "api", "t02-r02.json"))["repeat_index"], 2)
        self.assertIn("round 1: collected=2 refused=0 failed=0", log)
        self.assertIn("round 2: collected=2 refused=0 failed=0", log)

    def test_the_log_carries_counts_and_no_key_body_or_text(self):
        self.write_questions(["t01", "t02"])
        stub = StubTransport([claude_body(), TransportError("http", "HTTP 500: body mentioning " + FAKE_KEY, status=500)])
        code, log = self.run_collector("claude", stub)
        self.assertEqual(code, 1)
        self.assertNotIn(FAKE_KEY, log)
        self.assertNotIn(ANSWER, log)
        self.assertNotIn("hostinger", log)
        self.assertNotIn("claude-echoed-model-id", log)
        self.assertIn("collector: assistant=claude arm=baseline questions=2 repeats=1 requests=2", log)
        self.assertIn("done: records=2 collected=1 refused=0 failed=1", log)
        failed = read_json(os.path.join(self.out, "claude", "api", "t02-r01.json"))
        self.assertNotIn(FAKE_KEY, json.dumps(failed), "a key never lands in a record, even via an error body")
        self.assertIn("<redacted>", failed["failure_detail"])

    def test_nothing_is_written_outside_the_output_directory(self):
        self.write_questions(["t01", "t02"])
        before = self.files_under(self.tmp)
        stub = StubTransport([claude_body(), TransportError("timeout", "request timed out", )])
        code, log = self.run_collector("claude", stub, repeats=1)
        self.assertEqual(code, 1, log)
        after = self.files_under(self.tmp)
        new = sorted(set(after) - set(before))
        out_relative = os.path.relpath(self.out, self.tmp)
        self.assertTrue(new, "the run should have written records")
        for path in new:
            self.assertTrue(path.startswith(out_relative + os.sep), path)
        self.assertEqual(self.files_under(self.cwd), [], "the working directory stays untouched")

    def test_collector_output_is_accepted_by_the_scorer(self):
        self.write_questions(["t01", "c01"])
        scorer_data = os.path.join(self.tmp, "scorer-data")
        os.makedirs(scorer_data)
        shutil.copy(os.path.join(DATA, "question-set.json"), os.path.join(scorer_data, "question-set.json"))
        shutil.copy(os.path.join(DATA, "collection-settings.json"), os.path.join(scorer_data, "collection-settings.json"))
        shutil.copy(os.path.join(DATA, "arms.json"), os.path.join(scorer_data, "arms.json"))
        out = os.path.join(scorer_data, "responses", "baseline")
        for assistant in ("claude", "gemini", "chatgpt"):
            stub = StubTransport([VENDOR_BODY[assistant]() for _ in range(2)])
            code, log = self.run_collector(assistant, stub, out=out)
            self.assertEqual(code, 0, log)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = score.main(["--data", scorer_data])
        self.assertEqual(code, 0, buffer.getvalue())
        text = buffer.getvalue()
        self.assertIn("launchyourfirstwebsite.com | claude | api | baseline", text)
        self.assertIn("retrieved rate                   1/1 (100.0%)", text)
        self.assertIn("launchyourfirstwebsite.com | chatgpt | api | baseline", text)


class UsageTextTest(unittest.TestCase):
    def test_collector_usage_names_every_argument_and_variable(self):
        usage = collect.__doc__
        for name in ("--question-set", "--assistant", "--repeats", "--arm", "--out", "--settings"):
            self.assertIn(name, usage)
        for variable in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "GITHUB_RUN_ID"):
            self.assertIn(variable, usage)
        self.assertIn("11.3", usage)

    def test_scorer_usage_names_its_arguments(self):
        for name in ("--data", "--json"):
            self.assertIn(name, score.__doc__)


if __name__ == "__main__":
    unittest.main()
