import { escape, icon, notice, panel, buttonLink, statusBadge } from './components.js';

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
    const recordedStatus = { approve: 'approved', deny: 'denied', request_info: 'info_requested' }[item.decision?.decision];
    return panel('Recorded HR decision', `<div class="panel-body">${recordedStatus ? statusBadge(recordedStatus) : ''}<p class="spaced generated-text">${escape(item.decision?.reason || (item.handoff ? `Approved enrollment handoff recorded. ${item.handoff.hr_reason || ''}` : item.employee_update) || 'No further decision is available at this stage.')}</p><p class="inline-note spaced">The current workflow status is shown in the case overview.</p></div>`);
  }
  const incomplete = item.kind === 'enrollment' && Boolean(item.enrollment?.missing?.length);
  const approvalReason = item.kind === 'enrollment' ? Boolean(item.enrollment?.hr_flags?.length) : item.check?.complete === false;
  return panel('Record an HR decision', `<form id="hr-decision-form" data-case-id="${escape(item.id)}" data-approval-reason="${approvalReason}"><div class="panel-body"><p>Review the facts before recording a decision. This is a fictional demo case; no external notice is sent.</p>${incomplete ? `<div class="spaced">${notice('Approval is blocked until the missing enrollment items are resolved. HR can request information or deny with a reason.', 'warning')}</div>` : ''}<div class="form-field spaced"><label for="hr-decision">Decision</label><select id="hr-decision" name="decision" required><option value="">Choose a decision</option><option value="approve" ${incomplete ? 'disabled' : ''}>Approve</option><option value="request_info">Request information</option><option value="deny">Do not approve</option></select></div><div class="form-field"><label for="hr-reason">Reason</label><textarea id="hr-reason" name="reason" maxlength="2000" aria-describedby="reason-help"></textarea><p class="inline-note" id="reason-help">Required for information requests, denials${approvalReason ? ' and approval of this exception' : ''}. Saved with the decision; the employee receives the decision update.</p></div></div><div class="form-actions"><button class="btn primary" data-workflow-action="decision" type="submit">Record HR decision</button></div></form>`);
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
  return `<div class="spaced">${panel('Follow-up drafts for HR', `<div class="panel-body">${result.ai_error ? notice(`AI explanation unavailable: ${result.ai_error} The comparison and rule-based draft templates are still available.`, 'warning') : ''}${result.follow_ups?.length ? result.follow_ups.map(draft => `<article class="draft spaced"><h3>${escape(draft.vendor)}</h3><p class="inline-note">${escape(draft.issue)}</p><p class="generated-text spaced">${escape(draft.draft_message)}</p><p class="inline-note spaced">Draft only · HR reviews and sends through its own channel.</p></article>`).join('') : '<p>No follow-up drafts are needed for these results.</p>'}</div>`)}</div>`;
}
