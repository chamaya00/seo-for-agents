# Project context

<!-- One bracketed line is left below, under "What this is", and provisioning
     fills it in. The two sections after it are read out of this repository
     rather than asked about, and when it does not answer them yet they stay
     exactly as they stand: "not chosen yet" is a real answer here, not a gap
     somebody forgot. Everything from the marker onward is the standing
     arrangement.

     A bracketed line that survives into a provisioned repository fails
     project-guard, on purpose - see the check named after this file there. -->

## What this is

My explorations and experiments in optimizing websites so AI agents and assistants surface them in their answers, for anyone who wants their site found by agents rather than only by search engines.

## Stack

Python 3, standard library only, on the system `python3` of a plain
`ubuntu-latest` runner - ADR `docs/decisions/0001-python-standard-library-for-measurement-tooling.md`.
The code is the measurement tooling under `scripts/measurement/` with two
entry points, `scripts/score.py` and `scripts/collect.py`; the tests are under
`tests/`. The data shape is section 11 of
`docs/measurement/4-measurement-framework.md`, and the data itself lives under
`data/`. There is no package manager, no lockfile and no build.

Nothing publishes this repository. The gate runs the tests and the scorer; the
collector runs in a `workflow_dispatch` workflow on a runner, never in a
session (O6 on #2). If something starts publishing it, the question at the top
of `.github/workflows/ci.yml` - does the gate run what publishes it - becomes
answerable and is answered in the pull request that makes the swap.

## Commands

- Install: none. `python3` 3.12 or later is the only requirement, and the
  runner has it.
- Dev:
  - `python3 scripts/score.py [--data data] [--json]` - score every record
    under `data/responses/` and every report under `data/indexing/`; exits 1
    naming the file and the invariant when a record is refused.
  - `python3 scripts/collect.py --question-set data/question-set.json --assistant <claude|gemini|chatgpt> --repeats 5 --arm <baseline|post-change> --out data/responses/<arm>`
    - the API collector; runs only inside the `workflow_dispatch` workflow,
    with the assistant's key in `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` or
    `OPENAI_API_KEY` and `GITHUB_RUN_ID` set. `--help` on either prints the
    full contract.
- Checks CI runs: `python3 -m unittest discover -s tests -v`, from the
  repository root. One check is the complete answer: it covers the scorer,
  the collector against a stubbed HTTP layer, the four frozen data files and
  the recording template. No test makes a network call.

The check above is what CI runs once the gate is real. Until the swap lands,
`.github/workflows/ci.yml` ships a placeholder that checks the scaffolding is
intact and fails the moment product code lands, because a project gets its
gate before it gets its stack and a gate that goes green on untested code is
worse than no gate. The comment at the top of that file says how to swap it;
on this project the `commands` path is the destination, with the one command
above in it.

Whatever the gate runs, the rule is the same. If a check is renamed here,
rename it in `.github/workflows/ci.yml` in the same commit, or the gate
silently stops checking that thing.

Branch protection is not part of that change and should not be touched by it.
The `ci` job is named `checks` on every path, so what protection requires stays
the same however often the commands under it change. Renaming that job is the
one edit here that breaks the rule: a required check that stops reporting
blocks every merge rather than gating them, including the pull request that
would name it back.

## How work moves

Objectives become issues labelled `objective`. A human labels the objective
`agent:queued`; nothing else needs labelling by hand. The orchestrator splits it
into 1-5 child issues sized to the work, each with acceptance criteria and one
role label, and then queues them itself as each one becomes ready. A small
objective may be a single engineer issue - when it is, the orchestrator says
which roles it skipped, so a thin plan is visible rather than assumed.

**Who starts a run is a setting.** `.claude/agent-factory.json` names the
runner. Under `session` - the default for a new repository - nothing starts a
run but a session: the one driving the work, or one a self-driving stretch
schedules, runs the role through `/dispatch` with the same checks, budgets,
labels, and brief the workflow used, and the agent-run workflow reads the line
and stands down. Under `actions`, a label starts that workflow, which spends the
`CLAUDE_CODE_OAUTH_TOKEN` secret. Everything below reads the same either way:
`agent:queued` is a request under both, and a wake means whichever runner is in
charge starts the next run.

It stays with the objective after the split. A child reaching `agent:review` or
`agent:blocked` wakes it: it reads the state of every child, queues whatever the
merge has just unblocked, rewrites and re-queues a child that blocked on its own
scoping, and replaces the status picture on the parent issue. The parent issue
is the whole surface - a human reads that and nothing else, and hears from the
orchestrator when a decision is genuinely theirs.

Ready means the issues a child depends on are merged to the default branch, not
merely finished and labelled `agent:review`. An agent reads the default branch,
so work that is finished but unmerged is invisible to the child that depends on
it. Which roles open a pull request for their own work is not restated here -
each role file says what that role does, and a summary of it in this file could
only drift. A run started too early refuses, correctly, and still spends one of
that issue's three attempts. That check is now the orchestrator's to make before
it queues anything.

The human still decides what merges. The orchestrator queues work and reports on
it; it does not merge a pull request, and it cannot break a child down further -
that comes back as `needs-decomposition` and a comment on the parent.

A role that hits a decision it cannot make asks it on its own issue and keeps
working under the answer it recommends. That question comes back labelled
`agent:needs-input`, which rides alongside `agent:review` rather than replacing
it: the work shipped and is reviewable, and what is waiting is an answer, not a
run. The orchestrator carries it onto the parent issue verbatim, so the parent
stays the only page a human has to read. It blocks the merge and nothing else,
and no merge policy covers it - that one is always the person's.

**Work that is refused comes back rather than stopping.** A driver that reads a
pull request and will not take it writes the review, drops `agent:review`, and
adds `agent:revise`. That starts a run on the branch and pull request that
already exist, holding the review as its brief. It spends a budget of two
revision rounds rather than one of the three attempts, which is what makes
rejecting a nearly-right diff affordable instead of a way to strand an issue at
`needs-decomposition`. A third round is refused and comes to a person, and it
is a finding about the review rather than about the role. The `house-rules`
skill carries both halves.

Labels: `objective`, `agent:queued`, `agent:running`, `agent:review`,
`agent:blocked`, `agent:needs-input`, `agent:revise`, `needs-decomposition`,
`needs-human`, `role:researcher`, `role:analyst`, `role:designer`,
`role:engineer`.

A label the preflight matches on and the repository does not have is a
mechanism that fails silently. Re-run `bootstrap` from the Actions tab after
picking up a release that adds one; it is idempotent.

## Driving an objective

A session that files an objective, or is pointed at one, is that objective's
driver: the person's window into it, and the technical judgment between an
agent's work and what ships. Nobody else is watching, and nothing downstream
catches what the driver waves through. Filing one is `/objective`, which
refines the idea, sets the merge policy, queues it, and hands back to the
session to drive.

The driver is expected to reject work that clears the merge gate and is still
not good enough - and to send it back with `agent:revise` rather than merely
saying so - to press a specification for definition before the child that
depends on it is queued, and to tell the orchestrator that a split or a brief
was wrong. What it does not get to decide is what the product should be. That
line - subject matter, not seniority - is the first thing the skill draws.

**Shorthand:** a message starting with `obj` - any case, with or without a
trailing `.` or `:` - means the same thing as typing `/objective`. Read
`.claude/commands/objective.md` and follow it, treating the rest of the
message as the rough idea. Nothing else is shorthand for anything; a plain
description of work with no `obj` prefix is a question or a discussion, not an
instruction to file something.

**Waking back up is `/check-in`.** Whether that is a person resuming a
session, a scheduled wake, or a subscribed pull request's activity firing one,
it runs the same catch-up: what is waiting on the person first, then the state
of every child, then the two reading passes over each waiting diff, merging
under the policy where it applies.

**Starting a run is `/dispatch`.** Where the runner is `session`, a queued role
starts when a session starts it, and `/check-in` does that one run at a time -
in this session as a subagent by default, or in a child session when the driver
judges the run is worth one. Between the sessions the person opens, nothing
runs unless a self-driving stretch is keeping scheduled sessions going.

**Long autonomous runs are `/self-driving`**, whether the person types it or
asks in their own words for the work to keep moving while they are away. When the person wants one or more
objectives taken to done without them in the loop - overnight, or a day spent
elsewhere - that command starts the stretch: one round of questions first, a
decision log for every call made on their behalf, wakes on a clock as well as on
events, and a close-out when it ends. It never begins on its own.

**Read `.claude/skills/driving-an-objective/` whenever an objective is in play**
- what to do with its merge policy, how to report, how to put a blocker so it
can be answered, and what only the person can decide. This paragraph exists to
say the role is yours; the skill says how to hold it.

## The rules

Not restated here. Two sections used to summarise them and every line had a
fuller source a click away, so the summaries could only ever drift out of
agreement with the thing they summarised - which is worse than not having them,
because a reader who finds a rule here stops looking for the real one.

- `.claude/skills/house-rules/` - what must be true before work starts and
  before anything merges, who may merge, the three-strike rule, and what no
  agent may touch.
- `.claude/skills/memory-protocol/` - how this repository's lessons are stored,
  capped, proposed, and retired.
- `.claude/skills/acceptance-criteria/` - what a criterion has to look like to
  gate anything.
- `.claude/skills/driving-an-objective/` - what the session in front of a person
  does once an objective is running, what it owns, and what it may refuse.
- `.claude/skills/briefing/` - what the orchestrator's report on a parent issue
  has to carry intact, what it compresses, and what a driver may send back.

Every agent run is told to follow the first three by name. The last two are the
two ends of one channel: the orchestrator writes to `briefing`, the driving
session reads by it, and the section above names them rather than leaving them
to be discovered.

<!-- agent-factory:end -->
