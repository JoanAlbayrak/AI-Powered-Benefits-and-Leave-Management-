import { icon, escape, label, coverageTier, badge, statusBadge, buttonLink, emptyState, notice, panel, pageHeader, agentInfo, caseName } from '../components.js';
import { decisionPanel, vendorActions, vendorDrafts } from '../workflow-ui.js';
const nameFor = (data, id) => data.people.find(person => person.id === id)?.name || id;
const summaryFor = item => item.vendor?.ai?.hr_summary || item.ai?.hr_summary;
const nextAction = item => ({ incomplete: 'Review missing information', ready_for_hr_review: 'Review case', approved: 'Prepare vendor records', vendor_records_ready: 'Confirm HR transmission', sent_to_vendors: 'Check vendor confirmations', vendor_follow_up: 'Review vendor follow-ups', vendor_confirmed: 'No open vendor action', info_requested: 'Await employee information', denied: 'Review recorded decision' }[item.status] || 'Review case');

function caseRows(data, cases) {
  return cases.map(item => `<tr data-case-row data-search="${escape(`${item.id} ${nameFor(data, item.employee_id)} ${item.employee_id} ${caseName(item)}`.toLowerCase())}" data-status="${escape(item.status)}"><td data-label="Case"><div><a href="#/hr/cases/${encodeURIComponent(item.id)}"><b>${escape(item.id)}</b></a><small>${escape(caseName(item))}</small></div></td><td data-label="Employee"><div><b>${escape(nameFor(data, item.employee_id))}</b><small>${escape(item.employee_id)}</small></div></td><td data-label="Status">${statusBadge(item.status)}</td><td data-label="Next action"><span>${escape(nextAction(item))}</span></td><td data-label="Open">${buttonLink('View case', `#/hr/cases/${encodeURIComponent(item.id)}`, { symbol: 'arrow' })}</td></tr>`).join('');
}

function queue(data) {
  const cases = data.cases;
  return pageHeader('HR review queue', 'Review the facts, understand outstanding items, and find the next step.', 'HR workspace')
    + `<section class="panel"><div class="toolbar"><div class="filter-group" role="group" aria-label="Filter cases"><button data-filter="all" aria-pressed="true">All cases · ${cases.length}</button><button data-filter="review" aria-pressed="false">Needs review</button><button data-filter="vendor" aria-pressed="false">With vendors</button></div><div class="search-field">${icon('search')}<label class="skip-link" for="case-search">Search cases</label><input id="case-search" type="search" placeholder="Search name or case ID" autocomplete="off"></div></div>${cases.length ? `<div class="table-wrap responsive-table"><table><thead><tr><th>Case</th><th>Employee</th><th>Status</th><th>Next action</th><th>Action</th></tr></thead><tbody>${caseRows(data, cases)}</tbody></table></div><div id="no-filter-results" hidden>${emptyState('No matching cases', 'Try another name or filter.', 'search')}</div>` : emptyState('No cases in the queue', 'Cases appear here after an employee starts the existing workflow.', 'inbox')}</section>`
    + `<div class="spaced">${notice('Open a case to review its facts and record the next allowed HR action. Decisions and vendor records use the existing workflow guards.')}</div>`;
}

function vendors(data) {
  const cases = data.cases.filter(item => item.kind === 'enrollment' && ['approved', 'vendor_records_ready', 'sent_to_vendors', 'vendor_follow_up', 'vendor_confirmed'].includes(item.status));
  return pageHeader('Vendor follow-ups', 'Follow approved elections from the HR handoff to carrier confirmation.', 'HR workspace')
    + notice('Prepared records, HR transmission status, and confirmed carrier coverage are separate steps. Opening this page does not run a vendor check.')
    + `<div class="spaced">${cases.length ? cases.map(item => panel(`${item.id} · ${nameFor(data, item.employee_id)}`, `<div class="panel-body"><div class="actions">${statusBadge(item.status)}</div><p class="spaced">${escape(nextAction(item))}.</p><p class="inline-note">Approved handoff: ${item.handoff?.records?.length || 0} benefit records. Read only: no transmission or agent generation is triggered here.</p><div class="actions spaced">${buttonLink('Inspect approved records', `#/hr/cases/${encodeURIComponent(item.id)}`, { primary: true, symbol: 'arrow' })}</div></div>`)).join('') : panel('Vendor cases', emptyState('No approved vendor cases yet', 'Vendor preparation becomes available after HR approval.', 'building'))}</div>`
    + agentInfo('Vendor Agent', 'Open a case and choose Check confirmations to run the comparison and explanation. Follow-up messages remain drafts for HR.');
}

function tasks(data) {
  const open = data.cases.filter(item => !['denied', 'vendor_confirmed'].includes(item.status));
  return pageHeader('Next steps', 'See the next workflow action for existing cases.', 'HR workspace')
    + notice('These next steps are derived from case status. Persistent owners, due dates, and completion evidence will be added with the shared action tracker.')
    + `<div class="spaced">${panel('Case actions', open.length ? open.map(item => `<div class="list-row"><div class="row-content">${icon('tasks')}<div><b>${escape(nextAction(item))}</b><p>${escape(item.id)} · ${escape(nameFor(data, item.employee_id))} · Ownership not assigned in this phase</p></div></div>${buttonLink('View case', `#/hr/cases/${encodeURIComponent(item.id)}`)}</div>`).join('') : emptyState('No next steps to show', 'Open cases will appear here as the workflow progresses.', 'check'))}</div>`;
}

function history(data) {
  const events = data.cases.flatMap(item => (item.history || []).map((event, index) => ({ caseId: item.id, event, index })));
  return pageHeader('Case history', 'Recorded workflow events from the current in-memory case store.', 'HR workspace')
    + panel('Recorded events', events.length ? `<div class="timeline">${events.map(item => `<div class="timeline-item"><small><a href="#/hr/cases/${encodeURIComponent(item.caseId)}">${escape(item.caseId)}</a> · Event ${item.index + 1}</small><p>${escape(item.event)}</p></div>`).join('')}</div>` : emptyState('No events recorded', 'History appears as the existing workflow runs.', 'history'))
    + `<p class="inline-note">Events are displayed in recorded order within each case. The current store does not attach timestamps or persist history after a server restart.</p>`;
}

function caseDetail(data, caseId) {
  const item = data.cases.find(value => value.id === caseId);
  const back = `<a class="back-link" href="#/hr/queue">${icon('back')}Back to review queue</a>`;
  if (!item) return back + pageHeader('Case not found', 'This case is not in the current store.') + notice('Refresh the queue and select an existing case.', 'warning');
  const check = item.kind === 'leave' ? item.check : item.enrollment;
  const missing = item.kind === 'leave' ? [...(check?.missing_fields || []), ...(check?.missing_documents || [])] : check?.missing || [];
  const flags = check?.hr_flags || [];
  let html = back + pageHeader(`${item.id} · ${caseName(item)}`, `${nameFor(data, item.employee_id)} · ${item.employee_id}`, 'HR case review');
  html += panel('Case overview', `<div class="panel-body"><div class="actions">${statusBadge(item.status)}</div><dl class="definition spaced"><div><dt>Employee</dt><dd>${escape(nameFor(data, item.employee_id))}</dd></div><div><dt>Next action</dt><dd>${escape(nextAction(item))}</dd></div><div><dt>Assigned owner</dt><dd>Not assigned in this phase</dd></div></dl></div>`);
  const trusted = check ? `<div class="panel-body">${check.done?.length ? `<h3>Recorded items</h3>${check.done.map(text => `<p class="inline-note">${icon('check')} ${escape(text)}</p>`).join('')}` : ''}${missing.length ? `<h3 class="spaced">Missing information</h3>${missing.map(text => `<p class="inline-note">${escape(text)}</p>`).join('')}` : `<p>${check.complete === false ? 'Incomplete check; inspect required information.' : 'No missing items recorded in this snapshot.'}</p>`}${flags.length ? `<h3 class="spaced">HR-only review flags</h3>${flags.map(text => `<p class="inline-note">${escape(text)}</p>`).join('')}` : ''}${check.fmla_precheck ? `<h3 class="spaced">FMLA pre-check</h3><p class="inline-note">${escape(label(check.fmla_precheck.status))}. This is a pre-check, not a decision.</p>` : ''}</div>` : emptyState('No check recorded', 'Check results will appear after the relevant workflow step.', 'info');
  html += `<div class="two-col spaced"><div>${panel('Trusted check results', trusted)}${panel('Agent summary', summaryFor(item) ? `<div class="panel-body"><p class="generated-text">${escape(summaryFor(item))}</p></div>` : emptyState('No generated summary stored', 'The check results remain available when AI is unavailable.', 'bot'))}${item.ai_error ? `<div class="spaced">${notice(`Enrollment Agent unavailable: ${item.ai_error}`, 'warning')}</div>` : ''}</div>${decisionPanel(item)}</div>`;
  html += vendorActions(item);
  if (item.handoff?.records?.length) html += `<div class="spaced">${panel('Frozen approved handoff', `<div class="table-wrap responsive-table"><table><thead><tr><th>Benefit</th><th>Vendor</th><th>Approved record</th></tr></thead><tbody>${item.handoff.records.map(record => `<tr><td data-label="Benefit">${escape(label(record.benefit))}</td><td data-label="Vendor">${escape(record.vendor)}</td><td data-label="Approved record">${escape(record.plan || `${record.contribution_percent}% contribution`)}${record.tier ? ` · ${escape(coverageTier(record.tier))}` : ''}</td></tr>`).join('')}</tbody></table></div>`, 'Exactly the snapshot HR approved; no carrier match is inferred.')}</div>`;
  if (item.vendor?.reconciliation?.length) html += `<div class="spaced">${panel('Stored vendor results', item.vendor.reconciliation.map(result => `<div class="list-row"><div><b>${escape(result.vendor)}</b><p>${escape(result.detail || 'Recorded comparison result')}</p></div>${badge(label(result.result), result.result === 'confirmed' ? 'success' : 'warning')}</div>`).join(''))}</div>`;
  html += vendorDrafts(item);
  if (item.history?.length) html += `<div class="spaced">${panel('Recorded history', `<div class="timeline">${item.history.map((event, index) => `<div class="timeline-item"><small>Event ${index + 1}</small><p>${escape(event)}</p></div>`).join('')}</div>`)}</div>`;
  return html;
}

export function hrView(route, data) {
  if (route.page === 'cases') return caseDetail(data, route.caseId);
  return ({ queue, vendors, tasks, history }[route.page] || (() => pageHeader('Page not found', 'Choose a destination from the navigation.')))(data);
}
