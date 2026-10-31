# Execution board

**Status: proposed work, not started.** This board scaffolds the next development phase. Owners and implementation branches are unassigned until we agree together. Checkboxes below are acceptance criteria, not completed features.

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
- [ ] Confirm the key provider; keep credentials in a local ignored configuration file.
- [ ] Verify a supported model and request parameters, with bounded timeout/retries.
- [ ] Make key/model readiness visible without exposing secrets or making model calls on page browse.
- [ ] Agree endpoint payloads and claim work packages before coding.

## P1: Employee enrollment and HR review

- [ ] Wire explicit enrollment check to the current endpoint; browsing stays read-only.
- [ ] Show loading, success and recoverable error states without duplicate requests.
- [ ] Display the created case and HR-only summary in the appropriate workspace.
- [ ] HR can approve, deny or request information with existing guards and required reasons.
- [ ] An incomplete enrollment cannot be approved; errors keep the user's input available.

Checkpoint: a complete profile reaches HR approval; an incomplete profile remains blocked.

## P2: Vendor journey

- [ ] HR can prepare records only after approval and explicitly mark them sent.
- [ ] Compare confirmations against the frozen handoff, not a later election edit.
- [ ] Show pending, missing, confirmed and discrepant results distinctly.
- [ ] Display follow-up drafts as drafts; no external sending is added.
- [ ] Keep employee updates separate from internal provider investigation details.

Checkpoint: the seeded E2004 mismatch is easy to explain in the new interface.

## P3: Evidence and clarification

- [ ] Introduce scoped fictional evidence references with absent/received/verified states.
- [ ] Keep employee claims separate from verified records.
- [ ] Retrieve a small approved policy library with explicit version/source labels.
- [ ] Ask one targeted question when useful; preserve the clarification context.
- [ ] Do not change approval state or issue a formal HR notice during clarification.

Checkpoint: "I already uploaded it" gets different grounded responses for absent, received and verified evidence. No real document uploading is required.

## P4: Specialist consultation

- [ ] Vendor Agent can request an Enrollment Agent finding through workflow code.
- [ ] Validate the case, employee and approved-snapshot reference before invoking a specialist.
- [ ] Limit consultation count and total model work; disallow recursive consultation.
- [ ] Carry evidence references, unknowns and a proposed next action in the reply.
- [ ] Include the specialist result in the Vendor Agent's final findings/draft.
- [ ] A failed consultation returns an explicit unknown and leaves HR in control.

Checkpoint: the consultation actually changes or substantiates the final HR follow-up. Three static labels are not the demonstration.

## P5: Leave journey

- [ ] Help clarify dates/type/schedule without promising eligibility.
- [ ] Show a structured draft for employee confirmation before formal submission.
- [ ] Display missing information and a separate HR pre-check.
- [ ] Preserve unknown employment facts as "cannot determine."
- [ ] HR decides, and the employee sees only the permitted update.
- [ ] Clarification and formal HR requests/notices remain separate events.

Checkpoint: one synthetic leave case goes from incomplete draft to HR review. A failed FMLA pre-check does not automatically deny every leave option.

## P6-P7: Presentation and quality

- [ ] A compact case activity view shows actor, useful findings, evidence and next step.
- [ ] Keyboard, narrow-screen, loading, error and empty states remain usable.
- [ ] Tests cover missing data, approval guards, frozen handoffs, scope and consultation budgets.
- [ ] Runtime failure preserves deterministic results and clearly labels unavailable AI.
- [ ] Two clean-start rehearsals succeed using the actual key and chosen model.
- [ ] README and demo instructions reflect actual implemented behavior.
- [ ] Feature PRs describe what changed, how it was checked and what remains limited.

## Live presentation route

About seven minutes: problem (1), benefits and consultation (3), leave (1), architecture (1), limitations and next work (1). Keep the browser on the relevant case rather than opening several dashboards. Do not show the key, environment contents or real employee records.

## Scope limits

Use fictional records and the existing app architecture. No real carrier/payroll connections, production login, real medical uploads, full legal decision engine, new AI manager or visual redesign. Case storage remains in memory unless we separately agree on persistence. Do not claim a live-model result when displaying a deterministic fallback.

## If the schedule slips

Preserve P1-P4 and their boundary checks as the first complete story. Keep the existing leave workflow available as a clearly labeled reference if the new leave integration is unfinished. Cut decorative motion and optional activity filtering first. Report any unfinished acceptance criteria honestly instead of representing them as completed.
