# Joan handoff: interactive enrollment and leave work

Prepared 2 November 2026. Branch: `feat/interactive-enrollment`.

**Work-in-progress handoff, not ready to merge.** This branch preserves the latest Claude changes so another teammate can finish them. Do not treat passing tests as proof that every new path is correct.

## Download and run

From an existing clone, preserve any local changes before switching:

```sh
git fetch origin
git switch --track origin/feat/interactive-enrollment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp -n .env.example .env
```

If the branch already exists locally, use `git switch feat/interactive-enrollment`. For a separate clean clone:

```sh
git clone --branch feat/interactive-enrollment https://github.com/JoanAlbayrak/AI-Powered-Benefits-and-Leave-Management-.git
```

Paste your own Anthropic key into the ignored local `.env`; never share or commit it. Then:

```sh
.venv/bin/python -m benefits_leave.readiness
.venv/bin/python -m benefits_leave.web
```

Open http://127.0.0.1:8001. If occupied, append `8002` to the server command and open that port. The optional `.claude/launch.json` now uses the relative virtual-environment interpreter rather than another teammate's absolute path. Create the environment in this checkout first.

The configuration-only readiness check makes no model call. `--live` explicitly sends a small check to Anthropic and can consume credits. A personal API key is not included. Cases and edits are in memory and reset when the server restarts. Use fictional data only.

## What is already in the shared baseline

PR #13 merged the T02-T10 implementation on 2 November: AI readiness, scoped policy/evidence, enrollment Q&A, Vendor-to-Enrollment consultation, leave drafts/confirmation, activity and demo instructions. The older integration is also merged via PR #4. Several older stacked PRs still show open even though their commits are contained in the final stack; verify containment before closing those PRs, rather than merging them again blindly.

The original work-plan/task-log PR #5 is separate and still pending at this handoff. This document is the current interactive-extension accomplishment and remaining-task record.

## Accomplishment checklist for this branch

These checkmarks mean code has been written and preserved, not that the feature is ready for release.

- [x] Employee election editing, permitted plan/tier validation, waivers and retirement percentages.
- [x] Explain an unsaved choice using the Enrollment Agent, without saving for the employee.
- [x] Add dependents and record simulated proof upload as received, not verified.
- [x] Employee/employer premium summaries and synthetic plan descriptions.
- [x] Categorized PTO, sick and personal balances with unknown-data handling.
- [x] Free-text leave intake suggesting a type before creating a draft.
- [x] Leave-only approval pending documents, with a required HR reason.
- [x] Provider document-request results and follow-up draft support.
- [x] Renamed synthetic people and preserved the existing rehearsal records.
- [x] Added backend regression tests for the new paths and rebuilt the static demo.

## Verification actually performed

During the 2 November inspection, **131 Python tests and 24 frontend tests passed**, plus a separate public-page consistency check. The generated-page test was performed against a temporary output file to preserve the working page. The unchanged baseline separately passed 104 Python tests and 24 frontend tests plus that same consistency check.

No new paid model calls or end-to-end browser rehearsal of the latest extension were performed during this inspection. The live runs recorded in `DEMO-SCRIPT.md` are prior-session results for the earlier journey; they do not establish correctness of every new interactive feature. Existing frontend tests still number 24 and do not fully cover the new forms.

## Finish in this order

### 1. Fix stale enrollment approval — blocking, reproduced

- [ ] After an election/dependent/evidence edit, invalidate or refresh the open HR review packet and its guidance.
- [ ] Recompute completeness and required HR flags immediately before approval; freeze exactly the version HR reviewed. If it changed, require a fresh review.
- [ ] Add a regression: check E2002 as complete, change medical to Gold HMO/family without dependents, then attempt approval. It must fail.

Observed in the current code: the saved case has zero missing items while the live data has two, but HR approval succeeds and freezes family coverage. `set_election` changes the record; `hr_decide` uses the old `case['enrollment']`. Do not demonstrate this path as guarded until fixed.

### 2. Restore employee/HR projection separation — reproduced

- [ ] Remove `hr_flags` from `/api/employee/enrollment/elect` responses.
- [ ] Add an endpoint test for E2003 and check every new employee-facing response for internal fields.

Observed: the employee election endpoint returns the internal flags array. Keep it in the HR projection only.

### 3. Finish document lifecycle

- [ ] Add an explicit HR verification action, or clearly restrict the demo route to already-verified fixtures.
- [ ] Keep received distinct from verified; do not let an employee mark their own evidence verified.
- [ ] Provide a supported transition to finish an `approved_pending_documents` leave case, or label it as an unfinished terminal demo state.
- [ ] Complete leave correction/resubmission after an HR information request, or state this limitation in the final script.

At present a new dependent's received proof remains missing and there is no HR verification UI to complete it.

### 4. Check grounding and runtime limits

- [ ] Supply the actual approved policy content to the new consideration/intake tools before relying on policy-based explanations; filtering reference IDs alone does not ground the answer.
- [ ] Review the hardcoded retirement vesting explanation and sick-versus-PTO suggestions against explicitly labeled demo policy.
- [ ] Add a shared elapsed-time budget for the Vendor/specialist run, or document the actual per-request/turn limits. Current SDK retries and multiple model calls can exceed the browser's 120-second action timeout.

### 5. Rehearse and finish delivery

- [ ] Exercise election save, unsaved consideration, dependent upload, leave intake, balances and conditional approval in the browser.
- [ ] Rehearse the latest version with a working key after the blockers are fixed. Clearly distinguish live output from fallbacks.
- [ ] Update the canonical task log and reconcile stale documentation that says nothing was pushed, merged or tested live.
- [ ] Review the feature PR before merging. Do not push directly to main.

## File map

- `workflow.py`: election/dependent mutations, cost summaries, leave intake and new decision state.
- `web.py`: employee projections and five added action routes.
- `agents.py`: unsaved-choice explanation, free-text leave intake and vendor document-request wording.
- `frontend/js/`: new forms, API calls and rendering.
- `hr_lookup.py` / fictional JSON: categorized balances, plan metadata and people.
- `tests/`: new backend coverage; new frontend-path coverage still needed.

The other checkout `Multi-Agent-HR` was left untouched. Its renamed fixtures and rehearsal/documentation edits are represented in this newer branch; continue development in a single agreed checkout to avoid diverging copies. No credentials, virtual environment or local runtime logs are part of the handoff.
