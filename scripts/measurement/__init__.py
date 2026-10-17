"""Measurement tooling for docs/measurement/4-measurement-framework.md.

`records` holds the field list and the per-record checks both protocols share,
`scoring` turns a directory of records into the framework's report, and
`collector` is what the workflow_dispatch workflow runs against an assistant's
API. The entry points are scripts/score.py and scripts/collect.py.
"""
