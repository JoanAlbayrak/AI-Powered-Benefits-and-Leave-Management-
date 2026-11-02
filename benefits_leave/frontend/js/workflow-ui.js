import { escape, icon, notice, panel, buttonLink, statusBadge, badge, label, formatDate } from './components.js';

export function enrollmentActions(data) {
  const item = data.cases.find(value => value.kind === 'enrollment');
  const open = !item || ['incomplete', 'ready_for_hr_review', 'info_requested'].includes(item.status);
  return panel('Check with the Enrollment Agent', `<div class="panel-body"><p>Check these recorded elections and prepare a case for HR. The agent explains the results; it does not choose benefits or approve coverage.</p><div class="actions spaced">${open ? `<button class="btn primary" data-workflow-action="enrollment">${icon('bot')}${item ? 'Recheck enrollment' : 'Check enrollment and create case'}</button>` : ''}${item ? buttonLink('View your enrollment case', `#/employee/cases/${encodeURIComponent(item.id)}`) : ''}</div><p class="inline-note spaced">${open ? 'This action may call the live model. If AI is unavailable, the checks and HR case still work.' : 'HR has already decided this case. Checking the page will not reopen it or change the approved elections.'}</p></div>`);
}

export function enrollmentGuidance(item) {
  if (!item) return '';
  return panel('Enrollment check result', `<div class="panel-body">${statusBadge(item.status)}${item.guidance ? `<p class="spaced generated-text">${escape(item.guidance)}</p>` : '<p class="spaced">Use the checklist for the recorded findings. No AI explanation is stored for this case.</p>'}${item.ai_error ? `<div class="spaced">${notice(`AI explanation unavailable: ${item.ai_error} The checklist and HR review remain available.`, 'warning')}</div>` : ''}</div>`);
}

export function decisionPanel(item) {
  if (!['incomplete', 'ready_for_hr_review'].includes(item.status)) {
    const recordedStatus = { approve: 'approved', deny: 'denied', request_info: 'info_requested',
      approved_pending_documents: 'approved_pending_documents' }[item.decision?.decision];
    return panel('Recorded HR decision', `<div class="panel-body">${recordedStatus ? statusBadge(recordedStatus) : ''}<p class="spaced generated-text">${escape(item.decision?.reason || (item.handoff ? `Approved enrollment handoff recorded. ${item.handoff.hr_reason || ''}` : item.employee_update) || 'No further decision is available at this stage.')}</p><p class="inline-note spaced">The current workflow status is shown in the case overview.</p></div>`);
  }
  const incomplete = item.kind === 'enrollment' && Boolean(item.enrollment?.missing?.length);
  const approvalReason = item.kind === 'enrollment' ? Boolean(item.enrollment?.hr_flags?.length) : item.check?.complete === false;
  const pendingDocsOption = item.kind === 'leave' ? '<option value="approved_pending_documents">Approve, pending a document</option>' : '';
  return panel('Record an HR decision', `<form id="hr-decision-form" data-case-id="${escape(item.id)}" data-review-revision="${escape(item.review_revision ?? '')}" data-approval-reason="${approvalReason}"><div class="panel-body"><p>Review the facts before recording a decision. This is a fictional demo case; no external notice is sent.</p>${incomplete ? `<div class="spaced">${notice('Approval is blocked until the missing enrollment items are resolved. HR can request information or deny with a reason.', 'warning')}</div>` : ''}<div class="form-field spaced"><label for="hr-decision">Decision</label><select id="hr-decision" name="decision" required><option value="">Choose a decision</option><option value="approve" ${incomplete ? 'disabled' : ''}>Approve</option>${pendingDocsOption}<option value="request_info">Request information</option><option value="deny">Do not approve</option></select></div><div class="form-field"><label for="hr-reason">Reason</label><textarea id="hr-reason" name="reason" maxlength="2000" aria-describedby="reason-help"></textarea><p class="inline-note" id="reason-help">Required for information requests, denials, pending-document approvals${approvalReason ? ' and approval of this exception' : ''}. Saved with the decision; the employee receives the decision update.</p></div></div><div class="form-actions"><button class="btn primary" data-workflow-action="decision" type="submit">Record HR decision</button></div></form>`);
}

export function vendorActions(item) {
  if (item.kind !== 'enrollment' || !['approved', 'vendor_records_ready', 'sent_to_vendors', 'vendor_follow_up', 'vendor_confirmed'].includes(item.status)) return '';
  let content;
  if (item.status === 'approved') content = `<p>Build vendor-ready records from the frozen packet HR approved. This does not send them.</p><div class="actions spaced"><button class="btn primary" data-workflow-action="prepare" data-case-id="${escape(item.id)}">Prepare vendor records</button></div>`;
  else if (item.status === 'vendor_records_ready') content = `<form id="vendor-sent-form" data-case-id="${escape(item.id)}"><p>This demo cannot transmit records. Record a simulated HR sending step to continue to the fictional provider confirmations.</p><label class="confirm-check spaced"><input type="checkbox" name="confirmed" required><span>I confirm this is a simulated sending step; no records will be transmitted.</span></label><div class="actions spaced"><button class="btn primary" data-workflow-action="sent" type="submit">Record simulated sending</button></div></form>`;
  else if (item.status === 'vendor_confirmed') content = '<p>Every stored confirmation matches the approved records. There is no open vendor action.</p>';
  else content = `<p>Compare fictional provider confirmations with the approved handoff and ask the Vendor Agent for a summary and follow-up drafts.</p><div class="actions spaced"><button class="btn primary" data-workflow-action="vendor-check" data-case-id="${escape(item.id)}">${icon('bot')}${item.vendor?.reconciliation ? 'Recheck confirmations' : 'Check confirmations'}</button></div><p class="inline-note spaced">Drafts stay here for HR review. Nothing is sent to a provider.</p>`;
  return `<div class="spaced">${panel('Next vendor step', `<div class="panel-body">${content}</div>`)}</div>`;
}

export function vendorDrafts(item) {
  const result = item.vendor;
  if (!result?.reconciliation) return '';
  return `<div class="spaced">${panel('Follow-up drafts for HR', `<div class="panel-body">${result.ai_error ? notice(`AI explanation unavailable: ${result.ai_error} The comparison and rule-based draft templates are still available.`, 'warning') : ''}${result.follow_ups?.length ? result.follow_ups.map(draft => `<article class="draft spaced"><h3>${escape(draft.vendor)}</h3><p class="inline-note">${escape(draft.issue)}</p><p class="generated-text spaced">${escape(draft.draft_message)}</p>${refChips(draft.evidence_refs)}<p class="inline-note spaced">Draft only · HR reviews and sends through its own channel.</p></article>`).join('') : '<p>No follow-up drafts are needed for these results.</p>'}</div>`)}</div>`;
}

const evidenceBadge = state => badge({ absent: 'Not on record', received: 'Received · awaiting HR check', verified: 'Verified by HR' }[state] || label(state), { absent: 'warning', received: '', verified: 'success' }[state] || 'neutral', { absent: 'warning', received: 'clock', verified: 'check' }[state]);
export const refChips = refs => (refs || []).length ? `<div class="ref-row">${refs.map(ref => `<span class="ref-chip">${escape(ref)}</span>`).join('')}</div>` : '';

export function documentStatus(evidence) {
  if (!evidence?.length) return '';
  return panel('Your documents', evidence.map(item => `<div class="list-row"><div class="row-content">${icon('document')}<div><b>${escape(label(item.requirement))} · ${escape(item.dependent)}</b><p>${item.state === 'absent' ? 'No document is on record for this requirement.' : item.state === 'received' ? `Received ${formatDate(item.received_on)}. It stays on your checklist until HR verifies it.` : `Verified by HR ${formatDate(item.verified_on)}.`}${item.evidence_ref ? ` · ${escape(item.evidence_ref)}` : ''}</p></div></div>${evidenceBadge(item.state)}</div>`).join(''), 'Fictional document records. Received is not the same as verified.');
}

function helpTurn(turn) {
  const answer = turn.answer ? `<p class="generated-text">${escape(turn.answer)}</p>` : notice(`AI answer unavailable: ${turn.ai_error || 'no answer'} The facts from your records are below.`, 'warning');
  return `<article class="help-turn"><p class="help-question"><b>You asked</b> ${escape(turn.question)}</p><div class="help-answer"><small>${icon('bot')}Enrollment Agent</small>${answer}${turn.follow_up_question ? `<p class="help-follow-up"><b>Question for you:</b> ${escape(turn.follow_up_question)}</p>` : ''}${refChips([...(turn.evidence_refs || []), ...(turn.policy_refs || [])])}${turn.unresolved?.length ? `<p class="inline-note spaced">Could not establish: ${escape(turn.unresolved.join('; '))}</p>` : ''}<details class="spaced"><summary>From your records</summary>${(turn.facts || []).map(fact => `<p class="inline-note">${escape(fact)}</p>`).join('')}</details></div></article>`;
}

export const HELP_SUGGESTIONS = ['I already uploaded my document. Why is it still on my list?', 'What do I still need to do before my deadline?', 'How does the 401(k) match work?'];

export function enrollmentHelp(data) {
  const thread = data.help_thread || [];
  return panel('Ask the Enrollment Agent', `<div class="panel-body"><p>Ask about your own enrollment. The agent looks up your document records and the approved demo policy before answering. Asking does not change your case, notify HR or approve anything.</p>${thread.length ? `<div class="help-thread spaced">${thread.map(helpTurn).join('')}</div>` : ''}<form id="enrollment-help-form" class="spaced"><div class="form-field"><label for="help-question">Your question</label><textarea id="help-question" maxlength="600" required placeholder="For example: I already uploaded my marriage certificate."></textarea></div><div class="chip-row" aria-label="Example questions">${HELP_SUGGESTIONS.map(text => `<button type="button" class="chip" data-help-suggestion="${escape(text)}">${escape(text)}</button>`).join('')}</div><div class="actions spaced"><button class="btn primary" type="submit" data-workflow-action="help">${icon('bot')}Ask the Enrollment Agent</button></div></form></div>`, 'Answers cite the records they used.');
}

const ACTORS = { employee: ['Employee', 'employee'], code: ['Workflow code', 'code'], hr: ['HR', 'hr'], enrollment_agent: ['Enrollment Agent', 'agent'], vendor_agent: ['Vendor Agent', 'agent'], leave_agent: ['Leave Agent', 'agent'] };

export function activityPanel(activity, title = 'Agent activity') {
  if (!activity?.length) return '';
  return panel(title, `<div class="panel-body"><div class="activity-list">${activity.map(item => {
    const [name, kind] = ACTORS[item.actor] || [label(item.actor), 'code'];
    const consult = /Enrollment Agent about|Answered the Vendor Agent|Consultation unavailable/.test(item.action);
    return `<div class="activity-item ${kind}${consult ? ' consult' : ''}"><span class="activity-step" aria-hidden="true">${escape(item.step)}</span><div><span class="activity-actor">${kind === 'agent' ? icon('bot') : ''}${escape(name)}${item.visibility === 'hr' ? ' · HR only' : ''}</span><p><b>${escape(item.action)}</b></p>${item.finding ? `<p class="${kind === 'agent' ? 'generated-text' : ''}">${escape(item.finding)}</p>` : ''}${refChips(item.evidence_refs)}${item.unknowns?.length ? `<p class="inline-note">Unknown: ${escape(item.unknowns.join('; '))}</p>` : ''}${item.next_step ? `<p class="activity-next">Next: ${escape(item.next_step)}</p>` : ''}</div></div>`;
  }).join('')}</div></div>`, 'Who acted, what they found, the records used and what happens next.');
}

export function consultationPanel(consultations) {
  if (!consultations?.length) return '';
  return panel('Specialist consultation', `<div class="panel-body">${consultations.map(c => `<article class="consult-box spaced"><p><b>${icon('bot')} Vendor Agent → Enrollment Agent</b> · ${escape(c.request_id)} · ${escape(label(c.benefit))}</p><p class="inline-note">Asked: ${escape(c.question)}</p><p>${badge(c.reply.status === 'answered' ? 'Answered' : 'Unavailable', c.reply.status === 'answered' ? 'success' : 'warning')}</p>${c.reply.finding ? `<p class="generated-text">${escape(c.reply.finding)}</p>` : ''}${refChips(c.reply.evidence_refs)}${c.reply.unknowns?.length ? `<p class="inline-note">Unknown: ${escape(c.reply.unknowns.join('; '))}</p>` : ''}${c.reply.proposed_next_action ? `<p class="activity-next">Proposed: ${escape(c.reply.proposed_next_action)}</p>` : ''}<p class="inline-note">Checked against snapshot ${escape(c.approved_snapshot_ref)} · ${escape(c.model_calls)} model call${c.model_calls === 1 ? '' : 's'}</p></article>`).join('')}</div>`, 'Routed and limited by workflow code: one consultation per vendor check.');
}

const DOC_STATE = { requested: ['Requested', 'warning', 'clock'], received: ['Received · awaiting HR check', '', 'clock'], verified: ['Verified by HR', 'success', 'check'] };
const docBadge = state => badge(...(DOC_STATE[state] || [label(state), 'neutral']));

// HR: dependent proof on an enrollment case. Received is not verified: HR verifies explicitly, on the revision it is looking at.
export function hrDocuments(item) {
  if (!item.evidence?.length) return '';
  const open = ['incomplete', 'ready_for_hr_review', 'info_requested'].includes(item.status);
  return panel('Dependent documents', `<div class="panel-body">${item.evidence.map(doc => `<div class="list-row"><div class="row-content">${icon('document')}<div><b>${escape(label(doc.requirement))} · ${escape(doc.dependent)}</b><p>${doc.state === 'absent' ? 'No document is on record.' : doc.state === 'received' ? `Received ${formatDate(doc.received_on)}. Not verified: the item stays open until HR verifies it.` : `Verified ${formatDate(doc.verified_on)}.`}</p></div></div><div class="actions">${doc.state === 'received' && open && doc.evidence_ref ? `<button class="btn" data-workflow-action="verify-document" data-case-id="${escape(item.id)}" data-evidence-ref="${escape(doc.evidence_ref)}" data-review-revision="${escape(item.review_revision ?? '')}">Mark verified</button>` : ''}${evidenceBadge(doc.state)}</div></div>`).join('')}<p class="inline-note spaced">Demo metadata only: no file is stored. Verifying records that HR checked the document.</p></div>`);
}

// HR: a leave request approved on condition of documents.
export function pendingDocumentsPanel(item) {
  if (item.kind !== 'leave' || !item.pending_documents?.length) return '';
  const waiting = ['approved_pending_documents', 'approved_documents_received'].includes(item.status);
  const rows = item.pending_documents.map(doc => `<div class="list-row"><div class="row-content">${icon('document')}<div><b>${escape(doc.document)}</b><p>${doc.state === 'requested' ? 'Waiting for the employee to provide it.' : doc.state === 'received' ? `Marked as provided ${formatDate(doc.received_on)}. HR has not checked it.` : `Verified ${formatDate(doc.verified_on)}.`}</p></div></div>${docBadge(doc.state)}</div>`).join('');
  if (!waiting) return panel('Documents requested with the approval', `<div class="panel-body">${rows}</div>`);
  const received = item.status === 'approved_documents_received';
  const options = received ? '<option value="verify_documents">Documents verified: complete the approval</option><option value="request_again">Ask for the document again</option>' : '';
  return panel('Documents requested with the approval', `<form id="doc-resolution-form" data-case-id="${escape(item.id)}"><div class="panel-body">${rows}${received ? '' : `<p class="inline-note spaced">Waiting for the employee. HR can withdraw the conditional approval if the document does not arrive.</p>`}<div class="form-field spaced"><label for="doc-resolution">Next step</label><select id="doc-resolution" name="resolution" required><option value="">Choose a step</option>${options}<option value="withdraw_approval">Withdraw the approval</option></select></div><div class="form-field"><label for="doc-reason">Reason</label><textarea id="doc-reason" name="reason" maxlength="2000"></textarea><p class="inline-note">Required to ask again or to withdraw the approval.</p></div></div><div class="form-actions"><button class="btn primary" type="submit" data-workflow-action="doc-resolution">Record this step</button></div></form>`);
}

// Employee: the documents HR asked for.
export function requestedDocumentsPanel(item) {
  if (item.kind !== 'leave' || !item.pending_documents?.length) return '';
  const asking = item.status === 'approved_pending_documents';
  return panel('Documents HR asked for', `<div class="panel-body">${asking ? '<p>Your leave request is approved on condition that HR receives these. This demo records a label only; no file is uploaded.</p>' : ''}${item.pending_documents.map(doc => `<div class="list-row"><div class="row-content">${icon('document')}<div><b>${escape(doc.document)}</b><p>${doc.state === 'requested' ? 'Not provided yet.' : doc.state === 'received' ? 'Provided. HR will check it.' : 'Checked and verified by HR.'}</p></div></div><div class="actions">${asking && doc.state === 'requested' ? `<button class="btn" data-workflow-action="provide-document" data-case-id="${escape(item.id)}" data-document="${escape(doc.document)}">Mark as provided</button>` : ''}${docBadge(doc.state)}</div></div>`).join('')}</div>`);
}

// Employee: correct the same request after HR asked for information.
export function leaveResubmitForm(item, data) {
  if (item.kind !== 'leave' || item.status !== 'info_requested') return '';
  const r = item.request || {};
  const docs = data.leave_types.flatMap(type => type.required_documents.map(doc => ({ type: type.id, doc })));
  return panel('Correct and resubmit', `<form id="leave-resubmit-form" data-case-id="${escape(item.id)}"><div class="panel-body">${notice(item.employee_update || 'HR asked for more information.', 'warning')}<p class="spaced">Update what HR asked about. This resubmits the same request; it is not approved yet.</p><div class="form-field"><label for="resubmit-type">Leave type</label><select id="resubmit-type" name="leave_type" required>${data.leave_types.map(type => `<option value="${escape(type.id)}" ${type.id === r.leave_type ? 'selected' : ''}>${escape(type.label)}</option>`).join('')}</select></div><div class="form-grid"><div class="form-field"><label for="resubmit-start">Start date</label><input id="resubmit-start" name="start_date" type="date" value="${escape(r.start_date || '')}" required></div><div class="form-field"><label for="resubmit-end">End date</label><input id="resubmit-end" name="end_date" type="date" value="${escape(r.end_date || '')}" required></div></div><div class="form-field"><label for="resubmit-schedule">Schedule</label><select id="resubmit-schedule" name="schedule" required>${(data.leave_schedules || []).map(opt => `<option value="${escape(opt.id)}" ${opt.id === r.schedule ? 'selected' : ''}>${escape(opt.label)}</option>`).join('')}</select></div><fieldset class="form-field"><legend>Supporting documents</legend><p class="inline-note">Demo labels only: no file is uploaded.</p>${[...new Set(docs.map(d => d.doc))].map(doc => `<label class="confirm-check"><input type="checkbox" name="documents" value="${escape(doc)}" ${(r.documents_attached || []).includes(doc) ? 'checked' : ''}><span>I have the ${escape(doc)} ready</span></label>`).join('')}</fieldset><div class="form-field"><label for="resubmit-note">Note for HR <span style="font-weight:400">(optional)</span></label><textarea id="resubmit-note" name="reason" maxlength="1000">${escape(r.reason || '')}</textarea></div></div><div class="form-actions"><button class="btn primary" type="submit" data-workflow-action="leave-resubmit">Resubmit to HR</button></div></form>`);
}
