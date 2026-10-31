import { icon, escape, label, coverageTier, formatDate, money, badge, statusBadge, buttonLink, emptyState, notice, panel, pageHeader, agentInfo, stageNote, disabledAction, caseName } from '../components.js';
import { enrollmentActions, enrollmentGuidance } from '../workflow-ui.js';
const selections = data => data.selections || [];
const benefitIcon = benefit => ({ medical: 'heart', dental: 'shield', vision: 'eye', retirement: 'savings' }[benefit] || 'shield');

function selectionCards(data) {
  return `<div class="selection-grid">${selections(data).map(item => {
    const elected = item.status === 'elected';
    const value = item.benefit === 'retirement' ? item.percent == null ? 'No election yet' : `${item.percent}% contribution` : item.plan || (item.status === 'waived' ? 'Coverage waived' : 'No election yet');
    const detail = item.benefit === 'retirement' ? 'Employee-selected amount' : elected ? `${coverageTier(item.tier)} · ${money(item.cost_per_paycheck)} / paycheck` : item.status === 'waived' ? 'Waiver recorded' : 'A choice is still needed';
    return `<article class="selection-card"><div class="selection-icon">${icon(benefitIcon(item.benefit))}</div><h3>${escape(label(item.benefit))}</h3><b>${escape(value)}</b><p>${escape(detail)}</p>${badge(elected ? 'Election recorded' : item.status === 'waived' ? 'Waived' : 'Not selected', elected ? '' : item.status === 'waived' ? 'neutral' : 'warning')}</article>`;
  }).join('')}</div>`;
}

function enrollmentProgress(data) {
  const selected = selections(data).filter(item => item.status !== 'not_started').length;
  const total = selections(data).length;
  return `<div class="mini-heading"><b>Election checklist</b><span>${selected} of ${total} recorded</span></div><div class="progress" role="progressbar" aria-label="Elections recorded" aria-valuenow="${selected}" aria-valuemin="0" aria-valuemax="${total}"><i style="width:${total ? selected / total * 100 : 0}%"></i></div>${selections(data).map(item => `<div class="mini-item"><span class="${item.status === 'not_started' ? 'text-warning' : 'text-success'}">${icon(item.status === 'not_started' ? 'clock' : 'check')}${escape(label(item.benefit))}</span><small>${item.status === 'not_started' ? 'Not started' : item.status === 'waived' ? 'Waived' : 'Recorded'}</small></div>`).join('')}<div class="source-note">Recorded choices do not establish evidence verification, HR approval, or active coverage.</div>`;
}

function requests(data) {
  if (!data.cases.length) return emptyState('No requests to follow yet', 'Your enrollment and leave cases will appear here after they are created through the workflow.', 'inbox');
  return data.cases.map(item => `<div class="list-row"><div class="row-content">${icon(item.kind === 'leave' ? 'calendar' : 'shield')}<div><a href="#/employee/cases/${encodeURIComponent(item.id)}"><b>${escape(caseName(item))}</b></a><p>${escape(item.id)}${item.employee_update ? ` · ${escape(item.employee_update)}` : ''}</p></div></div>${statusBadge(item.status)}</div>`).join('');
}

function overview(data) {
  const e = data.enrollment;
  let focus;
  if (e) {
    const missing = e.missing.length;
    focus = `<section class="panel focus-panel"><div class="focus-main"><div class="actions">${badge(missing ? 'Your next step' : 'Ready for the next check', missing ? 'warning' : '', missing ? 'clock' : 'check')}${badge(`Deadline ${formatDate(e.deadline)}`, 'neutral')}</div><h2>${missing ? 'A few details still need your attention.' : 'Your enrollment choices are recorded.'}</h2><p>${missing ? `${missing} outstanding ${missing === 1 ? 'item needs' : 'items need'} attention before enrollment is complete. Review the checklist to see exactly what is missing.` : 'You have recorded your benefit elections. HR review and vendor confirmation are separate steps.'}</p><div class="actions">${buttonLink('Review enrollment', '#/employee/benefits', { primary: true, symbol: 'arrow' })}</div></div><aside class="focus-aside">${enrollmentProgress(data)}</aside></section>`;
  } else {
    focus = panel('Need time away from work?', `<div class="panel-body"><p>Start with a clear request. The leave workflow organizes your information so HR can review it.</p><div class="actions spaced">${buttonLink('Explore the leave request form', '#/employee/leave', { primary: true, symbol: 'arrow' })}</div></div>`);
  }
  return pageHeader('Your benefits and requests', 'A clear view of your information, outstanding items, and the next step.', 'Employee workspace', `Demo records · ${formatDate(data.as_of)}`)
    + focus
    + (e ? `<div class="section-label"><h2>Your benefit elections</h2><a href="#/employee/benefits">View details ${icon('arrow')}</a></div>${selectionCards(data)}` : '')
    + `<div class="spaced">${panel('Your requests', requests(data), 'Updates from the existing case store.')}</div>`
    + agentInfo(e ? 'Enrollment Agent' : 'Leave Agent', e ? 'It will explain your enrollment checklist and prepare a summary for HR. It does not choose a plan or contribution for you.' : 'It will explain what your request still needs and prepare a summary for HR. HR makes the decision.');
}

function benefits(data) {
  let content = pageHeader('My benefits', 'Review the choices on your record and what still needs attention.', 'Employee workspace', `Snapshot · ${formatDate(data.as_of)}`);
  if (!data.enrollment) return content + panel('No new-hire enrollment record', emptyState('Choose a new-hire demo profile', 'This profile is a current employee. The available enrollment examples belong to E2001–E2004.', 'shield'));
  const e = data.enrollment;
  content += notice(`Enrollment deadline: ${formatDate(e.deadline)}. ${e.days_left < 0 ? `${Math.abs(e.days_left)} days past the deadline` : `${e.days_left} days remaining`} as of the demo record date ${formatDate(e.as_of)}.`, e.days_left < 0 || e.days_left <= 7 ? 'warning' : '');
  content += `<div class="spaced">${selectionCards(data)}</div><div class="two-col spaced">`;
  content += panel('Still to do', e.missing.length ? e.missing.map(text => `<div class="list-row"><div class="row-content">${icon('clock')}<div><b>${escape(text)}</b><p>From the enrollment completeness check.</p></div></div>${badge('Action needed', 'warning')}</div>`).join('') : emptyState('No missing items in this snapshot', 'HR may still need to review eligibility or exceptions. This is not an approval.', 'check'));
  content += panel('Retirement match', `<div class="panel-body"><p>${escape(data.retirement_match)}.</p><p class="inline-note">This explains the demo plan rule. Your contribution is your choice.</p>${e.notes.length ? `<div class="spaced">${e.notes.map(note => `<p class="inline-note">${escape(note)}</p>`).join('')}</div>` : ''}</div>`);
  content += `</div><div class="spaced">${enrollmentActions(data)}</div>`;
  const item = data.cases.find(value => value.kind === 'enrollment');
  if (item) content += `<div class="spaced">${enrollmentGuidance(item)}</div>`;
  return content + `<div class="spaced">${stageNote('Election editing, waivers and document handling remain previews. The check uses the choices already recorded in this fictional profile.')}</div>`;
}

function leave(data) {
  return pageHeader('Leave requests', 'Prepare the information HR needs to review your time away.', 'Employee workspace')
    + stageNote('The request form is a layout preview. Submission, saving, and document handling will be connected in the next phase; nothing entered here is saved.')
    + `<div class="two-col spaced"><section class="panel"><div class="panel-heading"><div><h2>Request a leave of absence</h2><p>Share only the information needed for review.</p></div>${badge('Form preview', 'neutral')}</div><div class="steps"><span class="current"><i>1</i>Request details</span><span><i>2</i>Supporting information</span><span><i>3</i>Review</span></div><form id="leave-preview"><div class="panel-body"><div class="form-field"><label for="leave-type">Leave type</label><select id="leave-type"><option value="">Choose a leave type</option>${data.leave_types.map(type => `<option value="${escape(type.id)}">${escape(type.label)}</option>`).join('')}</select></div><div class="form-grid"><div class="form-field"><label for="start-date">Start date</label><input id="start-date" type="date"></div><div class="form-field"><label for="end-date">End date</label><input id="end-date" type="date"></div></div><div class="form-field"><label for="leave-note">Anything HR should know <span style="font-weight:400">(optional)</span></label><textarea id="leave-note" placeholder="Add helpful context. No medical details are needed."></textarea><p class="inline-note">Preview only. These details are not submitted or stored.</p></div></div><div class="form-actions">${disabledAction('Continue to supporting information')}</div></form></section>${panel('What happens next', `<div class="panel-body"><div class="timeline"><div class="timeline-item"><small>1 · Employee</small><p>Provide your dates and supporting information.</p></div><div class="timeline-item"><small>2 · Code and Leave Agent</small><p>Check completeness and explain missing information.</p></div><div class="timeline-item"><small>3 · HR</small><p>Review the evidence and make a decision.</p></div></div></div>`, 'A pre-check is not a leave decision.')}</div><div class="spaced">${panel('Your existing requests', requests({ ...data, cases: data.cases.filter(item => item.kind === 'leave') }))}</div>`
    + agentInfo('Leave Agent', 'It will explain missing fields and required documents. An unavailable lookup remains unknown rather than becoming a denial.');
}

function tasks(data) {
  const missing = data.enrollment?.missing || [];
  return pageHeader('My next steps', 'A checklist of outstanding items from your current enrollment snapshot.', 'Employee workspace')
    + notice('This checklist comes from existing checks. Persistent task assignment, document verification, and reminders are planned for the action-tracker phase.')
    + `<div class="spaced">${panel('Outstanding enrollment items', missing.length ? missing.map(text => `<div class="list-row"><div class="row-content">${icon('document')}<div><b>${escape(text)}</b><p>Responsible: employee · Enrollment deadline: ${formatDate(data.enrollment.deadline)}</p></div></div>${buttonLink('View', '#/employee/benefits')}</div>`).join('') : emptyState('No outstanding enrollment items', 'This does not establish HR approval or vendor confirmation. Check your requests for case updates.', 'check'))}</div>`;
}

function caseDetail(data, caseId) {
  const item = data.cases.find(value => value.id === caseId);
  const back = `<a class="back-link" href="#/employee/overview">${icon('back')}Back to overview</a>`;
  if (!item) return back + pageHeader('Request not found', 'This case is not available in the selected employee’s workspace.') + notice('Choose a request from your own overview.', 'warning');
  return back + pageHeader(caseName(item), 'Your request status and the latest employee-visible update.', item.id)
    + panel('Request status', `<div class="panel-body">${statusBadge(item.status)}<p class="spaced">${escape(item.employee_update || 'There is no employee update recorded yet.')}</p>${item.dates ? `<dl class="definition spaced"><div><dt>Start date</dt><dd>${formatDate(item.dates[0])}</dd></div><div><dt>End date</dt><dd>${formatDate(item.dates[1])}</dd></div></dl>` : ''}</div>`)
    + (item.kind === 'enrollment' ? `<div class="spaced">${enrollmentGuidance(item)}</div>` : '')
    + `<div class="spaced">${stageNote('Correction and resubmission controls will be added with the core workflow. Internal HR notes are not included in this employee view.')}</div>`;
}

export function employeeView(route, data) {
  if (route.page === 'cases') return caseDetail(data, route.caseId);
  return ({ overview, benefits, leave, tasks }[route.page] || (() => pageHeader('Page not found', 'Choose a destination from the navigation.')))(data);
}
