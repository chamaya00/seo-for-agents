#!/usr/bin/env python3
"""Collect one assistant's API responses for one arm - section 11.4's contract.

usage: python3 scripts/collect.py --question-set data/question-set.json
                                  --assistant {claude,gemini,chatgpt}
                                  --repeats N --arm {baseline,post-change}
                                  --out data/responses/<arm>
                                  [--settings data/collection-settings.json]
                                  [--timeout SECONDS]

  --question-set  the frozen set (11.7); every question is asked, in file order
  --assistant     which assistant's API to call
  --repeats       repeats per question (5; 10 after 7.4's test fails)
  --arm           written into every record and checked by the scorer (I8)
  --out           the only directory this writes under (I12): one file per
                  response at <out>/<assistant>/api/<question_id>-r<NN>.json
  --settings      the pinned settings (11.8); default data/collection-settings.json
  --timeout       per-request timeout in seconds; default 120

Environment: the key is read from exactly one variable, by assistant -
  claude   ANTHROPIC_API_KEY
  gemini   GEMINI_API_KEY
  chatgpt  OPENAI_API_KEY
and nothing else. GITHUB_RUN_ID is required and recorded as
collector: "workflow:<GITHUB_RUN_ID>". RUNNER_LABEL (else RUNNER_OS) is
recorded as settings.runner_label; RUNNER_REGION, if the workflow sets it, as
settings.region.value, else "unknown". Set the variable from the repository
Actions secret of the same name in the workflow_dispatch workflow; no key is
printed, logged or written into a record.

Runs in rounds - repeat 1 of every question, then repeat 2 - each request a
fresh single-turn conversation carrying the question text verbatim. The log
holds counts only.

Exit status:
  0  every request came back; records written
  1  ran to the end but at least one record is `failed` (HTTP error, timeout,
     rate limit after the host had answered once) - the file says why
  2  stopped before any request, nothing written: a missing key variable
     (collect that assistant by the manual protocol, framework 11.3), a null
     model or tool type string in the settings row, GITHUB_RUN_ID unset, or an
     output file that already exists (I1)
  3  the first request could not reach the host - nothing written
  4  the host rejected the key on the first request (HTTP 401/403) - nothing
     written
Standard library only.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from measurement.collector import Collector, CollectorError, UrllibTransport  # noqa: E402
from measurement.records import ARMS, ASSISTANTS  # noqa: E402


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--question-set", required=True, help="path to data/question-set.json")
    parser.add_argument("--assistant", required=True, choices=ASSISTANTS, help="which assistant's API to call")
    parser.add_argument("--repeats", required=True, type=int, help="repeats per question")
    parser.add_argument("--arm", required=True, choices=ARMS, help="baseline or post-change")
    parser.add_argument("--out", required=True, help="output directory, normally data/responses/<arm>")
    parser.add_argument("--settings", default="data/collection-settings.json", help="path to data/collection-settings.json")
    parser.add_argument("--timeout", type=float, default=120.0, help="per-request timeout in seconds")
    return parser


def main(argv=None, env=None, transport=None, log=print):
    args = build_parser().parse_args(argv)
    env = os.environ if env is None else env
    if args.repeats < 1:
        log("collect: --repeats must be 1 or more")
        return 2
    try:
        collector = Collector(
            args.question_set, args.settings, args.assistant, args.repeats, args.arm, args.out,
            env=env, transport=transport or UrllibTransport(args.timeout), log=log,
        )
        return collector.run()
    except (OSError, ValueError) as error:
        log("collect: cannot read inputs: %s" % error)
        return 2
    except CollectorError as error:
        log("collect: %s" % error)
        return error.exit_code


if __name__ == "__main__":
    sys.exit(main())
