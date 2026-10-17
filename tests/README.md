# Tests

Run with `python3 -m unittest discover -s tests -v` from the repository root.
Nothing to install; standard library only. No test makes a network call - the
collector is tested against the stub transport in `test_collector.py`.

- `test_data_files.py` - the four frozen data files and the manual template
  against the framework document (criterion 5 of #5)
- `test_scorer.py` - the scorer's output: table 3.10 from the worked examples,
  the decision rule, the flip condition, the guardrails (criterion 1)
- `test_scorer_invariants.py` - each scorer-enforced invariant of section 9
  refuses by file and id (criterion 2)
- `test_collector.py` - the collector's failure exits and success path
  (criteria 3 and 4)
- `support.py` - fixture builders; records are built with every field of 11.1
