const paths = {
  check: '<path d="m5 12 4 4L19 6"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  shield: '<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6z"/><path d="m8 12 3 3 5-6"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18M8 15h2M14 15h2"/>',
  tasks: '<rect x="5" y="4" width="15" height="17" rx="2"/><path d="M9 4V2h7v4H9M9 11h7M9 16h7"/>',
  inbox: '<path d="m3 10 3-6h12l3 6v10H3zM3 13h5l2 3h4l2-3h5"/>',
  building: '<rect x="5" y="3" width="14" height="18" rx="1"/><path d="M9 7h1M14 7h1M9 11h1M14 11h1M10 21v-5h4v5"/>',
  history: '<path d="M3 10a9 9 0 1 1 1 7M3 4v6h6M12 7v6l4 2"/>',
  arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  back: '<path d="M20 12H4m6-6-6 6 6 6"/>',
  external: '<path d="M14 3h7v7M21 3 11 13M10 4H4v16h16v-6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  warning: '<path d="m12 3 10 18H2zM12 9v5M12 17h.01"/>',
  heart: '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  savings: '<path d="M3 10c0-5 15-7 17 0l2 2-2 2-1 5h-3v-2H8v2H5l-1-5-2-1M8 5V2l5 2M9 8h5"/><circle cx="17" cy="10" r=".5"/>',
  bot: '<rect x="4" y="6" width="16" height="14" rx="4"/><path d="M12 2v4M1 11v5M23 11v5M8 11h.01M16 11h.01M9 16h6"/>',
  search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
  refresh: '<path d="M20 7a8 8 0 0 0-14-2L3 8m0-5v5h5M4 17a8 8 0 0 0 14 2l3-3m0 5v-5h-5"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  minus: '<path d="M5 12h14"/>',
  document: '<path d="M14 2H5v20h14V7zM14 2v5h5M8 12h8M8 16h6"/>',
};
export const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.info}</svg>`;
export const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const label = value => String(value || '').replaceAll('_', ' ').replace(/^./, c => c.toUpperCase());
export const coverageTier = value => ({ employee: 'Employee only', employee_spouse: 'Employee + spouse', employee_children: 'Employee + children', family: 'Family' }[value] || label(value));
export function formatDate(value) {
  if (!value) return 'Not recorded';
  const date = new Date(`${value}T12:00:00Z`);
  return Number.isNaN(date.getTime()) ? 'Not recorded' : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
}
export const money = value => typeof value === 'number' ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value) : 'Not available';
export const badge = (text, tone = 'neutral', symbol = null) => `<span class="pill ${escape(tone)}">${symbol ? icon(symbol) : ''}${escape(text)}</span>`;
const statuses = {
  incomplete: ['Information needed', 'warning', 'clock'], ready_for_hr_review: ['Ready for HR review', '', 'clock'],
  approved: ['Approved by HR', 'success', 'check'], denied: ['Not approved', 'danger', 'warning'],
  info_requested: ['More information requested', 'warning', 'info'], vendor_records_ready: ['Vendor records prepared', '', 'document'],
  sent_to_vendors: ['Marked sent to vendors', '', 'external'], vendor_follow_up: ['Vendor follow-up needed', 'warning', 'clock'],
  vendor_confirmed: ['Vendor confirmed', 'success', 'check'],
};
export const statusBadge = status => badge(...(statuses[status] || [label(status), 'neutral']));
export const buttonLink = (text, href, { primary = false, symbol = null } = {}) => `<a class="btn ${primary ? 'primary' : ''}" href="${escape(href)}">${escape(text)}${symbol ? icon(symbol) : ''}</a>`;
export const emptyState = (title, description, symbol = 'inbox', action = '') => `<div class="empty">${icon(symbol)}<h3>${escape(title)}</h3><p>${escape(description)}</p>${action ? `<div class="actions">${action}</div>` : ''}</div>`;
export const notice = (text, tone = '') => `<div class="notice ${tone}" role="note">${icon(tone === 'error' ? 'warning' : 'info')}<span>${escape(text)}</span></div>`;
export const panel = (title, body, subtitle = '', action = '') => `<section class="panel"><div class="panel-heading"><div><h2>${escape(title)}</h2>${subtitle ? `<p>${escape(subtitle)}</p>` : ''}</div>${action}</div>${body}</section>`;
export const pageHeader = (title, description, eyebrow = '', meta = '') => `<header class="page-header"><div>${eyebrow ? `<div class="eyebrow">${escape(eyebrow)}</div>` : ''}<h1>${escape(title)}</h1><p>${escape(description)}</p></div>${meta ? `<div class="page-meta">${icon('calendar')}${escape(meta)}</div>` : ''}</header>`;
export const agentInfo = (name, description) => `<details class="agent-info"><summary>${icon('bot')}How the ${escape(name)} helps</summary><p>${escape(description)}<br><strong>Computer checks. AI explains. HR decides.</strong> Opening a page does not run an agent. Connected actions are labeled explicitly.</p></details>`;
export const stageNote = text => notice(text || 'Interface foundation: this action will be connected in the core-workflow phase. No changes are submitted from this screen.');
export const disabledAction = text => `<button class="btn primary" disabled aria-describedby="connection-note">${escape(text)}</button><span id="connection-note">Workflow connection comes next.</span>`;
export const caseName = item => item.kind === 'leave' ? item.leave_type || item.check?.leave_type_label || 'Leave request' : 'Benefits enrollment';
export const loadingView = () => `<div role="status" aria-label="Loading workspace"><div class="loading-label">Loading your workspace…</div><div class="skeleton large"></div><div class="skeleton"></div><section class="panel spaced"><div class="panel-body"><div class="skeleton"></div><div class="skeleton" style="width:85%"></div><div class="skeleton" style="width:50%"></div></div></section></div>`;
