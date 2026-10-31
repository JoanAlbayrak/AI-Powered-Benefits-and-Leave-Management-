import test from 'node:test';
import assert from 'node:assert/strict';
import { request, ApiError, api } from '../benefits_leave/frontend/js/api.js';
import { WorkflowController } from '../benefits_leave/frontend/js/workflows.js';
import { routeFromHash } from '../benefits_leave/frontend/js/state.js';
import { escape, statusBadge } from '../benefits_leave/frontend/js/components.js';
import { employeeView } from '../benefits_leave/frontend/js/views/employee.js';
import { hrView } from '../benefits_leave/frontend/js/views/hr.js';

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
