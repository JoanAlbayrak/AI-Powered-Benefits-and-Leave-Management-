# Benefits workflow integration checkpoint

## Delivered in this slice

The redesigned interface now uses the existing backend for enrollment checks, HR decisions, vendor-record preparation, a simulated sending event and confirmation review. It does not introduce new eligibility rules, provider integrations or agent-to-agent calls.

Opening a page stays read-only. A labeled action button is required to run an agent or change a case. The employee sees only their own permitted guidance and updates; HR sees the internal checks, summaries, approved records and follow-up drafts.

## Try it from a clean server start

```sh
python3 -m benefits_leave.web
```

The usual URL is http://127.0.0.1:8001. Use the port printed by your server if it differs. All dates use the displayed fictional snapshot date, not today's real date.

1. Choose **Employee preview**, profile **E2002**, then **My benefits**.
2. Choose **Check enrollment and create case**. If AI is unavailable, a case is still created and the checklist remains available.
3. Switch to **HR preview**, open E2002's case from the queue, choose **Approve**, then **Record HR decision**.
4. Choose **Prepare vendor records**. These records come from the frozen HR-approved packet.
5. Confirm the simulated sending checkbox, then choose **Record simulated sending**. Nothing is transmitted.
6. Choose **Check confirmations**. E2002 has no fixture confirmations, so follow-up drafts are expected rather than successful coverage confirmation.
7. For an actual fixture discrepancy, open **C1 / E2004** and check confirmations. Approved medical tier is employee-only; the fictional carrier reply says family. Dental is pending; vision and retirement match.
8. For the approval guard, check **E2001** enrollment. In HR review, approval is disabled while missing information remains. Request information or deny only with a reason. Switch back to E2001 to see the employee-visible update.

Restarting the server resets cases. Rechecking enrollment reuses an eligible open case rather than creating another enrollment case. Editing elections and submitting proof remain future work; use the complete fixture to demonstrate approval.

## Reliability behavior

- Only one UI workflow action runs at a time, including across role/profile navigation.
- Action errors keep decision input available for correction.
- Mutations use a bounded 120-second browser timeout and no automatic retry.
- If a response is lost, the UI says the action may have completed and blocks further mutations. **Refresh latest status** returns to the originating workspace and reads it before unlocking actions. This does not provide server-side idempotency or concurrency control across browser sessions.
- Results from a completed action stay associated with its submitting workspace rather than appearing in a different employee's view.
- The HR decision is shown separately from the later provider-processing status.
- Missing AI does not hide deterministic results. Provider draft templates are explicitly labeled as rule-based fallback when the model is unavailable.

## Verification

53 Python tests and 16 frontend tests pass. Added coverage checks saved employee guidance/privacy, the no-AI HR/vendor path, endpoint payloads, duplicate-action blocking, mutation timeout/lost-response behavior, scoped reconciliation, decision controls and escaping generated content.

Browser checks on the local server covered E2002 check/approval/preparation/simulated sending/follow-ups; E2001 approval blocking and reasoned information request; employee-visible update; and E2004's tier discrepancy/pending results. Browser logs showed no warnings/errors on the inspected flow. A 390px viewport check found no page-level horizontal overflow on the vendor case. Screenshot capture was unavailable in the browser tool, so pixel-level visual verification remains a review item; interaction/accessibility state and layout dimensions were checked.

## Remaining work

- Live AI setup: install the runtime dependency in a local virtual environment, supply the private key, validate model/SDK settings and test a real response. No successful live-model call is claimed by this checkpoint.
- Evidence absent/received/verified states and targeted clarification.
- A bounded Vendor-to-Enrollment consultation and structured agent activity.
- New leave draft, confirmation, submission and correction flow. Existing leave cases created through `/legacy` can be reviewed using the shared HR decision controls.
- Production identity, persistent storage and real document/provider integrations remain outside this fictional demo slice.

The original proposal/report is a design snapshot. Its future-state examples are not an implementation checklist marked complete.
