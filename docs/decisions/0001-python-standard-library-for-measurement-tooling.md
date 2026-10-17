# ADR 0001: Python 3 with the standard library only for the measurement tooling

Date: 2026-10-17
Status: accepted

## Context

Issue #5 is the first product code in this repository: a scorer that turns
stored response records into the framework's metrics, a collector that a
`workflow_dispatch` workflow runs against an assistant's API, and the tests
that prove both. Until now the repository held only documents, and
`CLAUDE.md` said the stack was not chosen.

Three constraints forced the choice rather than a preference:

- The collector runs on a plain `ubuntu-latest` GitHub Actions runner (O6 on
  #2: every network-bound step runs in Actions, never in a session) and has to
  be callable from a workflow with no install step, so a missing dependency
  cannot be the reason a baseline window is missed.
- The gate has to run the tests with no package manager and no lockfile, on
  the runner's system interpreter, so the swap of the placeholder gate is one
  command and not a toolchain.
- The data shape is fixed by section 11 of
  `docs/measurement/4-measurement-framework.md` - flat JSON files, one per
  response and one per indexing report - and nothing in it needs more than
  JSON, regular expressions, dates and HTTP POST.

The orchestrator's plan on #1 steered this to Python with the standard
library only, and the owner had the chance to overturn that there.

## Decision

The measurement tooling is Python 3 (3.12 or later; the runner's system
`python3`) using only the standard library. The code lives under
`scripts/measurement/` with two entry points, `scripts/score.py` and
`scripts/collect.py`; the tests live under `tests/` and run with
`python3 -m unittest discover -s tests -v` from the repository root. HTTP is
`urllib`, JSON is `json`, and the data shape is the one section 11 of the
framework defines - this record does not restate it.

## Consequences

- Install is nothing. The gate and the workflow both run a single `python3`
  command; a fresh runner or a fresh clone needs no step before it.
- No test can make a live call by accident through a client library's
  defaults: the only network code is one `urllib` call behind a transport
  class the tests replace with a stub.
- Vendor request and response shapes are written out by hand in
  `scripts/measurement/collector.py` rather than taken from a vendor SDK, so
  a field the vendor renames shows up as a stored record that re-scores
  differently, not as an SDK upgrade. The raw body is stored verbatim for
  that reason (11.1).
- Adding a third-party package later is a category change under the house
  rules and needs its own ADR saying why the standard library stopped being
  enough.

## Alternatives rejected

- **Node with the project's four standard scripts** (`typecheck`, `lint`,
  `test`, `build`): needs a lockfile and an install step on every run, and
  there is nothing to build; it lost on the no-install constraint.
- **Python with vendor SDKs** (`anthropic`, `google-genai`, `openai`): each
  is a dependency with its own retry, timeout and logging behaviour that the
  framework's I15 and log rules would have to be proved against; it lost
  because the request shapes are three small JSON bodies and the SDKs would
  hide what is sent.
- **Shell with `curl` and `jq`:** workable for the collector, but the scorer's
  rules (normalised substring matching, the four-case decision rule, twelve
  invariants) need a real test suite, and `jq` has none; it lost on
  testability.
