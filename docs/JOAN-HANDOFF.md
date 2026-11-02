# Joan handoff: interactive enrollment and leave work

Prepared 2 November 2026. Handoff branch: `feat/interactive-enrollment`; continuation branch: `claude/jolly-edison-vkgp9d` (started from it).

**Status (updated 2 November 2026, after the continuation work on `claude/jolly-edison-vkgp9d`):** the five tasks under "Continuation: what was done" are implemented and verified **offline and in a real browser against a scripted model**. **They have not been verified with a live model**: no paid call was made in this continuation. Passing tests are not proof that every path is correct; read "Verification" and "Remaining limitations" before presenting.

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

## Continuation: what was done (in order)

Each task was committed separately on `claude/jolly-edison-vkgp9d`, started from `feat/interactive-enrollment`.

- [x] **1. Stale enrollment approval (blocking, fixed and regression-tested).** Edits to elections, dependents or documents now refresh an open case's deterministic review and drop its old AI summary (`CaseStore._refresh_enrollment_review`). Every refresh bumps `review_revision`. `hr_decide` revalidates against the live data, rejects a case that changed after HR opened it (the page sends the revision it showed), and the frozen handoff is built from exactly the data that was reviewed. A conflict is a distinct `StaleReviewError`; the page reloads the latest case by itself and shows the message. Regression: E2002 checked as complete, medical changed to Gold HMO/family, approval now fails (`tests/test_stale_review.py`).
- [x] **2. Employee/HR projection separation (fixed and tested).** One shared employee enrollment projection (`employee_enrollment_view`) now backs the overview, check and election endpoints. `/api/employee/enrollment/elect` no longer returns `hr_flags`, and `/api/employee/enrollment` no longer returns `enrollment_state` (it revealed `needs_hr_exception`). The Enrollment Agent is told flags are internal, and a verbatim-copy guard replaces an employee message that quotes a flag. `tests/test_privacy.py` walks every employee endpoint for E2003 (HR flag) and E1003 (failed FMLA basics).
- [x] **3. Document and clarification transitions (implemented, role/state rules in the backend).**
  - HR verifies received dependent proof (`hr_verify_document`, `/api/hr/evidence/verify`). The employee upload path can never set verified; only the case employee's own received record can be verified, only on an open case, and a stale HR view is refused.
  - `approved_pending_documents` now has a lifecycle: each requested document is `requested` → `received` (employee marks it, label only) → `verified` (HR). Status moves to `approved_documents_received`; HR then verifies and completes the approval, asks again (reason required), or withdraws the approval (reason required).
  - After an information request the employee corrects the **same** case: leave via `resubmit_leave` (dates, type and schedule must be valid); enrollment by rechecking, which is the resubmission. Edits alone no longer silently re-queue an `info_requested` case for HR.
  - Employees can only act on their own cases (same "not found" answer for someone else's). The demo has no real login: role is the route prefix (`/api/hr/*` vs `/api/employee/*`) and the employee id the browser sends.
- [x] **4. Grounding and bounded execution.**
  - The consider agent now has `get_enrollment_policy` (it was passed the policy but could not read it).
  - Leave intake now has `get_approved_leave_policy`. A new explicit synthetic entry, `DEMO-LEAVE-BALANCES@v1`, replaces the invented sick-versus-PTO rule. A balance statement that does not cite it is replaced with "HR will confirm which balance applies". Likely documents come from the policy table, not the model.
  - The cost summary reads the vesting rule from `retirement_plan.vesting_schedule` and cites `DEMO-401K-VESTING@v1`; no data means no claim.
  - One `TimeBudget` per user action (`runner.py`), shared by the agent and any specialist it consults. Default 90 s (`ANTHROPIC_ACTION_BUDGET_SECONDS`, 10-110), under the page's 120 s action timeout. Each attempt is capped to its share of the remaining time so SDK retries cannot overrun it; a specialist is not started with under 5 s left. A timeout is reported as a clear, recoverable message and the checked results still show.
- [x] **5. Complete-demo validation and documentation.** Browser rehearsal below; this handoff, the execution board and the demo script are updated.

## Demo data and self-test additions (after the five tasks)

- **More realistic synthetic data**, added alongside (not replacing) the original records: new hires E2007-E2012 and current employees E1006-E1009, with carrier confirmations and document records. The originals back the tests and the earlier rehearsals and are unchanged.
- **Reset demo data**: `CaseStore.reset()` and `/api/demo/reset` forget every case, draft, edit and chat and re-read the data files, so editing the JSON and resetting takes effect without a restart. A button at the top of every page calls it. Demo only; the server listens on 127.0.0.1.
- **`docs/FUNCTIONAL-TEST-GUIDE.md`**: a person-by-person table and 18 numbered tests. `tests/test_demo_scenarios.py` pins each person's behavior, and the guide was followed literally in a browser (56/56 checks, scripted model, not live).
- Error messages no longer hardcode ID ranges.

## Behavior changed (summary for reviewers)

- HR approval of an enrollment can now be refused as stale or incomplete based on live data, not the saved review.
- New statuses and routes: `approved_documents_received`; `/api/hr/evidence/verify`, `/api/hr/leave/resolve`, `/api/employee/leave/document`, `/api/employee/leave/resubmit`. `hr_decide` accepts an optional `expected_revision`.
- Employee responses no longer contain `hr_flags` or `enrollment_state`.
- Cost summary: `retirement_employer_match` no longer includes vesting text; `retirement_vesting` carries the data-driven rule and its policy ref.
- Leave intake: `balance_note` and `documents_likely_needed` are now constrained as above.
- The public GitHub Pages demo (`docs/index.html`, `site/demo.js`) is unchanged in behavior; it was rebuilt because the shared data gained a policy entry.

## Verification actually performed

On 2 November, on the continuation branch:

- **196 Python tests pass** (`python3 -m unittest`), including the website-parity test (Python vs `site/demo.js`) and a check that `docs/index.html` is current.
- **31 frontend tests pass** (`node --test tests/frontend.test.mjs`).
- Regression tests were shown to **fail without** each fix, and key behaviors were **mutation-checked** (removing a guard makes a test fail). One mutation (the consultation-level budget check) initially survived because the runner enforces the budget too; a test for the 1-5 second window was added.
- **Browser rehearsal, 37/37 checks, no console errors** (headless Chromium against the real server and page, with a scripted model; no Anthropic call). Journeys: E2002 enrollment check, HR approval, frozen handoff, prepare, simulated sending, confirmation check, per-issue drafts; E2004 seeded mismatch with Vendor-to-Enrollment consultation; E2001 enrollment question, received-versus-verified, HR verifies a document; E2003 shows no HR flag text to the employee; E1001 leave draft, confirmation, conditional approval, documents provided, HR resolution; E1002 information request and same-case correction; a stale HR approval refused and the page reloading the latest version; and a model that always fails (employee check, HR vendor check) with a clear message and working checks.
- An earlier rehearsal run found a real UX gap (after a refused stale approval the page kept the old version); it was fixed by the `stale` flag and covered by tests.

**Not verified:** nothing in this continuation used a live model or a real key. The live runs recorded in `DEMO-SCRIPT.md` are earlier-session results for the earlier journey. Run `readiness --live` and rehearse the new interactive paths with a working key before claiming live behavior.

## Remaining limitations

- No live-model rehearsal of the new paths (election consideration, free-text leave intake, the new policy tools, the verbatim flag guard, the time budget under real latency).
- The employee-message flag guard catches a verbatim copy only; a paraphrase relies on the prompt. It is defense in depth, not a proof.
- Demo identity only: the browser chooses the employee, and "HR" is the `/api/hr/*` route prefix. This is not authentication or authorization.
- Cases, evidence changes and drafts live in memory and reset on restart. Document upload is metadata only (no file stored).
- Verifying a document or resolving pending leave documents records that HR checked it; there is no reviewer identity, timestamp history or reversal.
- HR cannot reject a received enrollment document with a reason from the UI (it can request information on the case instead).
- Enrollment resubmission after an information request is the existing "Recheck enrollment" action; there is no separate form.
- The time budget bounds model time, not tool time (tools are local and fast) or browser network time.
- The public website is a separate, simplified static demo (example agent text, no editing flows).

## File map

- `workflow.py`: election/dependent mutations, cost summaries, leave intake and new decision state.
- `web.py`: employee projections and five added action routes.
- `agents.py`: unsaved-choice explanation, free-text leave intake and vendor document-request wording.
- `frontend/js/`: new forms, API calls and rendering.
- `hr_lookup.py` / fictional JSON: categorized balances, plan metadata and people.
- `tests/`: `test_stale_review.py`, `test_privacy.py`, `test_transitions.py`, `test_grounding.py` plus extended `frontend.test.mjs`.
- `runner.py`: `TimeBudget` and the action-budget setting.

The other checkout `Multi-Agent-HR` was left untouched. Its renamed fixtures and rehearsal/documentation edits are represented in this newer branch; continue development in a single agreed checkout to avoid diverging copies. No credentials, virtual environment or local runtime logs are part of the handoff.
