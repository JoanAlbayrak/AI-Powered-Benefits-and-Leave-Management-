/** The only network boundary for the new interface. Mutations stay disconnected. */
export class ApiError extends Error {}

export async function request(path, body = {}, { signal } = {}) {
  const controller = new AbortController();
  const forwardAbort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  else signal?.addEventListener('abort', forwardAbort, { once: true });
  const timer = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body), signal: controller.signal,
    });
    if (!response.ok) throw new ApiError('We couldn’t load this workspace. Please try again.');
    const result = await response.json();
    // The existing backend returns workflow errors in successful HTTP responses.
    if (result.error) throw new ApiError(result.error);
    return result;
  } catch (error) {
    if (error instanceof ApiError) throw error;
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
};
