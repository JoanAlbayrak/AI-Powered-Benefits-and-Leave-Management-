# Execution board

**2 November (continuation) update:** the five tasks that blocked the interactive extension are done on `claude/jolly-edison-vkgp9d` (stale-approval fix, employee/HR privacy, document and correction transitions, grounding and a shared time budget, demo validation). They are verified offline and in a browser rehearsal against a scripted model (196 Python, 31 frontend tests, 37/37 rehearsal checks). **No live-model verification of the new paths has been done.** Details and limitations: [Joan handoff](JOAN-HANDOFF.md).

**2 November update:** the original task stack is merged through PR #13 (and benefits integration through PR #4). The latest interactive extension is a separate work-in-progress branch. See [Joan handoff](JOAN-HANDOFF.md) for completed additions, reproduced blockers and remaining tasks. Historical status below describes the earlier checkpoint.

**Status (1 November 2026): P1/P2 on `feat/connect-benefits-workflow`; P0 setup, P3–P6 and the P7 automated checks implemented on the T02–T08 task branches (see [implementation record](T02-T08-IMPLEMENTATION.md)).** Live rehearsal with the real key (P7/T09) passed on 2026-11-01. Feature PRs for T02–T08 and human review/merge remain open. Checked items describe implementation branches, not merges.

Target: a presentable local live demo by Sunday evening, ready for Monday, 2 November 2026. Time boxes are estimates, not promises. If time becomes tight, complete and stabilize the first journey before expanding scope.

## Demo we want to show

1. Employee reviews enrollment and gets a useful explanation.
2. HR reviews, approves, prepares records and explicitly records sending.
3. A fictional provider confirmation differs from the approved election.
4. Vendor Agent consults Enrollment Agent about the approved intent, then drafts a grounded follow-up.
5. Another employee clarifies a leave request and confirms it before HR review.

The current seed case E2004 has **employee-only** medical coverage approved, while its fixture confirmation says **family**. Do not accidentally demonstrate the reverse as if it were the existing record. The report's Maya story is an illustrative alternative, not the current fixture.

## Work packages

| ID | Work package | Estimate | Depends on | Suggested workstream |
|---|---|---|---|---|
| P0 | Agree on scope and live-model setup | 45 min | Joint review | Together |
| P1 | Connect enrollment and HR review | 2.5 h | P0 | UI integration with backend review |
| P2 | Connect provider preparation and confirmation review | 1.5 h | P1 | UI integration |
| P3 | Evidence status, policy references and clarification | 1.5-2 h | P0; agree contracts | Backend/agent work |
| P4 | Bounded Vendor-to-Enrollment consultation | 1.5-2 h | P2, P3 contracts | Backend/agent work |
| P5 | Leave clarification, confirmation and HR review | 2 h | P1; P3 pattern | Joint integration |
| P6 | Agent activity display and usability pass | 1.5 h | P4, P5 | UI integration |
| P7 | Boundary tests, live rehearsal and PR review | 2-3 h | Working journey | Together |

Two people can work on separate modules after agreeing the contracts. Avoid concurrent edits to `app.js`, `web.py` and `workflow.py` without coordinating. A sensible split is one owner for P1/P2/UI and another for P3/P4/backend, with both reviewing P5-P7. These are suggested responsibilities, not assignments to either teammate.

## P0: Scope and runtime

- [ ] Both teammates can inspect the scaffold and explain the same demo story.
- [x] Confirm the key provider; keep credentials in a local ignored configuration file.
- [x] Verify a supported model and request parameters, with bounded timeout/retries. *(Configurable model, standard `output_config.effort`, timeout and retries; live verification is the T09 rehearsal.)*
- [x] Make key/model readiness visible without exposing secrets or making model calls on page browse.
- [ ] Agree endpoint payloads and claim work packages before coding.

## P1: Employee enrollment and HR review

- [x] Wire explicit enrollment check to the current endpoint; browsing stays read-only.
- [x] Show loading, success and recoverable error states without duplicate requests.
- [x] Display the created case and HR-only summary in the appropriate workspace.
- [x] HR can approve, deny or request information with existing guards and required reasons.
- [x] An incomplete enrollment cannot be approved; errors keep the user's input available.

Checkpoint: a complete profile reaches HR approval; an incomplete profile remains blocked.

## P2: Vendor journey

- [x] HR can prepare records only after approval and explicitly mark them sent.
- [x] Compare confirmations against the frozen handoff, not a later election edit.
- [x] Show pending, missing, confirmed and discrepant results distinctly.
- [x] Display follow-up drafts as drafts; no external sending is added.
- [x] Keep employee updates separate from internal provider investigation details.

Checkpoint: the seeded E2004 mismatch is easy to explain in the new interface.

## P3: Evidence and clarification

- [x] Introduce scoped fictional evidence references with absent/received/verified states.
- [x] Keep employee claims separate from verified records.
- [x] Retrieve a small approved policy library with explicit version/source labels.
- [x] Ask one targeted question when useful; preserve the clarification context.
- [x] Do not change approval state or issue a formal HR notice during clarification.

Checkpoint: "I already uploaded it" gets different grounded responses for absent, received and verified evidence. No real document uploading is required.

## P4: Specialist consultation

- [x] Vendor Agent can request an Enrollment Agent finding through workflow code.
- [x] Validate the case, employee and approved-snapshot reference before invoking a specialist.
- [x] Limit consultation count and total model work; disallow recursive consultation.
- [x] Carry evidence references, unknowns and a proposed next action in the reply.
- [x] Include the specialist result in the Vendor Agent's final findings/draft.
- [x] A failed consultation returns an explicit unknown and leaves HR in control.

Checkpoint: the consultation actually changes or substantiates the final HR follow-up. Three static labels are not the demonstration.

## P5: Leave journey

- [x] Help clarify dates/type/schedule without promising eligibility.
- [x] Show a structured draft for employee confirmation before formal submission.
- [x] Display missing information and a separate HR pre-check.
- [x] Preserve unknown employment facts as "cannot determine."
- [x] HR decides, and the employee sees only the permitted update.
- [x] Clarification and formal HR requests/notices remain separate events.

Checkpoint: one synthetic leave case goes from incomplete draft to HR review. A failed FMLA pre-check does not automatically deny every leave option.

## P6-P7: Presentation and quality

- [x] A compact case activity view shows actor, useful findings, evidence and next step.
- [x] Keyboard, narrow-screen, loading, error and empty states remain usable. *(Browser walkthrough: no console errors, no horizontal overflow at 390px.)*
- [x] Tests cover missing data, approval guards, frozen handoffs, scope and consultation budgets.
- [x] Runtime failure preserves deterministic results and clearly labels unavailable AI.
- [x] Two clean-start rehearsals succeed using the actual key and chosen model. *(2026-11-01: readiness `--live` passed on claude-opus-5-5; two independent clean-start server instances both completed the enrollment check, Q&A, vendor mismatch + Vendor→Enrollment consultation, and leave draft→clarify→confirm→HR-approve journeys live with no errors.)*
- [x] README and demo instructions reflect actual implemented behavior.
- [ ] Feature PRs describe what changed, how it was checked and what remains limited.

## Interactive extension (continuation work)

Checked items are implemented and verified as stated in the [handoff](JOAN-HANDOFF.md); none is live-verified.

- [x] **X1 Stale approval:** edits refresh the open review; approval revalidates against live data and the revision HR saw; conflicts reload the latest case. *(Regression-tested; shown to fail without the fix.)*
- [x] **X2 Privacy:** one employee enrollment projection; no `hr_flags` or `enrollment_state` in employee responses; flag-copy guard on the employee message. *(Endpoint-walk test for E2003 and E1003.)*
- [x] **X3 Transitions:** HR verifies received proof; pending leave documents requested → received → verified/asked again/withdrawn; same-case correction after an information request. *(Backend rules and UI; browser rehearsal.)*
- [x] **X4 Grounding and limits:** consider and intake agents read the approved policy; `DEMO-LEAVE-BALANCES@v1` replaces the invented balance rule; vesting from plan data with its policy ref; shared per-action time budget (default 90 s, under the 120 s page timeout).
- [x] **X5 Validation and docs:** browser rehearsal 37/37 with a scripted model; handoff, board and script updated.
- [ ] **X6 Live rehearsal of the new paths with a working key** (election consideration, free-text leave intake, new policy tools, budget under real latency). Not done.
- [ ] **X7 Review and merge** of the feature PR by a human. Not merged.

## Live presentation route

About seven minutes: problem (1), benefits and consultation (3), leave (1), architecture (1), limitations and next work (1). Keep the browser on the relevant case rather than opening several dashboards. Do not show the key, environment contents or real employee records.

## Scope limits

Use fictional records and the existing app architecture. No real carrier/payroll connections, production login, real medical uploads, full legal decision engine, new AI manager or visual redesign. Case storage remains in memory unless we separately agree on persistence. Do not claim a live-model result when displaying a deterministic fallback.

## If the schedule slips

Preserve P1-P4 and their boundary checks as the first complete story. Keep the existing leave workflow available as a clearly labeled reference if the new leave integration is unfinished. Cut decorative motion and optional activity filtering first. Report any unfinished acceptance criteria honestly instead of representing them as completed.
