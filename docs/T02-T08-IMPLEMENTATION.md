# T02–T08 implementation record

1 November 2026. Implemented as stacked task branches on top of the T01 review base (`07c4461`): `feat/t02-ai-readiness` → `feat/t03-evidence-policy` → `feat/t04-enrollment-clarification` → `feat/t05-specialist-consultation` → `feat/t06-leave-journey` → `feat/t07-t08-activity-and-checks` → `docs/t10-demo-handoff`. Each branch contains the previous one. Nothing is merged to main and nothing was pushed automatically. Entries use the [task log](https://github.com/JoanAlbayrak/AI-Powered-Benefits-and-Leave-Management-/blob/docs/prioritized-plan-and-task-log/docs/TASK-LOG.md) template so they can be copied there.

**Verification for the whole stack:** 105 Python tests and 24 frontend tests pass (scripted/fake model). A Playwright walkthrough against the local server with a scripted model covered E2001 Q&A and enrollment check, the C1/E2004 consultation, the E1001 draft → confirm → HR request-info path, and a 390px layout check. No console errors, no horizontal overflow. A smoke run of the real server with no key confirmed the deterministic fallbacks. **No live-model call has been made**: that is T09.

## T02 — Live AI configuration and readiness

- **Changed:** `runner.py` now reads model, effort, timeout, retries and a disable switch from `.env`. It calls the standard `client.messages.create` with `output_config.effort` and drops the unverified beta/fallback parameters. A missing or placeholder key raises a clear `AIUnavailable`. Agent tools can now take validated inputs, and tool exceptions go back to the model as errors. There's a new `benefits_leave/readiness.py` (`--live` makes one structured call), a new `/api/ai/status` endpoint, a status badge in the app, server start-up diagnostics, clearer SDK error messages and an updated `.env.example`.
- **Accomplished:** the presenter adds only a key. Readiness never calls the model on page browse and never returns the key.
- **Verified:** `tests/test_runtime.py`.
- **Limits:** the model ID and effort settings still need a live run with the real account.

## T03 — Evidence, policy and snapshot references

- **Changed:** `data/benefits_demo.json` has new fictional `evidence` records (absent/received/verified), a versioned `policy_library` (synthetic employer rules; the FMLA summary is labeled illustration-only) and new hires E2005 (proof absent) and E2006 (proof verified). E2001's marriage certificate is now *received*. `checks.py` adds `evidence_for`, `evidence_status`, `policy_entries`, `snapshot_ref_for` and `approved_snapshot_record`. Handoffs carry `snapshot_ref`; the static demo mirrors this and `docs/index.html` was rebuilt.
- **Compatibility decision:** only verified proof sets `proof_received`, so received proof leaves the completeness item open. The approval guard is unchanged.
- **Verified:** `tests/test_evidence_policy.py`, which includes the fixture-consistency, scope and later-edit-immunity checks.

## T04 — Enrollment clarification

- **Changed:** `run_enrollment_help` gets an employee-safe status (no HR flags), the employee's own documents, enrollment policy and plan options. The question is wrapped as unverified text, with the last three turns as context. Code drops any evidence or policy refs that aren't in scope. There's a new `/api/employee/enrollment/help` endpoint, plus *Your documents* and *Ask the Enrollment Agent* panels with example questions.
- **Accomplished:** "I already uploaded it" gets three different grounded answers for absent, received and verified, with one follow-up question only when useful. Facts from the records still show when AI is unavailable. No case or status changes.
- **Verified:** `tests/test_enrollment_help.py`.

## T05 — Vendor → Enrollment consultation

- **Changed:** the Vendor Agent has a `consult_enrollment_specialist` tool and vendor policy. `CaseStore._consultation_router` checks the question type and the benefit against the case's frozen snapshot, and derives the employee from the case. It allows one consultation per vendor check and records each request and reply with its model-call count. `run_enrollment_specialist` (max 4 turns) reads the frozen record with plan costs by tier, the dependents and proof documents, and policy. It has no consultation tool. Follow-ups carry `evidence_refs`, and there are new *Specialist consultation* and *Agent activity* panels.
- **Accomplished:** for E2004 the specialist confirms Silver PPO employee-only, with no dependents or proof on record and $230 vs $78, and the Acme Health draft cites `C1:approved:1/records/medical`. Out-of-scope, over-budget and failed consultations become explicit *unavailable* replies, and HR stays in control.
- **Verified:** `tests/test_consultation.py`, covering draft change, frozen snapshot, budget, fresh budget on recheck, scope rejection without a specialist run, failure, no recursion and employee privacy.
- **Limits:** whether the live model chooses to consult is prompted, not forced. Code records "did not consult" as an unknown if it skips.

## T06 — Leave draft, confirmation and HR review

- **Changed:** `save_leave_draft` and `confirm_leave_draft` give the employee a server-owned draft. The schedule is required, documents are filtered to the leave type's list, and notes are capped. `run_leave_clarifier` gets no FMLA facts or FMLA policy. There are new `/api/employee/leave/draft` and `/confirm` endpoints, and the leave page is now a working form with draft review and explicit confirmation. HR sees the request details, the unverified employee note, the source draft and the FMLA detail.
- **Accomplished:** a draft is never a case. Only the employee's confirmation of the exact saved draft creates one. Missing documents may still go to HR, but approving an incomplete request still needs a reason. "Cannot determine" stays unknown, and failing FMLA basics never denies.
- **Verified:** `tests/test_leave_journey.py`.
- **Limits:** there's no correction or resubmission after an HR information request.

## T07–T08 — Activity view and system checks

- **Changed:** every case has a structured `activity` list (actor, action, finding, evidence refs, unknowns, next step, visibility). Employees see only steps marked employee-visible. The raw history is kept unchanged for static-demo parity. There are frontend tests for the new panels, and the confirm button now stays disabled for a draft that isn't ready (a bug found in browser testing).
- **Verified:** see the stack verification above.

## T09 — Live rehearsal (owner: presenter)

Not done: it needs the real key. Follow [DEMO-SCRIPT.md](DEMO-SCRIPT.md) and fill in its rehearsal log.
