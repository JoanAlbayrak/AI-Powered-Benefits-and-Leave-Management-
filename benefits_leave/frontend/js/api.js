/** Same-origin requests. Mutations are explicit and never automatically retried. */
export class ApiError extends Error {
  constructor(message, outcomeUnknown = false, stale = false) {
    super(message);
    this.outcomeUnknown = outcomeUnknown;
    this.stale = stale;   // the case changed under the user: show the latest version
  }
}

export async function request(path, body = {}, { signal, mutation = false, timeoutMs = mutation ? 120000 : 12000 } = {}) {
  const controller = new AbortController();
  const forwardAbort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  else signal?.addEventListener('abort', forwardAbort, { once: true });
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body), signal: controller.signal,
    });
    if (!response.ok) throw new ApiError(mutation ? 'The server could not confirm this action. Refresh its status before trying again.' : 'We couldn’t load this workspace. Please try again.', mutation);
    const result = await response.json();
    // The existing backend returns workflow errors in successful HTTP responses.
    if (result.error) throw new ApiError(result.error, false, Boolean(result.stale));
    return result;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (mutation) throw new ApiError('The action result could not be confirmed. It may still have completed. Refresh the latest status before taking another action.', true);
    if (error.name === 'AbortError') throw new ApiError('The request took too long. Please try again.');
    throw new ApiError('Unable to reach the application. Check that the local server is running.');
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', forwardAbort);
  }
}

export const api = {
  people: () => request('/api/people'),
  aiStatus: () => request('/api/ai/status'),
  overview: employeeId => request('/api/employee/overview', { employee_id: employeeId }),
  queue: () => request('/api/hr/queue'),
  enrollmentHelp: (employeeId, question) => request('/api/employee/enrollment/help', { employee_id: employeeId, question }, { mutation: true }),
  leaveIntake: (employeeId, description) => request('/api/employee/leave/intake', { employee_id: employeeId, description }, { mutation: true }),
  leaveDraft: (employeeId, fields) => request('/api/employee/leave/draft', { employee_id: employeeId, ...fields }, { mutation: true }),
  confirmLeave: (employeeId, draftId) => request('/api/employee/leave/confirm', { employee_id: employeeId, draft_id: draftId, confirmed: true }, { mutation: true }),
  checkEnrollment: employeeId => request('/api/employee/enrollment', { employee_id: employeeId }, { mutation: true }),
  electBenefit: (employeeId, benefit, fields) => request('/api/employee/enrollment/elect', { employee_id: employeeId, benefit, ...fields }, { mutation: true }),
  considerElection: (employeeId, benefit, fields) => request('/api/employee/enrollment/consider', { employee_id: employeeId, benefit, ...fields }, { mutation: true }),
  addDependent: (employeeId, relationship, name) => request('/api/employee/enrollment/dependent/add', { employee_id: employeeId, relationship, name }, { mutation: true }),
  markDocumentUploaded: (employeeId, relationship, name) => request('/api/employee/enrollment/dependent/upload', { employee_id: employeeId, relationship, name }, { mutation: true }),
  decide: (caseId, decision, reason, reviewRevision) => request('/api/hr/decide',
    { case_id: caseId, decision, reason, ...(reviewRevision === undefined || reviewRevision === null ? {} : { review_revision: reviewRevision }) },
    { mutation: true }),
  verifyDocument: (caseId, evidenceRef, reviewRevision) => request('/api/hr/evidence/verify',
    { case_id: caseId, evidence_ref: evidenceRef, ...(reviewRevision === undefined || reviewRevision === null ? {} : { review_revision: reviewRevision }) },
    { mutation: true }),
  resolveLeaveDocuments: (caseId, resolution, reason) => request('/api/hr/leave/resolve', { case_id: caseId, resolution, reason }, { mutation: true }),
  provideLeaveDocument: (employeeId, caseId, document) => request('/api/employee/leave/document', { employee_id: employeeId, case_id: caseId, document }, { mutation: true }),
  resubmitLeave: (employeeId, caseId, fields) => request('/api/employee/leave/resubmit', { employee_id: employeeId, case_id: caseId, ...fields }, { mutation: true }),
  prepareVendor: caseId => request('/api/hr/vendor/prepare', { case_id: caseId }, { mutation: true }),
  markSent: caseId => request('/api/hr/vendor/sent', { case_id: caseId }, { mutation: true }),
  checkVendor: caseId => request('/api/hr/vendor/check', { case_id: caseId }, { mutation: true }),
};
