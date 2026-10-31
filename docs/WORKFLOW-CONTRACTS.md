# Workflow contracts

The current endpoints below exist; enrollment, HR decisions and vendor actions are now wired into the new UI. The proposed tools, models, endpoint paths and output fields later in this document do not exist yet. Agree them before implementation; do not build a frontend against a proposed route as if it were already available.

## Ownership boundaries

| Layer | Owns |
|---|---|
| `checks.py` | Required fields, dates, arithmetic, deterministic comparisons and flags |
| `agents.py` / `runner.py` | Scoped evidence retrieval, explanations, clarifications and structured model output |
| `workflow.py` | Case state, approvals, frozen handoffs, permitted consultation routing and history |
| `web.py` | Request validation and role-appropriate response projections |
| Frontend API adapter | Explicit requests, loading/error handling and response rendering |

No business eligibility rule belongs in a frontend component. No agent tool may approve, deny, send externally or mutate an employee election. A model's structured submit result is an output for code to handle, not authority to perform the proposed next action.

## Current HTTP API

All listed routes currently use JSON POST requests. The existing server reports workflow errors as `{"error": "message"}` in an HTTP 200 response; the frontend adapter already translates these. Changing this behavior requires updating both callers and tests.

| Route | Request fields | Effect / response |
|---|---|---|
| `/api/people` | None | Fictional demo identities; read-only |
| `/api/employee/overview` | `employee_id` | Read-only employee projection; no model call or case creation |
| `/api/employee/cases` | `employee_id` | Employee-safe case projections |
| `/api/employee/enrollment` | `employee_id` | Runs enrollment check/agent; creates or updates an eligible open case; returns `case`, `enrollment`, `message`, `ai_error` |
| `/api/employee/leave` | `employee_id`, `leave_type`, `start_date`, `end_date`, `reason`, `documents_attached` | Checks request and creates a leave case; returns `case`, `missing`, `message`, `ai_error` |
| `/api/hr/queue` | None | Internal case list; read-only |
| `/api/hr/decide` | `case_id`, `decision`, `reason` | Controlled HR decision; returns `case` |
| `/api/hr/vendor/prepare` | `case_id` | Prepares frozen approved records; returns `case` |
| `/api/hr/vendor/sent` | `case_id` | Records HR's sending step; performs no external transmission |
| `/api/hr/vendor/check` | `case_id` | Checks provider confirmations and runs Vendor Agent; returns `case` |

Decision values: `approve`, `deny`, `request_info`. `documents_attached` is a list of synthetic document labels, not actual file upload. The current server uses demo identity selection rather than authorization; projection filtering is not production access control.

Enrollment case projections now also include employee-only `guidance` and `ai_error`, so the last explanation or unavailability message survives a workspace refresh. HR-only summaries, handoffs and history are still excluded. New UI mutations allow up to 120 seconds, are never automatically retried, and block other mutations after an ambiguous transport result until a successful read of the originating workspace. This is browser-local coordination, not server-side idempotency or multi-user locking.

### Existing case states

```text
Enrollment check -> incomplete OR ready_for_hr_review
HR decision -> approved OR denied OR info_requested
Approved enrollment -> vendor_records_ready -> sent_to_vendors
Confirmation review -> vendor_follow_up OR vendor_confirmed

Leave submission -> ready_for_hr_review (may still contain missing items)
HR decision -> approved OR denied OR info_requested
```

The current HR decision guard accepts cases in `incomplete` or `ready_for_hr_review`. Correction/resubmission from `info_requested` is not a general-purpose implemented flow: enrollment rechecking can reopen it, while leave correction/resubmission needs its own design. Do not add a nonworking "resubmit" button.

## Proposed additions: agent-run context

Keep business case state separate from the progress of one AI interaction. A conversation must not implicitly issue an HR notice or approve a case.

```json
{
  "run_id": "RUN-EXAMPLE-1",
  "case_id": "C1",
  "employee_id": "E2004",
  "agent": "vendor",
  "state": "awaiting_specialist",
  "policy_refs": ["DEMO-ENROLLMENT-v1#dependent-proof"],
  "approved_snapshot_ref": "C1:approved:1",
  "unknowns": ["Whether the carrier processed a newer transaction"]
}
```

Example values are illustrative. Suggested run states: `running`, `awaiting_employee`, `awaiting_specialist`, `completed`, `unavailable`. The current handoff has no explicit snapshot version: introduce a stable reference before relying on one. Record source/evidence pointers and useful results, not hidden chain-of-thought.

## Proposed consultation contract

Start with one allow-listed question type: Vendor asks Enrollment about the **approved enrollment intent**. Code derives the employee and handoff from the selected case rather than trusting identity supplied by a model.

```json
{
  "request_id": "CONSULT-EXAMPLE-1",
  "case_id": "C1",
  "from_agent": "vendor",
  "to_agent": "enrollment",
  "question_type": "approved_enrollment_intent",
  "approved_snapshot_ref": "C1:approved:1",
  "question": "Which medical plan and tier did HR approve?"
}
```

The receiving agent can read only the permitted frozen packet and relevant approved policy. It must not substitute current editable elections for the approved snapshot. Return a structured result for the requesting agent to incorporate:

```json
{
  "request_id": "CONSULT-EXAMPLE-1",
  "status": "answered",
  "finding": "The approved medical election is Silver PPO, employee-only.",
  "evidence_refs": ["C1:approved:1/records/medical"],
  "unknowns": ["Carrier correction status is not established"],
  "proposed_next_action": "Ask HR to review a carrier follow-up draft"
}
```

That answer matches the current E2004 approved tier; the fixture carrier confirmation says family. Unknown/missing/mismatched references must return `unavailable` or fail validation, not guessed findings. Code must check the reference belongs to the case, disallow cross-employee access, prevent recursive calls and bound model turns, consultation count and total run work. Proposed initial limit: one specialist consultation per vendor run, with no specialist callbacks.

The tool must be available when useful, and the requesting agent must actually incorporate its result. Merely running another prompt in the background without affecting the finding is insufficient evidence of meaningful collaboration.

## Proposed clarification contract

Suggested paths, **not current routes**:

| Proposed route | Responsibility |
|---|---|
| `/api/employee/enrollment/help` | Scoped question plus relevant evidence status; return explanation, source references and any targeted question |
| `/api/employee/leave/draft` | Prepare/clarify a draft without creating a formal submitted case |
| `/api/employee/leave/confirm` | Validate the employee-confirmed draft before calling the formal submission workflow |

The backend should own draft identifiers and scope validation. Do not rely on browser state alone to prove which employee confirmed which draft. Treat employee text as unverified content; it must not change system instructions or permissions.

Evidence metadata should distinguish `absent`, `received` and `verified`, include case/employee scope and identify who verified it. The existing `proof_received` boolean cannot represent all three states by itself. Decide how to map it without breaking completeness checks. No real uploads are needed for the first synthetic scenario.

## Proposed UI rendering contract

Render concise facts, missing information, cited sources, unknowns and next action. For HR only, include specialist request/reply and draft follow-ups. Employee projections must omit internal flags, HR notes and vendor investigation content unless explicitly approved as employee-visible.

Mutation requests need a longer, bounded timeout appropriate for model work than the current 12-second read timeout. Disable duplicate submission while a request runs. A browser timeout does not prove the server action failed: refresh/reconcile case state before retrying a mutation, and consider idempotency for case-creating requests.

When AI fails, deterministic results stay available and the UI says the explanation is unavailable. Do not silently substitute canned prose and label it live AI. No key is ever sent to the browser.

## Contract acceptance checks for the next PRs

- Browsing performs no model calls or case mutations.
- Only allowed user actions trigger mutation endpoints.
- Incomplete enrollment approval and invalid vendor transitions remain blocked.
- Later employee edits do not alter an approved packet.
- Specialist requests cannot cross employee/case/snapshot boundaries or exceed the budget.
- Consultation failures are visible unknowns and preserve deterministic results.
- Leave clarification does not submit a request or change formal HR state.
- Employee output does not expose HR-only history, flags or specialist packets.
- Unknown employment facts remain unknown rather than a negative eligibility result.
- Tests and UI copy distinguish current capabilities from planned ones.
