#!/usr/bin/env python3
"""Score the stored responses against docs/measurement/4-measurement-framework.md.

usage: python3 scripts/score.py [--data DIR] [--json]

  --data DIR   the data directory in the layout of section 11.2 (default: data).
               It must hold question-set.json, collection-settings.json and
               arms.json; fingerprints.json is optional and its absence makes
               the paraphrased rung unobservable. Records are read from
               DIR/responses/<arm>/<assistant>/<surface>/*.json and indexing
               reports from DIR/indexing/<domain>/<engine>/<date>.json.
  --json       print the report as JSON instead of text.

Prints, per cell (site, assistant, surface, arm): every rung's rate as
numerator over section 4's denominator with n_collected, n_refused, n_failed
and distinct_questions; the indexed state per domain per engine per arm; the
per-question search fraction and 7.4's variability test on API cells; F_a per
assistant and the flip flag of 7.7; the guardrails of section 10; the
four-case decision rule of 7.6 per rung; and the per-assistant verdict.

Exit status: 0 when every record and report passes the invariants of section
9; 1 when any is refused (each refusal names the file and the invariant, and
the report is still printed for the records that passed); 2 when the data
directory or one of the frozen files cannot be read. Standard library only.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from measurement.scoring import Scorer, render  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="data", help="data directory in the layout of section 11.2 (default: data)")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)
    try:
        scorer = Scorer(args.data)
    except (OSError, ValueError) as error:
        print("score: cannot read the frozen files under %s: %s" % (args.data, error), file=sys.stderr)
        return 2
    report = scorer.run()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        sys.stdout.write(render(report))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
