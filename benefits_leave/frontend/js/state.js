export const navigation = {
  employee: [
    { id: 'overview', label: 'Overview', icon: 'grid' },
    { id: 'benefits', label: 'My benefits', icon: 'shield' },
    { id: 'leave', label: 'Leave requests', icon: 'calendar' },
    { id: 'tasks', label: 'My next steps', icon: 'tasks' },
  ],
  hr: [
    { id: 'queue', label: 'Review queue', icon: 'inbox' },
    { id: 'vendors', label: 'Vendor follow-ups', icon: 'building' },
    { id: 'tasks', label: 'Next steps', icon: 'tasks' },
    { id: 'history', label: 'Case history', icon: 'history' },
  ],
};

export function routeFromHash(hash) {
  const parts = hash.replace(/^#\/?/, '').split('/');
  const role = parts[0] === 'hr' ? 'hr' : 'employee';
  const page = parts[1] || navigation[role][0].id;
  const isCase = page === 'cases' && Boolean(parts[2]);
  if (!isCase && !navigation[role].some(item => item.id === page)) return { role, page: 'not-found', caseId: null };
  return { role, page, caseId: isCase ? parts[2] : null };
}

export function readEmployeePreference() {
  try { return localStorage.getItem('benefits-leave-demo-employee') || 'E2001'; }
  catch { return 'E2001'; }
}
export function saveEmployeePreference(value) {
  try { localStorage.setItem('benefits-leave-demo-employee', value); } catch { /* Optional preference only. */ }
}
