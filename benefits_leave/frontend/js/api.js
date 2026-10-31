/** Same-origin requests. Mutations are explicit and never automatically retried. */
export class ApiError extends Error {
  constructor(message, outcomeUnknown = false) {
    super(message);
    this.outcomeUnknown = outcomeUnknown;
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
    if (result.error) throw new ApiError(result.error);
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
  overview: employeeId => request('/api/employee/overview', { employee_id: employeeId }),
  queue: () => request('/api/hr/queue'),
  checkEnrollment: employeeId => request('/api/employee/enrollment', { employee_id: employeeId }, { mutation: true }),
  decide: (caseId, decision, reason) => request('/api/hr/decide', { case_id: caseId, decision, reason }, { mutation: true }),
  prepareVendor: caseId => request('/api/hr/vendor/prepare', { case_id: caseId }, { mutation: true }),
  markSent: caseId => request('/api/hr/vendor/sent', { case_id: caseId }, { mutation: true }),
  checkVendor: caseId => request('/api/hr/vendor/check', { case_id: caseId }, { mutation: true }),
};
