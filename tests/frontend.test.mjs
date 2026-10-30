import test from 'node:test';
import assert from 'node:assert/strict';
import { request, ApiError } from '../benefits_leave/frontend/js/api.js';
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
