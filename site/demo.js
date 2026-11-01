// Browser version of the Benefits & Leave system, for the public demo website.
//
// It mirrors benefits_leave/checks.py, workflow.py and web.py so the website
// works with no server and no API key. The one difference: the AI agents'
// messages are example messages written from the check results (demo mode),
// not live Claude calls. The live version runs on your laptop.
//
// BENEFITS_DATA and HR_DATA are inserted by scripts/build_site.py.

const Demo = (() => {
  const RETIREMENT = "retirement";

  class WorkflowError extends Error {}
  class HandoffError extends Error {}

  // --- small helpers ----------------------------------------------------------------
  const parseDate = (s) => { const [y, m, d] = s.slice(0, 10).split("-").map(Number); return new Date(Date.UTC(y, m - 1, d)); };
  const iso = (dt) => dt.toISOString().slice(0, 10);
  const addDays = (dt, n) => new Date(dt.getTime() + n * 86400000);
  const daysBetween = (a, b) => Math.round((b - a) / 86400000);
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
  const tierLabel = (t) => t.replaceAll("_", " + ");
  const clone = (x) => JSON.parse(JSON.stringify(x));

  function coverageStart(startDate) {
    return new Date(Date.UTC(startDate.getUTCFullYear(), startDate.getUTCMonth() + 1, 1));
  }

  // --- checks.py: enrollment ----------------------------------------------------------
  function enrollmentStatus(employeeId, data) {
    const hire = data.new_hires[employeeId];
    if (!hire) return { status: "error", reason: "not_found", employee_id: employeeId };
    const rules = data.rules;
    const start = parseDate(hire.start_date);
    const deadline = addDays(start, rules.enrollment_window_days);
    const daysLeft = daysBetween(parseDate(data.as_of), deadline);
    const elections = hire.elections;
    const missing = [], hrFlags = [], notes = [], done = [];

    for (const benefit of rules.benefit_types) {
      const election = elections[benefit] || { status: "not_started" };
      if (election.status === "not_started") { missing.push(`Choose a ${benefit} plan or waive ${benefit} coverage`); continue; }
      if (election.status === "waived") { done.push(`${cap(benefit)}: waived`); continue; }
      const plan = election.plan, tier = election.tier;
      const cost = ((data.plans[benefit] || {})[plan] || {})[tier];
      if (cost === undefined) { hrFlags.push(`${cap(benefit)}: plan or coverage tier not recognized (${plan}, ${tier})`); continue; }
      done.push(`${cap(benefit)}: ${plan}, ${tierLabel(tier)} tier, $${cost.toFixed(2)} per paycheck`);
      if (hire.weekly_hours < rules.benefits_eligible_min_weekly_hours) {
        hrFlags.push(`${cap(benefit)} elected, but ${hire.weekly_hours} hours/week is under the ` +
                     `${rules.benefits_eligible_min_weekly_hours}-hour benefits eligibility rule`);
      }
      for (const relationship of rules.tier_dependents[tier]) {
        const people = hire.dependents.filter((d) => d.relationship === relationship);
        const proof = rules.dependent_proof[relationship];
        if (!people.length) missing.push(`Add your ${relationship} as a dependent for the ${tierLabel(tier)} tier`);
        for (const person of people) {
          const item = `Upload ${proof} for ${person.name}`;
          if (!person.proof_received && !missing.includes(item)) missing.push(item);
        }
      }
    }

    const plan = data.retirement_plan;
    const retirement = elections[RETIREMENT] || { status: "not_started" };
    if (retirement.status === "not_started") {
      missing.push("Choose a retirement contribution (or choose 0% to decline)");
    } else {
      const percent = retirement.percent || 0;
      done.push(`Retirement: ${percent}% contribution`);
      if (percent < plan.match_up_to_percent) {
        notes.push(`Your ${percent}% contribution is below the ${plan.match_up_to_percent}% the employer ` +
                   `matches. (${plan.match_rule}.)`);
      }
    }

    if (daysLeft < 0) hrFlags.push(`Enrollment deadline passed on ${iso(deadline)}`);
    else if (missing.length && daysLeft <= 7) hrFlags.push(`Deadline in ${daysLeft} days with items still missing`);

    const state = missing.length ? "incomplete" : hrFlags.length ? "needs_hr_exception" : "complete";
    return { status: "ok", employee_id: employeeId, name: hire.name, start_date: hire.start_date,
             deadline: iso(deadline), days_left: daysLeft, enrollment_state: state,
             done, missing, hr_flags: hrFlags, notes, as_of: data.as_of };
  }

  // --- checks.py: vendor records, handoff, reconciliation -----------------------------
  function vendorRecords(employeeId, data) {
    const hire = data.new_hires[employeeId];
    const covStart = iso(coverageStart(parseDate(hire.start_date)));
    const records = [];
    for (const benefit of data.rules.benefit_types) {
      const election = hire.elections[benefit] || {};
      if (election.status !== "elected") continue;
      const deps = hire.dependents.filter((d) => data.rules.tier_dependents[election.tier].includes(d.relationship))
                                  .map((d) => d.name);
      records.push({ vendor: data.vendors[benefit], benefit, employee_id: employeeId, employee_name: hire.name,
                     plan: election.plan, tier: election.tier, coverage_start: covStart, dependents: deps,
                     employee_cost_per_paycheck: data.plans[benefit][election.plan][election.tier] });
    }
    const retirement = hire.elections[RETIREMENT] || {};
    if (retirement.status === "elected") {
      records.push({ vendor: data.vendors[RETIREMENT], benefit: RETIREMENT, employee_id: employeeId,
                     employee_name: hire.name, contribution_percent: retirement.percent,
                     first_payroll_after: hire.start_date });
    }
    return records;
  }

  const HANDOFF_FIELDS = ["case_id", "employee_id", "employee_name", "approved_as_of", "hr_reason",
                          "enrollment_summary", "records"];

  function buildVendorHandoff(caseId, employeeId, data, hrReason = "", enrollmentSummary = null) {
    return { case_id: caseId, employee_id: employeeId, employee_name: data.new_hires[employeeId].name,
             approved_as_of: data.as_of, hr_reason: hrReason, enrollment_summary: enrollmentSummary,
             records: vendorRecords(employeeId, data) };
  }

  function validateVendorHandoff(handoff) {
    if (!handoff || typeof handoff !== "object") return ["The handoff is missing"];
    const problems = HANDOFF_FIELDS.filter((f) => !(f in handoff)).map((f) => `Missing field: ${f}`);
    const records = handoff.records;
    if (!records || !records.length) problems.push("The handoff has no vendor records");
    for (const r of records || []) {
      if (r.employee_id !== handoff.employee_id) problems.push(`A ${r.benefit} record belongs to a different employee`);
      if (!r.vendor || !r.benefit) problems.push("A vendor record is missing its vendor or benefit");
    }
    return problems;
  }

  function reconcileVendorConfirmations(handoff, data) {
    const confirmations = data.vendor_confirmations[handoff.employee_id] || {};
    return handoff.records.map((record) => {
      const conf = confirmations[record.benefit];
      if (!conf || conf.status === "missing") {
        return { benefit: record.benefit, vendor: record.vendor, result: "no_confirmation",
                 detail: "No confirmation received from the vendor yet" };
      }
      if (conf.status === "pending") {
        return { benefit: record.benefit, vendor: record.vendor, result: "pending",
                 detail: "Vendor has not finished processing" };
      }
      const problems = [];
      for (const field of ["plan", "tier", "contribution_percent"]) {
        const key = field === "contribution_percent" ? "percent" : field;
        if (field in record && conf[key] !== record[field]) {
          problems.push(`${field.replaceAll("_", " ")}: we sent ${record[field]}, vendor shows ${conf[key]}`);
        }
      }
      return { benefit: record.benefit, vendor: record.vendor, result: problems.length ? "discrepancy" : "confirmed",
               detail: problems.length ? problems.join("; ") : "Matches what was sent" };
    });
  }

  // --- hr_lookup.py ---------------------------------------------------------------------
  const NUMBER_FIELDS = ["hours_worked_12mo", "months_of_service", "leave_balance_hours"];

  function lookupEmployeeLeaveBalance(employeeId, hr) {
    const err = (reason) => ({ status: "error", reason, employee_id: employeeId });
    if (typeof employeeId !== "string" || !/^E\d{4}$/.test(employeeId)) return err("invalid_employee_id");
    const record = (hr.employees || {})[employeeId];
    if (!record) return err("not_found");
    for (const f of NUMBER_FIELDS) {
      const v = record[f];
      if (typeof v !== "number" || v < 0) return err("bad_data");
    }
    const source = "lookup_employee_leave_balance";
    return { status: "ok", employee_id: employeeId, as_of: hr.as_of, facts: {
      hours_worked_12mo: { value: record.hours_worked_12mo, units: "hours", source: `${source}.hours_worked_12mo` },
      months_of_service: { value: record.months_of_service, units: "months", source: `${source}.months_of_service` },
      leave_balance: { value: record.leave_balance_hours, units: "hours", source: `${source}.leave_balance_hours` },
    } };
  }

  // --- checks.py: leave request ---------------------------------------------------------
  function leaveRequestCheck(request, data, hr) {
    const types = data.leave_policy.leave_types;
    const missing = [];
    for (const [field, label] of [["leave_type", "leave type"], ["start_date", "start date"], ["end_date", "end date"]]) {
      if (!request[field]) missing.push(`Add the ${label}`);
    }
    let leaveType = request.leave_type;
    if (leaveType && !(leaveType in types)) { missing.push("Choose a valid leave type"); leaveType = null; }
    if (request.start_date && request.end_date && request.end_date < request.start_date) {
      missing.push("The end date is before the start date");
    }
    const required = leaveType ? types[leaveType].required_documents : [];
    const attached = new Set(request.documents_attached || []);
    const missingDocs = required.filter((d) => !attached.has(d));

    const lookup = lookupEmployeeLeaveBalance(request.employee_id, hr);
    let fmla;
    if (lookup.status !== "ok") {
      fmla = { status: "cannot_determine", reason: lookup.reason,
               detail: "Eligibility facts could not be retrieved. HR must check the HR system." };
    } else {
      const months = lookup.facts.months_of_service.value, hours = lookup.facts.hours_worked_12mo.value;
      const meets = months >= 12 && hours >= 1250;
      fmla = { status: meets ? "meets_basics" : "does_not_meet_basics", months_of_service: months,
               hours_worked_12mo: hours, as_of: lookup.as_of,
               detail: `${months} months of service and ${hours} hours in the last 12 months. ` +
                       (meets ? "Meets the FMLA service and hours basics."
                              : "Does not meet the FMLA basics; HR should check state leave and company policy.") };
    }
    return { employee_id: request.employee_id, leave_type_label: leaveType ? types[leaveType].label : null,
             missing_fields: missing, missing_documents: missingDocs,
             complete: !missing.length && !missingDocs.length, fmla_precheck: fmla };
  }

  // --- agents (demo mode: example messages written from the check results) -----------
  const list = (items) => items.map((x) => `• ${x}`).join("\n");

  function enrollmentAgent(status, data) {
    const first = status.name;
    const parts = [`Hi ${first}! Here's where your benefits enrollment stands.`];
    if (status.done.length) parts.push(`Already done:\n${list(status.done)}`);
    if (status.missing.length) {
      parts.push(`Still to do:\n${list(status.missing)}`);
      parts.push(`Your deadline is ${status.deadline} (${status.days_left} days left). If you miss it, ` +
                 "you may have to wait until the next open enrollment.");
    } else {
      parts.push("You've finished every election. HR will now review your enrollment.");
    }
    parts.push(`About the 401(k): ${data.retirement_plan.match_rule}. How much to save is your choice.`);
    if (status.hr_flags.length) parts.push("Some items need HR review. HR will contact you if anything changes.");
    const hr = [`${status.name}'s enrollment is ${status.enrollment_state.replaceAll("_", " ")} ` +
                `(deadline ${status.deadline}, ${status.days_left} days left).`];
    hr.push(status.missing.length ? `Missing: ${status.missing.join("; ")}.` : "No items are missing.");
    hr.push(status.hr_flags.length ? `HR flags: ${status.hr_flags.join("; ")}.` : "No HR flags.");
    return { employee_message: parts.join("\n\n"), hr_summary: hr.join(" ") };
  }

  function leaveAgent(check, request) {
    const type = check.leave_type_label || "a leave";
    const items = check.missing_fields.concat(check.missing_documents.map((d) => `Upload: ${d}`));
    const parts = [`We received your request for ${type.toLowerCase()}` +
                   (request.start_date ? ` from ${request.start_date} to ${request.end_date || "?"}` : "") + "."];
    parts.push(items.length ? `To complete it, please add:\n${list(items)}` : "Your request is complete.");
    parts.push("HR will review your eligibility and make the decision. You'll see the update here.");
    const fmla = check.fmla_precheck;
    const fmlaText = fmla.status === "cannot_determine"
      ? "FMLA pre-check: the eligibility facts could not be retrieved, so HR must check the HR system (this is not 'not eligible')."
      : `FMLA pre-check: ${fmla.detail}`;
    const hr = [`${type}, ${request.start_date || "no start date"} to ${request.end_date || "no end date"}.`,
                items.length ? `Missing: ${items.join("; ")}.` : "Nothing is missing.", fmlaText];
    return { employee_message: parts.join("\n\n"), hr_summary: hr.join(" ") };
  }

  function completeFollowUps(reconciliation, drafted) {
    const byVendor = Object.fromEntries(drafted.map((f) => [f.vendor, f]));
    return reconciliation.filter((i) => i.result !== "confirmed").map((item) => byVendor[item.vendor] || {
      vendor: item.vendor, issue: item.detail,
      draft_message: `Hello, we're following up on a ${item.benefit} enrollment we sent. ` +
                     `${item.detail}. Could you please confirm the current status? Thank you.`,
    });
  }

  function vendorAgent(handoff, data) {
    const problems = validateVendorHandoff(handoff);
    if (problems.length) throw new HandoffError(problems.join("; "));
    const reconciliation = reconcileVendorConfirmations(handoff, data);
    const open = reconciliation.filter((r) => r.result !== "confirmed");
    const summary = `${handoff.records.length} approved records were sent for ${handoff.employee_name}. ` +
      (open.length ? `${reconciliation.length - open.length} confirmed; ${open.length} need follow-up: ` +
                     open.map((r) => `${r.vendor} (${r.result.replaceAll("_", " ")})`).join(", ") + "."
                   : "Every vendor confirmed what was sent.");
    return { records: handoff.records, reconciliation, ai: { hr_summary: summary, follow_ups: [] }, ai_error: null,
             follow_ups: completeFollowUps(reconciliation, []) };
  }

  // --- workflow.py: CaseStore -------------------------------------------------------------
  class CaseStore {
    constructor(data, hr) {
      this.data = data; this.hr = hr; this.cases = {}; this.next = 1;
      const c = this.newCase("enrollment", "E2004", { status: "sent_to_vendors",
        enrollment: enrollmentStatus("E2004", data), ai: null });
      c.handoff = buildVendorHandoff(c.id, "E2004", data, "Demo approval");
      c.history.push("Demo: approved by HR and sent to vendors");
    }
    newCase(kind, employeeId, fields) {
      const id = `C${this.next++}`;
      this.cases[id] = { id, kind, employee_id: employeeId, history: [], employee_update: null, ...fields };
      return this.cases[id];
    }
    get(id) { if (!this.cases[id]) throw new WorkflowError(`No case ${id}`); return this.cases[id]; }

    checkEnrollment(employeeId) {
      let c = Object.values(this.cases).find((x) => x.kind === "enrollment" && x.employee_id === employeeId);
      if (c && !["incomplete", "ready_for_hr_review", "info_requested"].includes(c.status)) {
        return [{ status: c.enrollment, ai: c.ai || null, ai_error: c.ai_error || null }, c];
      }
      const status = enrollmentStatus(employeeId, this.data);
      if (status.status !== "ok") throw new WorkflowError("No enrollment found for this employee");
      const ai = enrollmentAgent(status, this.data);
      const result = { status, ai, ai_error: null };
      const newStatus = status.missing.length ? "incomplete" : "ready_for_hr_review";
      if (!c) c = this.newCase("enrollment", employeeId, { status: newStatus, enrollment: status, ai });
      else Object.assign(c, { status: newStatus, enrollment: status, ai });
      c.history.push(`Enrollment checked: ${status.enrollment_state}`);
      return [result, c];
    }
    prepareVendorRecords(id) {
      const c = this.get(id);
      if (c.kind !== "enrollment" || c.status !== "approved") {
        throw new WorkflowError("Vendor records can only be prepared after HR approves the enrollment");
      }
      c.vendor = { records: c.handoff.records };
      c.status = "vendor_records_ready";
      c.history.push("Vendor-ready records prepared (not sent)");
      return c;
    }
    markSent(id) {
      const c = this.get(id);
      if (c.status !== "vendor_records_ready") throw new WorkflowError("Prepare vendor records before marking them sent");
      c.status = "sent_to_vendors";
      c.history.push("HR marked records as sent to vendors");
      return c;
    }
    checkVendorConfirmations(id) {
      const c = this.get(id);
      if (!["sent_to_vendors", "vendor_follow_up"].includes(c.status)) {
        throw new WorkflowError("Records must be sent to vendors before confirmations can be checked");
      }
      let result;
      try { result = vendorAgent(c.handoff, this.data); } catch (e) {
        if (!(e instanceof HandoffError)) throw e;
        c.history.push(`Vendor Agent stopped: bad handoff (${e.message})`);
        throw new WorkflowError(`The handoff to the Vendor Agent is not valid: ${e.message}`);
      }
      c.vendor = result;
      const allConfirmed = result.reconciliation.every((r) => r.result === "confirmed");
      c.status = allConfirmed ? "vendor_confirmed" : "vendor_follow_up";
      c.history.push("Vendor confirmations checked: " +
                     (allConfirmed ? "all confirmed" : `${result.follow_ups.length} need follow-up`));
      if (allConfirmed) c.employee_update = "Your benefits enrollment is complete and confirmed by every vendor.";
      return c;
    }
    submitLeave(request) {
      const check = leaveRequestCheck(request, this.data, this.hr);
      const ai = leaveAgent(check, request);
      const c = this.newCase("leave", request.employee_id, { status: "ready_for_hr_review", request, check, ai });
      c.history.push("Leave request submitted" + (check.complete ? "" : " (incomplete: items missing)"));
      return [{ check, ai, ai_error: null }, c];
    }
    hrDecide(id, decision, reason = "") {
      const c = this.get(id);
      reason = (reason || "").trim();
      if (!["approve", "deny", "request_info"].includes(decision)) throw new WorkflowError("Decision must be approve, deny or request_info");
      if (!["ready_for_hr_review", "incomplete"].includes(c.status)) {
        throw new WorkflowError(`This case is already ${c.status.replaceAll("_", " ")}`);
      }
      if (["deny", "request_info"].includes(decision) && !reason) {
        throw new WorkflowError("A reason is required to deny or request more information");
      }
      let labels;
      if (c.kind === "enrollment") {
        if (decision === "approve") {
          if (c.enrollment.missing.length) throw new WorkflowError("Can't approve: the employee still has missing items");
          if (c.enrollment.hr_flags.length && !reason) {
            throw new WorkflowError("This enrollment has HR flags: add a reason to approve an exception");
          }
        }
        labels = { approve: "Your benefits elections were approved by HR and will be sent to the vendors.",
                   deny: `HR could not approve your elections: ${reason}`,
                   request_info: `HR needs more information: ${reason}` };
      } else {
        if (decision === "approve" && !c.check.complete && !reason) {
          throw new WorkflowError("This request is incomplete: add a reason to approve it anyway");
        }
        labels = { approve: "Your leave request was approved by HR.",
                   deny: `Your leave request was not approved: ${reason}`,
                   request_info: `HR needs more information about your leave request: ${reason}` };
      }
      c.status = { approve: "approved", deny: "denied", request_info: "info_requested" }[decision];
      c.decision = { decision, reason };
      c.employee_update = labels[decision];
      c.history.push(`HR decision: ${decision}` + (reason ? ` (${reason})` : ""));
      if (c.kind === "enrollment" && decision === "approve") {
        c.handoff = buildVendorHandoff(c.id, c.employee_id, this.data, reason, (c.ai || {}).hr_summary || null);
        c.history.push(`Handoff to Vendor Agent created (${c.handoff.records.length} records)`);
      }
      return c;
    }
    hrQueue() { return Object.values(this.cases); }
    employeeCases(employeeId) { return Object.values(this.cases).filter((c) => c.employee_id === employeeId); }
  }

  // --- web.py: the same endpoints, answered in the browser ----------------------------------
  function employeeView(c) {
    const view = { id: c.id, kind: c.kind, status: c.status, employee_update: c.employee_update };
    if (c.kind === "leave") { view.leave_type = c.check.leave_type_label; view.dates = [c.request.start_date, c.request.end_date]; }
    return view;
  }

  function makeHandler(store) {
    const people = () => [
      ...Object.entries(store.data.new_hires).map(([id, h]) => ({ id, name: h.name, kind: "new hire" })),
      ...Object.entries(store.hr.employees).map(([id, e]) => ({ id, name: e.name, kind: "current employee" })),
    ];
    function route(path, body) {
      const eid = body.employee_id || "";
      switch (path) {
        case "/api/people": return { people: people() };
        case "/api/employee/enrollment": {
          const [r, c] = store.checkEnrollment(eid); const s = r.status;
          const keys = ["name", "deadline", "days_left", "enrollment_state", "done", "missing", "notes"];
          return { case: employeeView(c), enrollment: Object.fromEntries(keys.map((k) => [k, s[k]])),
                   message: (r.ai || {}).employee_message || null, ai_error: r.ai_error };
        }
        case "/api/employee/leave": {
          const request = {};
          for (const k of ["employee_id", "leave_type", "start_date", "end_date", "reason"]) request[k] = body[k] ?? null;
          request.documents_attached = body.documents_attached || [];
          const [r, c] = store.submitLeave(request);
          return { case: employeeView(c),
                   missing: r.check.missing_fields.concat(r.check.missing_documents.map((d) => `Upload: ${d}`)),
                   message: (r.ai || {}).employee_message || null, ai_error: r.ai_error };
        }
        case "/api/employee/cases": return { cases: store.employeeCases(eid).map(employeeView) };
        case "/api/hr/queue": return { cases: store.hrQueue() };
        case "/api/hr/decide": return { case: store.hrDecide(body.case_id, body.decision, body.reason || "") };
        case "/api/hr/vendor/prepare": return { case: store.prepareVendorRecords(body.case_id) };
        case "/api/hr/vendor/sent": return { case: store.markSent(body.case_id) };
        case "/api/hr/vendor/check": return { case: store.checkVendorConfirmations(body.case_id) };
      }
      throw new WorkflowError("Unknown action");
    }
    return (path, body) => {
      try { return clone(route(path, body || {})); } catch (e) {
        if (e instanceof WorkflowError) return { error: e.message };
        console.error(e);
        return { error: "Something went wrong. Reload the page to start the demo again." };
      }
    };
  }

  return { CaseStore, makeHandler, enrollmentStatus, vendorRecords, buildVendorHandoff, validateVendorHandoff,
           reconcileVendorConfirmations, leaveRequestCheck, lookupEmployeeLeaveBalance };
})();

if (typeof module !== "undefined") module.exports = Demo;
