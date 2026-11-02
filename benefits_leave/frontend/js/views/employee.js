import { icon, escape, label, coverageTier, formatDate, money, badge, statusBadge, buttonLink, emptyState, notice, panel, pageHeader, agentInfo, stageNote, disabledAction, caseName } from '../components.js';
import { enrollmentActions, enrollmentGuidance, documentStatus, enrollmentHelp, refChips, activityPanel, requestedDocumentsPanel, leaveResubmitForm } from '../workflow-ui.js';
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

function costSummaryPanel(data) {
  const c = data.cost_summary;
  if (!c || (!c.employee_per_paycheck && !c.employer_per_paycheck && !c.retirement_employee_contribution)) return '';
  return panel('Your cost per paycheck', `<div class="panel-body"><dl class="definition"><div><dt>You pay</dt><dd>${money(c.employee_per_paycheck)}</dd></div><div><dt>Company pays</dt><dd>${money(c.employer_per_paycheck)}</dd></div>${c.retirement_employee_contribution ? `<div><dt>Your 401(k) contribution</dt><dd>${escape(c.retirement_employee_contribution)}</dd></div><div><dt>Employer match</dt><dd>${escape(c.retirement_employer_match)}</dd></div>` : ''}</dl>${c.retirement_vesting ? `<p class="inline-note">${escape(c.retirement_vesting.text)} <span class="ref-chip">${escape(c.retirement_vesting.ref)}</span></p>` : ''}<p class="inline-note">Medical, dental and vision only. Figures from currently elected plans.</p></div>`, 'What you and the company each pay for your current elections.');
}

function planTierOptions(benefit, data, current) {
  const plans = data.plan_options?.plans?.[benefit] || {};
  const tiers = ['employee', 'employee_spouse', 'employee_children', 'family'];
  const opts = [];
  for (const [planName, planInfo] of Object.entries(plans)) {
    for (const tier of tiers) {
      if (planInfo[tier] == null) continue;
      const value = `${planName}|${tier}`;
      const selected = current.status === 'elected' && current.plan === planName && current.tier === tier;
      opts.push(`<option value="${escape(value)}" ${selected ? 'selected' : ''}>${escape(planName)} — ${escape(coverageTier(tier))} — ${escape(money(planInfo[tier]))}/paycheck</option>`);
    }
  }
  return opts.join('');
}

function considerBlock(considered, agentName = 'Enrollment Agent') {
  if (!considered) return '';
  const refs = [...(considered.evidence_refs || []), ...(considered.policy_refs || [])];
  return `<div class="help-answer"><small>${icon('bot')}${escape(agentName)}</small>${considered.explanation ? `<p class="generated-text">${escape(considered.explanation)}</p>` : notice(`AI explanation unavailable: ${considered.ai_error || 'no answer'}`, 'warning')}${refChips(refs)}</div>`;
}

function electionForm(benefit, data) {
  const current = selections(data).find(item => item.benefit === benefit) || { status: 'not_started' };
  const isRetirement = benefit === 'retirement';
  const statusOptions = isRetirement
    ? `<option value="not_started" ${current.status === 'not_started' ? 'selected' : ''}>Not chosen</option><option value="elected" ${current.status === 'elected' ? 'selected' : ''}>Contribute</option>`
    : `<option value="not_started" ${current.status === 'not_started' ? 'selected' : ''}>Not chosen</option><option value="elected" ${current.status === 'elected' ? 'selected' : ''}>Elect coverage</option><option value="waived" ${current.status === 'waived' ? 'selected' : ''}>Waive coverage</option>`;
  const choiceField = isRetirement
    ? `<div class="form-field"><label for="retire-percent">Contribution</label><select id="retire-percent" name="percent">${(data.plan_options?.retirement_plan?.contribution_options_percent || []).map(p => `<option value="${p}" ${current.percent === p ? 'selected' : ''}>${p}%</option>`).join('')}</select></div><p class="inline-note">${escape(data.plan_options?.retirement_plan?.vesting_schedule?.note || '')}</p>`
    : `<div class="form-field"><label for="plantier-${escape(benefit)}">Plan and coverage tier</label><select id="plantier-${escape(benefit)}" name="plan_tier">${planTierOptions(benefit, data, current)}</select></div>`;
  return `<form id="election-form-${escape(benefit)}" class="election-form workflow-form" data-benefit="${escape(benefit)}"><div class="panel-body"><div class="form-field"><label for="status-${escape(benefit)}">${escape(label(benefit))}</label><select id="status-${escape(benefit)}" name="status">${statusOptions}</select></div>${choiceField}${considerBlock(data.consider_results?.[benefit])}</div><div class="form-actions"><button class="btn" type="submit" data-intent="consider" data-workflow-action="enrollment-election">${icon('bot')}Check with the Enrollment Agent</button><button class="btn primary" type="submit" data-intent="save" data-workflow-action="enrollment-election">Save election</button></div></form>`;
}

function electionCards(data) {
  const benefits = [...data.plan_options?.plans ? Object.keys(data.plan_options.plans) : [], 'retirement'];
  return `<div class="two-col spaced">${benefits.map(benefit => panel(label(benefit), electionForm(benefit, data))).join('')}</div>`;
}

function dependentsPanel(data) {
  const deps = data.dependents || [];
  const rows = deps.length ? deps.map(d => {
    const tone = d.document_state === 'verified' ? 'success' : d.document_state === 'received' ? 'warning' : 'neutral';
    const label2 = d.document_state === 'verified' ? 'Verified by HR' : d.document_state === 'received' ? 'Received — awaiting HR check' : 'Not on file';
    return `<div class="list-row"><div><b>${escape(d.name)}</b><p>${escape(label(d.relationship))} · ${escape(d.requirement)}</p></div>${badge(label2, tone)}${d.document_state === 'absent' ? `<button class="btn small" type="button" data-mark-uploaded data-workflow-action="dependent-upload" data-relationship="${escape(d.relationship)}" data-name="${escape(d.name)}">Mark as uploaded</button>` : ''}</div>`;
  }).join('') : emptyState('No dependents on record', 'Add a spouse or child if you plan to cover them.', 'inbox');
  const addForm = `<form id="dependent-add-form" class="workflow-form"><div class="panel-body"><div class="form-grid"><div class="form-field"><label for="dependent-relationship">Relationship</label><select id="dependent-relationship" name="relationship"><option value="spouse">Spouse</option><option value="child">Child</option></select></div><div class="form-field"><label for="dependent-name">Name</label><input id="dependent-name" name="name" type="text" maxlength="80" placeholder="Full name" required></div></div></div><div class="form-actions"><button class="btn" type="submit" data-workflow-action="dependent-add">Add dependent</button></div></form>`;
  return panel('Your dependents', `${rows}${addForm}`, 'A dependent-covering tier (employee + spouse, + children, or family) needs proof for each dependent. Demo labels only: no file is uploaded.');
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
  content += `<div class="spaced">${selectionCards(data)}</div>`;
  content += `<div class="spaced">${costSummaryPanel(data)}</div>`;
  content += data.enrollment_locked
    ? notice('Your enrollment was already decided by HR. Contact HR to request a change.', '')
    : `<div class="spaced">${electionCards(data)}</div><div class="spaced">${dependentsPanel(data)}</div>`;
  content += `<div class="two-col spaced">`;
  content += panel('Still to do', e.missing.length ? e.missing.map(text => `<div class="list-row"><div class="row-content">${icon('clock')}<div><b>${escape(text)}</b><p>From the enrollment completeness check.</p></div></div>${badge('Action needed', 'warning')}</div>`).join('') : emptyState('No missing items in this snapshot', 'HR may still need to review eligibility or exceptions. This is not an approval.', 'check'));
  content += panel('Retirement match', `<div class="panel-body"><p>${escape(data.retirement_match)}.</p><p class="inline-note">This explains the demo plan rule. Your contribution is your choice.</p>${e.notes.length ? `<div class="spaced">${e.notes.map(note => `<p class="inline-note">${escape(note)}</p>`).join('')}</div>` : ''}</div>`);
  content += `</div>${data.evidence?.length ? `<div class="spaced">${documentStatus(data.evidence)}</div>` : ''}<div class="spaced">${enrollmentActions(data)}</div><div class="spaced">${enrollmentHelp(data)}</div>`;
  const item = data.cases.find(value => value.kind === 'enrollment');
  if (item) content += `<div class="spaced">${enrollmentGuidance(item)}</div>`;
  return content;
}

function leaveDraftReview(draft, data) {
  const r = draft.request || {};
  const latest = draft.clarifications?.[draft.clarifications.length - 1];
  const schedule = data.leave_schedules?.find(item => item.id === r.schedule)?.label;
  const missing = [...(draft.missing_fields || []), ...(draft.missing_documents || []).map(doc => `Document: ${doc}`)];
  const agent = latest ? `<div class="help-answer"><small>${icon('bot')}Leave Agent</small>${latest.message ? `<p class="generated-text">${escape(latest.message)}</p>` : notice(`AI explanation unavailable: ${latest.ai_error || 'no answer'} The checklist below comes from the request check.`, 'warning')}${latest.question ? `<p class="help-follow-up"><b>Question for you:</b> ${escape(latest.question)}</p>` : ''}${refChips(latest.policy_refs)}</div>` : '';
  return panel(`Review your draft · ${escape(draft.id)}`, `<div class="panel-body draft-review">${agent}<dl class="definition spaced"><div><dt>Leave type</dt><dd>${escape(draft.leave_type_label || 'Not chosen')}</dd></div><div><dt>Dates</dt><dd>${r.start_date ? formatDate(r.start_date) : 'Not set'} – ${r.end_date ? formatDate(r.end_date) : 'Not set'}</dd></div><div><dt>Schedule</dt><dd>${escape(schedule || 'Not chosen')}</dd></div><div><dt>Documents</dt><dd>${escape((r.documents_attached || []).join(', ') || 'None marked')}</dd></div></dl>${r.reason ? `<p class="inline-note spaced">Your note: ${escape(r.reason)}</p>` : ''}${missing.length ? `<h3 class="spaced">Still missing</h3>${missing.map(text => `<p class="inline-note">${icon('clock')} ${escape(text)}</p>`).join('')}` : `<p class="spaced">${badge('Nothing missing in this draft', 'success', 'check')}</p>`}</div><form id="leave-confirm-form" data-draft-id="${escape(draft.id)}"><div class="panel-body">${draft.ready_to_confirm ? `${draft.missing_documents?.length ? notice('You can submit without the documents; HR may ask for them. Submitting is not an approval.', 'warning') : ''}<label class="confirm-check spaced"><input type="checkbox" name="confirmed" required><span>I confirm these details are correct and want HR to review this request.</span></label>` : notice('Add the leave type, valid dates and a schedule, then check the draft again before submitting.', 'warning')}</div><div class="form-actions"><button class="btn primary" type="submit" data-workflow-action="leave-confirm" ${draft.ready_to_confirm ? '' : 'disabled data-locked="true"'}>Submit to HR</button></div></form>`, 'Nothing is sent to HR until you confirm.');
}

function leaveBalancePanel(data) {
  const b = data.leave_balance;
  if (!b) return '';
  if (b.status !== 'ok') return notice('Your leave balance could not be determined from the HR system right now. This is not a denial.', 'warning');
  const categories = [['pto', 'PTO'], ['sick', 'Sick'], ['personal', 'Personal']];
  return panel('Your leave balance', `<div class="panel-body"><dl class="definition">${categories.map(([key, label2]) => `<div><dt>${escape(label2)}</dt><dd>${escape(b.balances[key])} hrs</dd></div>`).join('')}</dl><p class="inline-note">As of ${formatDate((b.as_of || '').slice(0, 10))}. HR system figures, not a promise of eligibility.</p></div>`);
}

function leaveIntakeBlock(data) {
  const result = data.intake_result;
  const typeLabel = result?.suggested_leave_type ? data.leave_types.find(t => t.id === result.suggested_leave_type)?.label : null;
  const answer = result ? `<div class="help-answer spaced"><small>${icon('bot')}Leave Agent</small>${result.reason ? `<p class="generated-text">${escape(result.reason)}</p>` : result.ai_error ? notice(`AI explanation unavailable: ${result.ai_error}`, 'warning') : ''}${typeLabel ? `<p><b>Suggested type:</b> ${escape(typeLabel)}</p>` : ''}${result.documents_likely_needed?.length ? `<p><b>Documents you'll likely need:</b> ${escape(result.documents_likely_needed.join(', '))}</p>` : ''}${result.balance_note ? `<p><b>Which balance:</b> ${escape(result.balance_note)}</p>` : ''}${result.follow_up_question ? `<p class="help-follow-up"><b>Question for you:</b> ${escape(result.follow_up_question)}</p>` : ''}${refChips(result.policy_refs)}${typeLabel ? `<div class="actions spaced"><button class="btn" type="button" id="use-intake-suggestion" data-leave-type="${escape(result.suggested_leave_type)}">Use this suggestion</button></div>` : ''}</div>` : '';
  return panel('Not sure what kind of leave to ask for?', `<form id="leave-intake-form" class="workflow-form"><div class="panel-body"><div class="form-field"><label for="leave-description">What's going on?</label><textarea id="leave-description" name="description" maxlength="1000" placeholder="For example: I need surgery and expect to be out about two weeks."></textarea></div>${answer}</div><div class="form-actions"><button class="btn primary" type="submit" data-workflow-action="leave-intake">${icon('bot')}Get a suggestion</button></div></form>`, "Describe your situation; the Leave Agent suggests a type, documents and which balance fits -- you still choose, below.");
}

function leave(data) {
  const header = pageHeader('Leave requests', 'Prepare the information HR needs to review your time away.', 'Employee workspace');
  if (data.employee?.kind !== 'current employee') return header + panel('Leave requests', emptyState('Choose a current-employee profile', 'The leave examples belong to E1001–E1005. New-hire profiles use the benefits journey.', 'calendar'));
  const draft = (data.leave_drafts || []).find(item => item.status === 'draft');
  const r = draft?.request || {};
  const docs = data.leave_types.flatMap(type => type.required_documents.map(doc => ({ type: type.id, doc })));
  const form = `<section class="panel"><div class="panel-heading"><div><h2>${draft ? 'Update your draft' : 'Start a leave request'}</h2><p>Share only what HR needs. No medical details are needed.</p></div>${badge(draft ? `Draft ${draft.id}` : 'New draft', 'neutral')}</div><form id="leave-draft-form"><div class="panel-body"><div class="form-field"><label for="leave-type">Leave type</label><select id="leave-type" name="leave_type"><option value="">Choose a leave type</option>${data.leave_types.map(type => `<option value="${escape(type.id)}" ${type.id === r.leave_type ? 'selected' : ''}>${escape(type.label)}</option>`).join('')}</select></div><div class="form-grid"><div class="form-field"><label for="start-date">Start date</label><input id="start-date" name="start_date" type="date" value="${escape(r.start_date || '')}"></div><div class="form-field"><label for="end-date">End date</label><input id="end-date" name="end_date" type="date" value="${escape(r.end_date || '')}"></div></div><div class="form-field"><label for="leave-schedule">Schedule</label><select id="leave-schedule" name="schedule"><option value="">Choose a schedule</option>${(data.leave_schedules || []).map(item => `<option value="${escape(item.id)}" ${item.id === r.schedule ? 'selected' : ''}>${escape(item.label)}</option>`).join('')}</select></div><fieldset class="form-field"><legend>Supporting documents</legend><p class="inline-note">Demo labels only: no file is uploaded.</p>${docs.map(({ type, doc }) => `<label class="confirm-check" data-doc-type="${escape(type)}" ${type === r.leave_type ? '' : 'hidden'}><input type="checkbox" name="documents" value="${escape(doc)}" ${(r.documents_attached || []).includes(doc) ? 'checked' : ''}><span>I have the ${escape(doc)} ready</span></label>`).join('')}<p class="inline-note" id="no-docs-note" ${docs.some(item => item.type === r.leave_type) ? 'hidden' : ''}>${r.leave_type ? 'No document is required for this leave type.' : 'Choose a leave type to see required documents.'}</p></fieldset><div class="form-field"><label for="leave-note">Anything HR should know <span style="font-weight:400">(optional)</span></label><textarea id="leave-note" name="reason" maxlength="1000" placeholder="Helpful context only. No medical details.">${escape(r.reason || '')}</textarea></div></div><div class="form-actions"><button class="btn primary" type="submit" data-workflow-action="leave-draft">${icon('bot')}Check draft with the Leave Agent</button></div></form></section>`;
  return header
    + `<div class="spaced">${leaveBalancePanel(data)}</div>`
    + `<div class="spaced">${leaveIntakeBlock(data)}</div>`
    + notice('Step 1: the Leave Agent checks your draft and asks about anything unclear. Step 2: you confirm. Only then does HR receive the request.')
    + `<div class="two-col spaced">${form}${draft ? leaveDraftReview(draft, data) : panel('What happens next', `<div class="panel-body"><div class="timeline"><div class="timeline-item"><small>1 · You and the Leave Agent</small><p>Draft the request; the agent points out anything missing.</p></div><div class="timeline-item"><small>2 · You</small><p>Review and confirm the exact details.</p></div><div class="timeline-item"><small>3 · HR</small><p>Reviews eligibility and decides. A pre-check is not a decision.</p></div></div></div>`)}</div><div class="spaced">${panel('Your submitted requests', requests({ ...data, cases: data.cases.filter(item => item.kind === 'leave') }))}</div>`
    + agentInfo('Leave Agent', 'It explains missing fields and documents and asks one clarifying question at a time. It never approves leave or promises eligibility.');
}

function tasks(data) {
  const missing = data.enrollment?.missing || [];
  return pageHeader('My next steps', 'A checklist of outstanding items from your current enrollment snapshot.', 'Employee workspace')
    + notice('This checklist comes from existing checks. Persistent task assignment, document verification, and reminders are planned for the action-tracker phase.')
    + `<div class="spaced">${panel('Outstanding enrollment items', missing.length ? missing.map(text => `<div class="list-row"><div class="row-content">${icon('document')}<div><b>${escape(text)}</b><p>Responsible: employee · Enrollment deadline: ${formatDate(data.enrollment.deadline)}</p></div></div>${buttonLink('View', '#/employee/benefits')}</div>`).join('') : emptyState('No outstanding enrollment items', 'This does not establish HR approval or vendor confirmation. Check your requests for case updates.', 'check'))}</div>`;
}

function leaveGuidance(item) {
  return `<div class="spaced">${panel('Leave Agent check', `<div class="panel-body">${item.guidance ? `<p class="generated-text">${escape(item.guidance)}</p>` : item.ai_error ? notice(`AI explanation unavailable: ${item.ai_error}`, 'warning') : ''}${item.missing?.length ? `<h3 class="spaced">Missing when submitted</h3>${item.missing.map(text => `<p class="inline-note">${escape(text)}</p>`).join('')}` : '<p class="spaced">Nothing was missing when you submitted.</p>'}<p class="inline-note spaced">HR reviews eligibility and decides. This check is not a decision.</p></div>`)}</div>`;
}

function caseDetail(data, caseId) {
  const item = data.cases.find(value => value.id === caseId);
  const back = `<a class="back-link" href="#/employee/overview">${icon('back')}Back to overview</a>`;
  if (!item) return back + pageHeader('Request not found', 'This case is not available in the selected employee’s workspace.') + notice('Choose a request from your own overview.', 'warning');
  return back + pageHeader(caseName(item), 'Your request status and the latest employee-visible update.', item.id)
    + panel('Request status', `<div class="panel-body">${statusBadge(item.status)}<p class="spaced">${escape(item.employee_update || 'There is no employee update recorded yet.')}</p>${item.dates ? `<dl class="definition spaced"><div><dt>Start date</dt><dd>${formatDate(item.dates[0])}</dd></div><div><dt>End date</dt><dd>${formatDate(item.dates[1])}</dd></div></dl>` : ''}</div>`)
    + (item.kind === 'enrollment' ? `<div class="spaced">${enrollmentGuidance(item)}</div>` : leaveGuidance(item))
    + (item.kind === 'leave' && item.pending_documents?.length ? `<div class="spaced">${requestedDocumentsPanel(item)}</div>` : '')
    + (item.kind === 'leave' && item.status === 'info_requested' ? `<div class="spaced">${leaveResubmitForm(item, data)}</div>` : '')
    + (item.kind === 'enrollment' && item.status === 'info_requested' ? `<div class="spaced">${panel('HR asked for more information', `<div class="panel-body"><p>Update your elections, dependents or documents, then recheck your enrollment. Rechecking sends the same case back to HR.</p><div class="actions spaced">${buttonLink('Update my enrollment', '#/employee/benefits', { primary: true, symbol: 'arrow' })}</div></div>`)}</div>` : '')
    + (item.activity?.length ? `<div class="spaced">${activityPanel(item.activity, 'What happened on your request')}</div>` : '')
    + `<div class="spaced">${stageNote('You can correct a request only after HR asks for more information. Internal HR notes are not included in this employee view.')}</div>`;
}

export function employeeView(route, data) {
  if (route.page === 'cases') return caseDetail(data, route.caseId);
  return ({ overview, benefits, leave, tasks }[route.page] || (() => pageHeader('Page not found', 'Choose a destination from the navigation.')))(data);
}
