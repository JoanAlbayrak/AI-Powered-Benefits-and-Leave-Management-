# Team start here

## What this handoff contains

This is a **documentation and planning scaffold for joint review**. It adds the proposed agent responsibilities, work packages, integration contracts and a shareable report. It does not connect new UI actions or change application behavior. We should review the proposed boundaries together before implementing the next phase.

| Read in this order | Purpose |
|---|---|
| [Visual report](reports/Benefits-and-Leave-Case-Team-Report.pdf) / [editable report](BENEFITS-LEAVE-PROPOSAL.md) | Learn the HR domain, real employer processes, agents and proposal. |
| This document | Understand what exists and how to inspect it locally. |
| [Execution board](EXECUTION-BOARD.md) | Pick bounded tasks, dependencies and completion checks. |
| [Workflow contracts](WORKFLOW-CONTRACTS.md) | See current endpoints and proposed additions before coding. |
| [Frontend scaffold](FRONTEND-SCAFFOLD.md) | Find UI modules and existing design boundaries. |

The requirement known to us is a multi-agent system. No additional grading rubric has been supplied. The presentation will be a live local demo. A working key will be supplied locally later; we must not claim live-model validation before testing it.

## Current implementation versus proposal

| Area | Implemented now | Planned next |
|---|---|---|
| Employee/HR interface at `/` | Read-only views, navigation, fictional records, filters and status displays | Connect explicit employee and HR actions |
| Original interface at `/legacy` | Existing enrollment, leave and vendor workflows | Retain as a reference while integrating the new UI |
| Three agents | Scoped tools and structured summaries/drafts | Evidence clarification and a useful specialist consultation |
| Coordination | Code-owned cases and frozen enrollment-to-vendor handoff | Code-routed Vendor-to-Enrollment consultation |
| Decisions and external actions | HR decision guards; HR manually records sending | Preserve these boundaries in the new interface |
| Storage and identities | In-memory cases; demo role/profile selection | Keep explicit demo limitations; no production claim |
| Public GitHub Pages demo | Static browser demo with example agent messages | No live key or live-model calls in the public page |

Agents currently do not call each other. The proposed consultation is an addition, not a feature already delivered. Evidence verification, durable agent sessions, policy versioning and transaction versioning also need implementation.

## Inspect this branch

For an existing clone, first check for local work and preserve it on your own branch before switching. Do not reset or overwrite someone else's changes.

```sh
git status
git fetch origin
git switch --track origin/docs/team-planning-scaffold
```

If this branch is already available locally, use `git switch docs/team-planning-scaffold` instead. You can also open the PR's Files changed view without running anything.

For a fresh clone:

```sh
git clone --branch docs/team-planning-scaffold https://github.com/JoanAlbayrak/AI-Powered-Benefits-and-Leave-Management-.git
cd AI-Powered-Benefits-and-Leave-Management-
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m benefits_leave.web
```

Open http://127.0.0.1:8001 to browse the scaffold; open http://127.0.0.1:8001/legacy to inspect the existing action workflow. If that port is already occupied, run `.venv/bin/python -m benefits_leave.web 8002` and open port 8002 instead. Restarting the application resets cases.

### API key setup later

Browsing the new scaffold and running tests do not need an API key. The existing runtime uses Anthropic. Copy `.env.example` to `.env` **only if `.env` does not already exist**, then replace the placeholder locally:

```sh
cp -n .env.example .env
```

Edit `ANTHROPIC_API_KEY` in the private `.env` file. Never put a key in chat, GitHub, screenshots, browser JavaScript or the public demo. Never overwrite a teammate's configured file. A key from another provider is not interchangeable with an Anthropic key; provider support would be separate work.

**Pending runtime check:** validate the configured model name and SDK request parameters with the actual account before the first live demo. The existing `runner.py` has provider-specific model and beta settings. This handoff makes no promise that past settings will work with a newly supplied key. The next phase should provide a supported, configurable model and a non-secret readiness check.

## Verify the existing baseline

```sh
.venv/bin/python -m unittest
node --test tests/frontend.test.mjs
```

Node is only needed for the frontend checks; there is no frontend build or package install. Tests use a fake model and do not validate live model quality, credentials or availability.

Handoff verification on 31 October 2026: **51 Python tests and 7 frontend tests passed**. Local document links were checked, and the shared PDF matches the reviewed report. No live API call was made. The checks were run with available local Python and Node runtimes; each teammate should create their own virtual environment using the setup above.

## Where to work

| Responsibility | Main locations |
|---|---|
| Deterministic checks | `benefits_leave/checks.py` |
| Scoped agent prompts and tools | `benefits_leave/agents.py` |
| Bounded model execution and local configuration | `benefits_leave/runner.py` |
| Case transitions, approvals and handoffs | `benefits_leave/workflow.py` |
| API boundary and employee-safe projections | `benefits_leave/web.py` |
| Frontend requests and action wiring | `benefits_leave/frontend/js/api.js`, `app.js` |
| Employee/HR page content | `benefits_leave/frontend/js/views/` |
| Shared UI | `benefits_leave/frontend/js/components.js`, `styles/` |
| Fictional fixtures and checks | `data/`, `tests/` |

## Working together

1. Review the proposal and agree on the first task before starting implementation.
2. Claim a work package in the execution board. Owners are deliberately unassigned, not presumed.
3. Branch from the agreed shared base for each new task. Never commit or push directly to `main`.
4. Keep commits at coherent working milestones. Open a PR with behavior, validation and known limits.
5. Review each other's contracts before changing shared files such as `workflow.py`, `web.py` or `app.js`.
6. Merge only after review and explicit agreement. Do not assume this planning PR is already merged.

### Partner review checklist

- Can you browse both interfaces locally and understand the difference?
- Do the agent roles match the project we want to present?
- Is Vendor-to-Enrollment the first specialist consultation we want to demonstrate?
- Are the first task's API and case-state boundaries clear?
- Which work package will each person own, and which files might overlap?

## Remote check for this handoff

On 31 October 2026, `origin/main` was at `51e88c0`. GitHub reported no open PRs. The existing remote partner branch was fully contained in `origin/main`; it had no additional commits to integrate. This cannot detect unpublished local work or changes made after that check.

## Rebuild the report if needed

The report is documentation, not part of the app runtime. With `reportlab` available in your chosen Python environment, run `python3 scripts/build_agentic_report.py`. It writes a PDF under the ignored `outputs/` directory. After reviewing a revised PDF, copy it to `docs/reports/Benefits-and-Leave-Case-Team-Report.pdf` to update the version shared in the repository. Do not add PDF tooling to the application's runtime solely to browse the scaffold.
