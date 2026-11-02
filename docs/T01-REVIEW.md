# T01 — Benefits baseline review

31 October 2026. Technical review completed on `review/t01-benefits-baseline`, based on `feat/connect-benefits-workflow` at `1f4bc09`. This is a proposed continuation base, not a merge into main or a claim of human approval.

## What was reviewed

- Explicit frontend action wiring and single-action/uncertain-response handling.
- Employee-safe guidance projections and HR-only case content.
- E2002 enrollment → approval → frozen vendor preparation → marked sending → confirmation follow-up.
- E2001 incomplete approval guard and reason requirements.
- E2004's employee-only approved medical tier versus the family-tier fixture reply, plus pending dental.
- Existing Python/static-demo parity and frozen-handoff tests.

## Finding and fix

Rechecking an already-decided enrollment still invoked the Enrollment Agent before returning the existing case. If underlying elections changed, the endpoint could return fresh guidance beside the saved historical decision. This also wasted a model request.

The workflow now checks case state first and returns its saved enrollment, guidance and availability result for approved, denied and provider-processing cases. It does not invoke AI, reopen the case, alter history or replace the approved handoff. Open and information-requested enrollments remain recheckable. The browser-only demo mirrors the change and its generated page was rebuilt.

## Evidence

55 Python tests and 16 frontend tests passed after the fix. New regression coverage checks all decided/provider states, unchanged case/history, no added model requests despite later election edits, correct endpoint guidance and continued rechecking after an information request. The static/Python parity scenario now includes a decided-case recheck. Whitespace checks passed.

The preceding integration checkpoint's browser checks remain recorded in [Benefits workflow](BENEFITS-WORKFLOW.md). This review changes no frontend interaction code and does not claim a new live-model run or new screenshot review.

## Outcome and next step

Technical review is complete with the identified issue fixed. Human review and merges remain pending; the review fix is intended to land on the benefits implementation branch before that implementation lands on main. Do not automatically merge either PR.

Next implementation task: T02, configurable private model/key setup and readiness. Existing limitations remain: no successful live-model validation, in-memory cases, demo identities, no actual provider sending, no specialist consultation or new leave submission yet.
