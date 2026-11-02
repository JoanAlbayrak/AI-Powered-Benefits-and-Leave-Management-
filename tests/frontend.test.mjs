import test from 'node:test';
import assert from 'node:assert/strict';
import { request, ApiError, api } from '../benefits_leave/frontend/js/api.js';
import { WorkflowController } from '../benefits_leave/frontend/js/workflows.js';
import { routeFromHash } from '../benefits_leave/frontend/js/state.js';
import { escape, statusBadge } from '../benefits_leave/frontend/js/components.js';
import { employeeView } from '../benefits_leave/frontend/js/views/employee.js';
import { hrView } from '../benefits_leave/frontend/js/views/hr.js';
import { decisionPanel, enrollmentGuidance, vendorActions, vendorDrafts, hrDocuments, pendingDocumentsPanel, requestedDocumentsPanel, leaveResubmitForm } from '../benefits_leave/frontend/js/workflow-ui.js';

test('deep links preserve case identity and separate employee and HR views', () => {
  assert.deepEqual(routeFromHash('#/employee/cases/C1'), { role: 'employee', page: 'cases', caseId: 'C1' });
  assert.deepEqual(routeFromHash('#/hr/cases/C1'), { role: 'hr', page: 'cases', caseId: 'C1' });
  assert.equal(routeFromHash('#/hr/not-a-page').page, 'not-found');
});

test('employee case views do not substitute another employee’s available case', () => {
  const html = employeeView({ page: 'cases', caseId: 'C9' }, { cases: [{ id: 'C1', kind: 'leave', status: 'approved' }] });
  assert.match(html, /Request not found/);
  assert.doesNotMatch(html, /Approved by HR/);
});

test('employee and generated HR text is escaped before HTML rendering', () => {
  const payload = '<img src=x onerror="alert(1)">';
  assert.doesNotMatch(escape(payload), /<img/);
  const html = hrView({ page: 'cases', caseId: 'C1' }, {
    people: [{ id: 'E1', name: payload }],
    cases: [{ id: 'C1', employee_id: 'E1', kind: 'leave', status: 'ready_for_hr_review', ai: { hr_summary: payload }, history: [payload] }],
  });
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /&lt;img/);
});

test('marking records sent is visually distinct from confirmed coverage', () => {
  assert.doesNotMatch(statusBadge('sent_to_vendors'), /pill success/);
  assert.match(statusBadge('vendor_confirmed'), /pill success/);
});

test('backend workflow errors are surfaced even when HTTP reports success', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ error: 'Employee not found' }) });
  await assert.rejects(request('/api/employee/overview'), error => error instanceof ApiError && error.message === 'Employee not found');
});

test('failed connections produce an actionable error rather than an empty workspace', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); };
  await assert.rejects(request('/api/people'), /local server is running/);
});

test('an already-aborted request is handled as a canceled or timed-out request', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async (_path, options) => {
    assert.equal(options.signal.aborted, true);
    throw new DOMException('Aborted', 'AbortError');
  };
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(request('/api/people', {}, { signal: controller.signal }), /took too long/);
});

test('workflow API sends only the selected identity or case and explicit HR input', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  const calls = [];
  globalThis.fetch = async (path, options) => {
    calls.push([path, JSON.parse(options.body)]);
    return { ok: true, json: async () => ({ case: { id: 'C2' } }) };
  };
  await api.checkEnrollment('E2002');
  await api.decide('C2', 'request_info', 'Please clarify');
  await api.prepareVendor('C2');
  await api.markSent('C2');
  await api.checkVendor('C2');
  assert.deepEqual(calls, [
    ['/api/employee/enrollment', { employee_id: 'E2002' }],
    ['/api/hr/decide', { case_id: 'C2', decision: 'request_info', reason: 'Please clarify' }],
    ['/api/hr/vendor/prepare', { case_id: 'C2' }],
    ['/api/hr/vendor/sent', { case_id: 'C2' }],
    ['/api/hr/vendor/check', { case_id: 'C2' }],
  ]);
});

test('HR decisions carry the review revision HR opened, so a changed case is rejected by the backend', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  const calls = [];
  globalThis.fetch = async (path, options) => {
    calls.push(JSON.parse(options.body));
    return { ok: true, json: async () => ({ case: { id: 'C2' } }) };
  };
  await api.decide('C2', 'approve', '', 3);
  await api.decide('C2', 'deny', 'No', undefined);
  assert.deepEqual(calls, [
    { case_id: 'C2', decision: 'approve', reason: '', review_revision: 3 },
    { case_id: 'C2', decision: 'deny', reason: 'No' },
  ]);
});

test('lost mutation response is not retried or misreported as a failed action', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  let calls = 0;
  globalThis.fetch = async () => { calls++; throw new TypeError('Connection lost'); };
  await assert.rejects(api.markSent('C1'), error => error.outcomeUnknown && /may still have completed/.test(error.message));
  assert.equal(calls, 1);
});

test('mutation timeout is bounded and requires status reconciliation', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = (_path, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
  });
  await assert.rejects(request('/api/hr/decide', {}, { mutation: true, timeoutMs: 5 }), error => error.outcomeUnknown);
});

test('action controller prevents overlapping submissions even across navigation', async () => {
  const controller = new WorkflowController();
  let finish;
  const first = controller.execute('employee:E2002', () => new Promise(resolve => { finish = resolve; }));
  assert.equal(controller.pending, true);
  let duplicate = false;
  assert.deepEqual(await controller.execute('hr:C1', () => { duplicate = true; }), { accepted: false });
  assert.equal(duplicate, false);
  finish({ case: { id: 'C2' } });
  assert.equal((await first).result.case.id, 'C2');
  assert.equal(controller.blocked, false);
});

test('uncertain action stays blocked until its own workspace is successfully reconciled', async () => {
  const controller = new WorkflowController();
  await controller.execute('hr:C1', () => { throw new ApiError('Unknown', true); });
  controller.reconcile('employee:E2002');
  assert.equal(controller.blocked, true);
  assert.equal((await controller.execute('hr:C1', () => ({}))).accepted, false);
  controller.reconcile('hr:C1');
  assert.equal(controller.blocked, false);
});

test('a conclusive workflow rejection leaves the controller ready for corrected input', async () => {
  const controller = new WorkflowController();
  const out = await controller.execute('hr:C1', () => { throw new ApiError('A reason is required'); });
  assert.match(out.error.message, /reason/);
  assert.equal(controller.blocked, false);
});

test('incomplete enrollment blocks approval while leaving reasoned HR options available', () => {
  const html = decisionPanel({ id: 'C2', kind: 'enrollment', status: 'incomplete', enrollment: { missing: ['Proof'], hr_flags: [] } });
  assert.match(html, /value="approve" disabled/);
  assert.match(html, /value="request_info"/);
  assert.match(html, /id="hr-reason"/);
  assert.doesNotMatch(decisionPanel({ status: 'approved' }), /<form/);
});

test('vendor controls follow workflow state and never offer external sending', () => {
  const item = { id: 'C1', kind: 'enrollment' };
  assert.equal(vendorActions({ ...item, status: 'ready_for_hr_review' }), '');
  assert.match(vendorActions({ ...item, status: 'approved' }), /data-workflow-action="prepare"/);
  const ready = vendorActions({ ...item, status: 'vendor_records_ready' });
  assert.match(ready, /type="checkbox" name="confirmed" required/);
  assert.match(ready, /no records will be transmitted/);
  assert.match(vendorActions({ ...item, status: 'sent_to_vendors' }), /data-workflow-action="vendor-check"/);
  assert.doesNotMatch(vendorActions({ ...item, status: 'vendor_confirmed' }), /<button/);
});

test('employee guidance and provider drafts escape generated text and label unavailable AI', () => {
  const payload = '<img src=x onerror=alert(1)>';
  const employee = enrollmentGuidance({ status: 'incomplete', guidance: payload, ai_error: payload });
  const vendor = vendorDrafts({ vendor: { reconciliation: [], ai_error: payload, follow_ups: [{ vendor: payload, issue: payload, draft_message: payload }] } });
  for (const html of [employee, vendor]) {
    assert.doesNotMatch(html, /<img/);
    assert.match(html, /&lt;img/);
    assert.match(html, /unavailable/);
  }
  assert.match(vendor, /rule-based draft templates/);
  assert.match(vendor, /Draft only/);
});

// --- T02-T07 additions ---------------------------------------------------------------
import { aiStatusBadge } from '../benefits_leave/frontend/js/components.js';
import { enrollmentHelp, documentStatus, activityPanel, consultationPanel } from '../benefits_leave/frontend/js/workflow-ui.js';

test('AI badge distinguishes unavailable, configured-but-untested and live states', () => {
  assert.match(aiStatusBadge({ ready: false, problems: ['No API key'] }), /AI unavailable/);
  assert.match(aiStatusBadge({ ready: true, model: 'claude-opus-5-5', last_live_result: { status: 'not_run' } }), /not run yet/);
  assert.match(aiStatusBadge({ ready: true, model: 'claude-opus-5-5', last_live_result: { status: 'ok' } }), /Live AI · claude-opus-5-5/);
  assert.match(aiStatusBadge({ ready: true, model: 'm', last_live_result: { status: 'error', detail: 'APITimeoutError' } }), /last call failed/);
  assert.equal(aiStatusBadge(null), '');
});

test('document status keeps received separate from verified', () => {
  const html = documentStatus([{ requirement: 'marriage certificate', dependent: 'Spouse of A', state: 'received', received_on: '2026-10-24', evidence_ref: 'EV-1' }, { requirement: 'birth certificate', dependent: 'Child', state: 'verified', verified_on: '2026-10-12' }]);
  assert.match(html, /Received · awaiting HR check/);
  assert.match(html, /stays on your checklist until HR verifies/);
  assert.match(html, /Verified by HR/);
});

test('enrollment help escapes generated answers and shows the follow-up question and references', () => {
  const payload = '<img src=x onerror=alert(1)>';
  const html = enrollmentHelp({ help_thread: [{ question: payload, answer: payload, follow_up_question: 'When did you send it?', evidence_refs: ['EV-E2001-01'], policy_refs: ['DEMO-ENR-DEPENDENT-PROOF@v1'], facts: ['fact'] }] });
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /Question for you:/);
  assert.match(html, /EV-E2001-01/);
  assert.match(html, /does not change your case/);
});

test('enrollment help shows record facts when AI is unavailable', () => {
  const html = enrollmentHelp({ help_thread: [{ question: 'q', answer: null, ai_error: 'No API key', facts: ['No birth certificate for Child of E is on record.'] }] });
  assert.match(html, /AI answer unavailable/);
  assert.match(html, /No birth certificate/);
});

test('leave draft review allows submission only for a ready draft and only after confirmation', () => {
  const base = { employee: { kind: 'current employee' }, cases: [], leave_types: [{ id: 'own_health', label: 'Own health', required_documents: ['medical certification'] }], leave_schedules: [{ id: 'continuous', label: 'One continuous block' }] };
  const notReady = employeeView({ page: 'leave' }, { ...base, leave_drafts: [{ id: 'D1', status: 'draft', request: { leave_type: 'own_health' }, missing_fields: ['Add the start date'], missing_documents: [], ready_to_confirm: false, clarifications: [{ message: 'Need dates', question: 'When does it start?' }] }] });
  assert.match(notReady, /data-workflow-action="leave-confirm" disabled/);
  assert.match(notReady, /When does it start\?/);
  const ready = employeeView({ page: 'leave' }, { ...base, leave_drafts: [{ id: 'D1', status: 'draft', request: { leave_type: 'own_health', start_date: '2026-11-09', end_date: '2026-11-20', schedule: 'continuous' }, missing_fields: [], missing_documents: ['medical certification'], ready_to_confirm: true, clarifications: [] }] });
  assert.match(ready, /name="confirmed" required/);
  assert.doesNotMatch(ready, /leave-confirm" disabled/);
  assert.match(ready, /HR may ask for them/);
  const newHire = employeeView({ page: 'leave' }, { ...base, employee: { kind: 'new hire' }, leave_drafts: [] });
  assert.match(newHire, /current-employee profile/);
});

test('activity shows actors, references, unknowns and HR-only labels, escaped', () => {
  const html = activityPanel([
    { step: 1, actor: 'vendor_agent', action: 'Asked the Enrollment Agent about the approved medical intent', finding: '<b>x</b>', evidence_refs: ['C1:approved:1'], unknowns: [], next_step: 'Answer', visibility: 'hr' },
    { step: 2, actor: 'enrollment_agent', action: 'Answered the Vendor Agent', finding: 'Employee-only approved', evidence_refs: [], unknowns: ['Carrier status'], next_step: '', visibility: 'hr' },
  ]);
  assert.match(html, /Vendor Agent · HR only/);
  assert.match(html, /activity-item agent consult/);
  assert.match(html, /Unknown: Carrier status/);
  assert.match(html, /C1:approved:1/);
  assert.doesNotMatch(html, /<b>x<\/b>/);
});

test('consultation panel shows the routed question, reply status and snapshot', () => {
  const html = consultationPanel([{ request_id: 'CONSULT-C1-1', benefit: 'medical', question: 'What tier?', approved_snapshot_ref: 'C1:approved:1', model_calls: 2, reply: { status: 'unavailable', finding: null, evidence_refs: [], unknowns: ['budget used'], proposed_next_action: 'HR reviews' } }]);
  assert.match(html, /Vendor Agent → Enrollment Agent/);
  assert.match(html, /Unavailable/);
  assert.match(html, /C1:approved:1/);
  assert.equal(consultationPanel([]), '');
});

test('new mutation endpoints are explicit, labeled mutations', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  const calls = [];
  globalThis.fetch = async (path, options) => { calls.push([path, JSON.parse(options.body)]); return { ok: true, json: async () => ({}) }; };
  await api.enrollmentHelp('E2001', 'q');
  await api.leaveDraft('E1001', { leave_type: 'own_health' });
  await api.confirmLeave('E1001', 'D1');
  await api.aiStatus();
  assert.deepEqual(calls.map(c => c[0]), ['/api/employee/enrollment/help', '/api/employee/leave/draft', '/api/employee/leave/confirm', '/api/ai/status']);
  assert.equal(calls[2][1].confirmed, true);
});

test('HR can verify only a received document on an open case, and the click carries the revision HR saw', () => {
  const evidence = [{ requirement: 'marriage certificate', dependent: 'Spouse', state: 'received', evidence_ref: 'EV-1', received_on: '2026-10-24' },
    { requirement: 'birth certificate', dependent: 'Kid', state: 'verified', evidence_ref: 'EV-2', verified_on: '2026-10-25' },
    { requirement: 'birth certificate', dependent: 'Other', state: 'absent', evidence_ref: null }];
  const open = hrDocuments({ id: 'C2', status: 'incomplete', review_revision: 4, evidence });
  assert.equal((open.match(/data-workflow-action="verify-document"/g) || []).length, 1);
  assert.match(open, /data-evidence-ref="EV-1"/);
  assert.match(open, /data-review-revision="4"/);
  assert.match(open, /Not verified: the item stays open until HR verifies it/);
  assert.doesNotMatch(hrDocuments({ id: 'C2', status: 'approved', evidence }), /verify-document/);
});

test('pending leave documents show received distinct from verified, and only offer valid HR steps', () => {
  const docs = state => [{ document: 'medical certification', state, received_on: '2026-10-26', verified_on: '2026-10-27' }];
  const waiting = pendingDocumentsPanel({ id: 'C5', kind: 'leave', status: 'approved_pending_documents', pending_documents: docs('requested') });
  assert.doesNotMatch(waiting, /value="verify_documents"/);        // nothing received yet: cannot verify
  assert.match(waiting, /value="withdraw_approval"/);
  const received = pendingDocumentsPanel({ id: 'C5', kind: 'leave', status: 'approved_documents_received', pending_documents: docs('received') });
  assert.match(received, /value="verify_documents"/);
  assert.match(received, /HR has not checked it/);
  const done = pendingDocumentsPanel({ id: 'C5', kind: 'leave', status: 'approved', pending_documents: docs('verified') });
  assert.doesNotMatch(done, /<form/);
  assert.match(done, /Verified by HR/);
});

test('employee can mark only requested documents, and correct a request only after HR asks', () => {
  const asking = requestedDocumentsPanel({ id: 'C5', kind: 'leave', status: 'approved_pending_documents',
    pending_documents: [{ document: 'a note', state: 'requested' }, { document: 'a form', state: 'received' }] });
  assert.equal((asking.match(/data-workflow-action="provide-document"/g) || []).length, 1);
  assert.match(asking, /data-document="a note"/);
  assert.doesNotMatch(requestedDocumentsPanel({ id: 'C5', kind: 'leave', status: 'approved_documents_received',
    pending_documents: [{ document: 'a note', state: 'received' }] }), /provide-document/);
  const data = { leave_types: [{ id: 'personal', label: 'Personal', required_documents: [] }, { id: 'own_health', label: 'Own health', required_documents: ['medical certification'] }], leave_schedules: [{ id: 'continuous', label: 'Continuous' }] };
  const item = { id: 'C5', kind: 'leave', status: 'info_requested', employee_update: 'HR needs <b>dates</b>', request: { leave_type: 'own_health', start_date: '2026-11-09', end_date: '2026-11-20', schedule: 'continuous', reason: 'Recovery', documents_attached: ['medical certification'] } };
  const form = leaveResubmitForm(item, data);
  assert.match(form, /id="leave-resubmit-form"/);
  assert.match(form, /value="2026-11-09"/);
  assert.match(form, /<option value="own_health" selected>/);
  assert.doesNotMatch(form, /<b>dates<\/b>/);                       // HR's message is escaped
  assert.equal(leaveResubmitForm({ ...item, status: 'ready_for_hr_review' }, data), '');
});

test('the employee case page offers the correction path that matches the case kind', () => {
  const data = { cases: [{ id: 'C2', kind: 'enrollment', status: 'info_requested', employee_update: 'More please' }], leave_types: [], leave_schedules: [] };
  const html = employeeView({ page: 'cases', caseId: 'C2' }, data);
  assert.match(html, /Update my enrollment/);
  assert.doesNotMatch(html, /leave-resubmit-form/);
});

test('the cost panel shows the vesting rule with its policy source, and nothing when there is none', () => {
  const base = { enrollment: { done: [], missing: [], notes: [] }, selections: [], dependents: [], evidence: [], help_thread: [], plan_options: { plans: { medical: {}, dental: {}, vision: {} } }, cases: [], leave_drafts: [], consider_results: {}, leave_types: [], employee: { id: 'E2002', kind: 'new hire' } };
  const summary = { employee_per_paycheck: 120, employer_per_paycheck: 200, retirement_employee_contribution: '4% of pay', retirement_employer_match: '4% of pay' };
  const withRule = employeeView({ page: 'benefits' }, { ...base, cost_summary: { ...summary, retirement_vesting: { text: 'The match vests over 4 <b>years</b>.', ref: 'DEMO-401K-VESTING@v1' } } });
  assert.match(withRule, /DEMO-401K-VESTING@v1/);
  assert.match(withRule, /The match vests over 4/);
  assert.doesNotMatch(withRule, /<b>years<\/b>/);                         // escaped
  assert.doesNotMatch(employeeView({ page: 'benefits' }, { ...base, cost_summary: { ...summary, retirement_vesting: null } }), /vest/i);
});

test('a conflict response is marked stale so the page reloads the case; a plain rule error is not', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ error: 'This case changed after you opened it.', stale: true }) });
  await assert.rejects(api.decide('C2', 'approve', '', 1), error => error.stale === true && !error.outcomeUnknown);
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ error: 'A reason is required for this decision' }) });
  await assert.rejects(api.decide('C2', 'deny', '', 1), error => error.stale === false);
});
