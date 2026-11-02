"""The two workflows and the HR review queue. Plain code, not an agent.

Workflow A (enrollment): employee checks enrollment -> Enrollment Agent -> HR review
  -> HR approves (this freezes the handoff packet) -> Vendor Agent prepares records -> HR marks sent -> confirmations tracked.
Workflow B (leave): employee submits -> Leave Agent -> HR review -> HR decides -> employee update.

Only HR actions move a case past review. Every step is logged in the case history.
"""

from benefits_leave import agents, checks
from benefits_leave.hr_lookup import load_fake_hr_data, lookup_employee_leave_balance

DECISIONS = {"approve", "deny", "request_info", "approved_pending_documents"}
LEAVE_ONLY_DECISIONS = {"approved_pending_documents"}
MAX_QUESTION_CHARS = 600
MAX_REASON_CHARS = 1000
LEAVE_SCHEDULES = {"continuous": "One continuous block", "intermittent": "Intermittent (separate days or hours)",
                   "reduced": "Reduced schedule"}
MAX_CONSULTATIONS_PER_RUN = 1
CONSULT_QUESTION_TYPES = {"approved_enrollment_intent"}
ACTORS = {"employee", "code", "enrollment_agent", "vendor_agent", "leave_agent", "hr"}
ELECTION_STATUSES = {"elected", "waived", "not_started"}
NON_TIER_PLAN_FIELDS = {"description", "network", "deductible", "total_premium"}
MAX_NAME_CHARS = 80
DEPENDENT_RELATIONSHIPS = {"spouse", "child"}


class WorkflowError(Exception):
    """An action that isn't allowed in the case's current state."""


class CaseStore:
    def __init__(self, data=None, client=None, lookup=None):
        self.data = data or checks.load_data()
        self.client = client          # None = real Claude; tests pass a pretend client
        self.lookup = lookup          # None = the real leave lookup tool
        self.cases = {}
        self.help_threads = {}        # employee_id -> enrollment questions and answers (no case state)
        self.consider_results = {}    # employee_id -> {benefit: last "consider" result} (no case state)
        self.intake_results = {}      # employee_id -> last leave-intake suggestion (no case state)
        self.drafts = {}              # leave drafts: not cases until the employee confirms
        self._next_draft = 1
        self._next = 1
        self._seed()

    # --- helpers -----------------------------------------------------------------------
    def _new_case(self, kind, employee_id, **fields):
        case_id = f"C{self._next}"
        self._next += 1
        self.cases[case_id] = {"id": case_id, "kind": kind, "employee_id": employee_id,
                               "history": [], "activity": [], "employee_update": None, **fields}
        return self.cases[case_id]

    def _log(self, case, event):
        case["history"].append(event)

    def _activity(self, case, actor, action, finding="", *, evidence_refs=(), unknowns=(), next_step="",
                  visibility="hr"):
        """A structured, readable record of who did what. Never hidden model reasoning.

        visibility "employee" means the employee and HR see it; "hr" means HR only.
        """
        assert actor in ACTORS and visibility in ("employee", "hr")
        case.setdefault("activity", []).append({
            "step": len(case.get("activity", [])) + 1, "actor": actor, "action": action, "finding": finding,
            "evidence_refs": list(evidence_refs), "unknowns": list(unknowns), "next_step": next_step,
            "visibility": visibility})

    def get(self, case_id):
        if case_id not in self.cases:
            raise WorkflowError(f"No case {case_id}")
        return self.cases[case_id]

    def _seed(self):
        """One enrollment that HR already approved and sent, so vendor tracking can be shown."""
        case = self._new_case("enrollment", "E2004", status="sent_to_vendors",
                              enrollment=checks.enrollment_status("E2004", self.data), ai=None,
                              sent_at="2026-09-28")   # 28 days before the demo's as_of: shows "approaching window"
        case["handoff"] = checks.build_vendor_handoff(case["id"], "E2004", self.data, "Demo approval")
        self._log(case, "Demo: approved by HR and sent to vendors")
        self._activity(case, "hr", "Approved the enrollment and recorded sending (seeded demo case)",
                       evidence_refs=[case["handoff"]["snapshot_ref"]], next_step="Check vendor confirmations")

    # --- Workflow A: enrollment --------------------------------------------------------
    def check_enrollment(self, employee_id):
        """Employee checks their enrollment. Creates or updates their case."""
        case = next((c for c in self.cases.values()
                     if c["kind"] == "enrollment" and c["employee_id"] == employee_id), None)
        if case and case["status"] not in ("incomplete", "ready_for_hr_review", "info_requested"):
            # A decided case is a historical snapshot, not a new AI request.
            return {"status": case["enrollment"], "ai": case.get("ai"),
                    "ai_error": case.get("ai_error")}, case
        result = agents.run_enrollment_agent(employee_id, client=self.client, data=self.data)
        status = result["status"]
        if status["status"] != "ok":
            raise WorkflowError("No enrollment found for this employee")
        new_status = "incomplete" if status["missing"] else "ready_for_hr_review"
        evidence = checks.evidence_status(employee_id, self.data)
        if case is None:
            case = self._new_case("enrollment", employee_id, status=new_status, enrollment=status,
                                  ai=result["ai"], ai_error=result["ai_error"], evidence=evidence)
        else:
            case.update(status=new_status, enrollment=status, ai=result["ai"], ai_error=result["ai_error"],
                        evidence=evidence)
        self._log(case, f"Enrollment checked: {status['enrollment_state']}")
        missing = len(status["missing"])
        self._activity(case, "enrollment_agent" if result["ai"] else "code",
                       "Checked the enrollment and explained it to the employee" if result["ai"]
                       else "Checked the enrollment (AI explanation unavailable)",
                       f"{missing} item{'s' if missing != 1 else ''} still missing" if missing else "Nothing missing",
                       evidence_refs=[e["evidence_ref"] for e in evidence if e["evidence_ref"]],
                       next_step="Employee completes the missing items" if missing else "HR reviews the case",
                       visibility="employee")
        if status["hr_flags"]:
            self._activity(case, "code", "Flagged items for HR review", "; ".join(status["hr_flags"]),
                           next_step="HR decides whether an exception applies")
        return result, case

    # --- Workflow A: the employee actually chooses their elections ---------------------
    def _decided_enrollment_case(self, employee_id):
        """The enrollment case blocking further election changes, or None if elections are still open."""
        case = next((c for c in self.cases.values()
                     if c["kind"] == "enrollment" and c["employee_id"] == employee_id), None)
        if case and case["status"] not in ("incomplete", "ready_for_hr_review", "info_requested"):
            return case
        return None

    def _validate_election_fields(self, benefit, fields):
        """Code validates every election against real plan/tier/percent options. No agent is involved."""
        status = fields.get("status")
        if status not in ELECTION_STATUSES:
            raise WorkflowError("Status must be elected, waived or not_started")
        if benefit == "retirement":
            if status == "waived":
                raise WorkflowError("Retirement can't be waived; choose a 0% contribution instead")
            if status == "not_started":
                return {"status": "not_started"}
            options = self.data["retirement_plan"]["contribution_options_percent"]
            percent = fields.get("percent")
            if percent not in options:
                raise WorkflowError(f"Choose a contribution percent from {options}")
            return {"status": "elected", "percent": percent}
        if benefit not in self.data["rules"]["benefit_types"]:
            raise WorkflowError(f"Unknown benefit: {benefit}")
        if status in ("waived", "not_started"):
            return {"status": status}
        plans = self.data["plans"][benefit]
        plan = fields.get("plan")
        if plan not in plans:
            raise WorkflowError(f"Unknown {benefit} plan: {plan}")
        valid_tiers = {k for k in plans[plan] if k not in NON_TIER_PLAN_FIELDS}
        tier = fields.get("tier")
        if tier not in valid_tiers:
            raise WorkflowError(f"Unknown coverage tier for {plan}: {tier}")
        return {"status": "elected", "plan": plan, "tier": tier}

    def enrollment_locked(self, employee_id):
        """True once HR has decided this enrollment; elections can no longer be changed from here."""
        return self._decided_enrollment_case(employee_id) is not None

    def _open_enrollment_case(self, employee_id):
        """The employee's own enrollment case if HR hasn't decided it yet, else None."""
        return next((c for c in self.cases.values() if c["kind"] == "enrollment"
                    and c["employee_id"] == employee_id
                    and c["status"] in ("incomplete", "ready_for_hr_review", "info_requested")), None)

    def _resync_open_case(self, employee_id, status):
        """Keep an already-created, not-yet-decided case's completeness in step with the current
        elections/dependents. Without this, HR's approval gate could read a stale snapshot from
        before a later edit -- e.g. approving a case that, after a subsequent election change,
        actually has missing items again. Called after every election/dependent mutation.
        """
        case = self._open_enrollment_case(employee_id)
        if case is None:
            return
        case["enrollment"] = status
        case["status"] = "incomplete" if status["missing"] else "ready_for_hr_review"
        self._activity(case, "code", "Elections changed; completeness re-checked",
                       f"{len(status['missing'])} item(s) still missing" if status["missing"] else "Nothing missing",
                       next_step="Employee completes the missing items" if status["missing"] else "HR reviews the case",
                       visibility="employee")

    def set_election(self, employee_id, benefit, fields):
        """The employee elects, waives, or resets one benefit. Code validates it; nothing here chooses for them."""
        hire = self.data["new_hires"].get(employee_id)
        if hire is None:
            raise WorkflowError("Elections are available for new-hire profiles (E2001-E2006)")
        locked = self._decided_enrollment_case(employee_id)
        if locked:
            raise WorkflowError(f"Your enrollment was already decided (case {locked['id']}); "
                                f"contact HR to request a change")
        hire["elections"][benefit] = self._validate_election_fields(benefit, fields)
        status = checks.enrollment_status(employee_id, self.data)
        self._resync_open_case(employee_id, status)
        return status

    def consider_election(self, employee_id, benefit, fields):
        """The employee is weighing a change but hasn't saved it. The agent only explains the choice.

        Code validates the pending choice the same way a real save would, so the agent is never
        asked to react to something that isn't a real plan/tier/percent. It has no save tool.
        """
        hire = self.data["new_hires"].get(employee_id)
        if hire is None:
            raise WorkflowError("Elections are available for new-hire profiles (E2001-E2006)")
        if self._decided_enrollment_case(employee_id):
            raise WorkflowError("Your enrollment was already decided; this choice can no longer be changed")
        pending = self._validate_election_fields(benefit, fields)
        status = checks.enrollment_status(employee_id, self.data)
        evidence = checks.evidence_status(employee_id, self.data)
        policy = checks.policy_entries("enrollment", self.data)
        result = agents.run_enrollment_consider(employee_id, benefit, pending, status, evidence, policy,
                                                 client=self.client, data=self.data)
        ai = result["ai"] or {}
        allowed_evidence = {e["evidence_ref"] for e in evidence if e["evidence_ref"]}
        allowed_policy = {e["ref"] for e in policy}
        evidence_refs = [r for r in ai.get("evidence_refs", []) if r in allowed_evidence]
        policy_refs = [r for r in ai.get("policy_refs", []) if r in allowed_policy]
        outcome = {"benefit": benefit, "pending": pending, "explanation": ai.get("explanation"),
                  "evidence_refs": evidence_refs, "policy_refs": policy_refs, "ai_error": result["ai_error"]}
        self.consider_results.setdefault(employee_id, {})[benefit] = outcome
        return outcome

    # --- Workflow A: dependents (plain code, no agent -- this is plumbing, not the product) ---
    def add_dependent(self, employee_id, relationship, name):
        """The employee adds a spouse or child as a dependent. Proof is separate (mark_document_uploaded)."""
        hire = self.data["new_hires"].get(employee_id)
        if hire is None:
            raise WorkflowError("Dependents are available for new-hire profiles (E2001-E2006)")
        if self._decided_enrollment_case(employee_id):
            raise WorkflowError("Your enrollment was already decided; contact HR to add a dependent")
        if relationship not in DEPENDENT_RELATIONSHIPS:
            raise WorkflowError("Relationship must be spouse or child")
        name = (name or "").strip()
        if not name:
            raise WorkflowError("A dependent needs a name")
        if len(name) > MAX_NAME_CHARS:
            raise WorkflowError(f"Keep the name under {MAX_NAME_CHARS} characters")
        hire["dependents"].append({"name": name, "relationship": relationship, "proof_received": False})
        self._resync_open_case(employee_id, checks.enrollment_status(employee_id, self.data))
        return checks.evidence_status(employee_id, self.data)

    def mark_document_uploaded(self, employee_id, relationship, name):
        """The employee marks a dependent's proof document as uploaded. A label only, like the leave
        flow's document checkboxes -- no real file. This never sets 'verified': only HR does that,
        and there's no UI for HR verification yet (a known, explicit gap, not silently dropped).
        """
        hire = self.data["new_hires"].get(employee_id)
        if hire is None:
            raise WorkflowError("Documents are available for new-hire profiles (E2001-E2006)")
        if self._decided_enrollment_case(employee_id):
            raise WorkflowError("Your enrollment was already decided; contact HR about this document")
        if relationship not in DEPENDENT_RELATIONSHIPS:
            raise WorkflowError("Relationship must be spouse or child")
        dependent = next((d for d in hire["dependents"]
                          if d["relationship"] == relationship and d["name"] == name), None)
        if dependent is None:
            raise WorkflowError("That dependent was not found; add them first")
        requirement = self.data["rules"]["dependent_proof"][relationship]
        existing = next((e for e in self.data.setdefault("evidence", {}).setdefault(employee_id, [])
                         if e["requirement"] == requirement and e["dependent"] == name), None)
        if existing and existing["state"] in ("received", "verified"):
            raise WorkflowError(f"{requirement.capitalize()} for {name} is already on file")
        entry_id = f"EV-{employee_id}-{relationship[:2].upper()}{len(self.data['evidence'][employee_id]) + 1}"
        self.data["evidence"][employee_id].append({
            "id": entry_id, "employee_id": employee_id, "scope": "enrollment", "requirement": requirement,
            "dependent": name, "state": "received", "received_on": self.data["as_of"],
            "channel": "employee portal upload", "verified_by": None, "verified_on": None})
        self._resync_open_case(employee_id, checks.enrollment_status(employee_id, self.data))
        return checks.evidence_status(employee_id, self.data)

    def enrollment_cost_summary(self, employee_id):
        """What the employee pays per paycheck, and what the employer pays, across every election."""
        hire = self.data["new_hires"].get(employee_id)
        if hire is None:
            return None
        employee_total, employer_total = 0.0, 0.0
        for benefit in self.data["rules"]["benefit_types"]:
            election = hire["elections"].get(benefit, {})
            if election.get("status") != "elected":
                continue
            plan_entry = self.data["plans"][benefit].get(election.get("plan"), {})
            employee_cost = plan_entry.get(election.get("tier"))
            total_premium = plan_entry.get("total_premium", {}).get(election.get("tier"))
            if employee_cost is None or total_premium is None:
                continue
            employee_total += employee_cost
            employer_total += total_premium - employee_cost
        retirement = hire["elections"].get(checks.RETIREMENT, {})
        if retirement.get("status") == "elected":
            percent = retirement.get("percent", 0)
            match_percent = min(percent, self.data["retirement_plan"]["match_up_to_percent"])
            # Informational only -- a percent of pay, not a dollar figure this demo computes payroll for.
            employee_total_note = f"{percent}% of pay"
            employer_match_note = f"{match_percent}% of pay (vests 25%/year, fully yours after 4 years)"
        else:
            employee_total_note = employer_match_note = None
        return {"employee_per_paycheck": round(employee_total, 2), "employer_per_paycheck": round(employer_total, 2),
                "retirement_employee_contribution": employee_total_note, "retirement_employer_match": employer_match_note}

    def enrollment_help(self, employee_id, question):
        """Answer an employee's question. Never creates a case, changes a status or sends a notice."""
        question = (question or "").strip()
        if employee_id not in self.data["new_hires"]:
            raise WorkflowError("Enrollment help is available for new-hire profiles (E2001-E2006)")
        if not question:
            raise WorkflowError("Type a question for the Enrollment Agent")
        if len(question) > MAX_QUESTION_CHARS:
            raise WorkflowError(f"Keep the question under {MAX_QUESTION_CHARS} characters")
        thread = self.help_threads.setdefault(employee_id, [])
        result = agents.run_enrollment_help(employee_id, question, thread, client=self.client, data=self.data)
        ai = result["ai"] or {}
        turn = {"question": question, "answer": ai.get("answer"), "follow_up_question": ai.get("follow_up_question") or "",
                "evidence_refs": ai.get("evidence_refs", []), "policy_refs": ai.get("policy_refs", []),
                "unresolved": ai.get("unresolved", []), "facts": result["facts"], "ai_error": result["ai_error"],
                "dropped_refs": result["dropped_refs"]}
        thread.append(turn)
        del thread[:-10]
        return turn

    def prepare_vendor_records(self, case_id):
        case = self.get(case_id)
        if case["kind"] != "enrollment" or case["status"] != "approved":
            raise WorkflowError("Vendor records can only be prepared after HR approves the enrollment")
        case["vendor"] = {"records": case["handoff"]["records"]}   # exactly what HR approved
        case["status"] = "vendor_records_ready"
        self._log(case, "Vendor-ready records prepared (not sent)")
        self._activity(case, "code", "Prepared vendor records from the frozen approved packet",
                       f"{len(case['vendor']['records'])} records; nothing sent",
                       evidence_refs=[case["handoff"].get("snapshot_ref")], next_step="HR records sending")
        return case

    def mark_sent(self, case_id):
        case = self.get(case_id)
        if case["status"] != "vendor_records_ready":
            raise WorkflowError("Prepare vendor records before marking them sent")
        case["status"] = "sent_to_vendors"
        case["sent_at"] = self.data["as_of"]
        self._log(case, "HR marked records as sent to vendors")
        self._activity(case, "hr", "Recorded a simulated sending step", "No external transmission",
                       next_step="Check vendor confirmations")
        return case

    def _consultation_router(self, case):
        """Workflow code routes the Vendor Agent's question to the Enrollment Agent.

        The employee, case and approved snapshot come from the case, never from the model.
        One consultation per vendor run; the specialist has no tool to call anyone back.
        """
        handoff = case["handoff"]
        used = {"count": 0}

        def consult(question_type="", benefit="", question=""):
            consultations = case.setdefault("consultations", [])
            request = {"request_id": f"CONSULT-{case['id']}-{len(consultations) + 1}", "case_id": case["id"],
                       "employee_id": case["employee_id"], "from_agent": "vendor", "to_agent": "enrollment",
                       "question_type": question_type, "benefit": benefit, "question": str(question)[:500],
                       "approved_snapshot_ref": handoff.get("snapshot_ref")}

            def finish(reply, model_calls=0):
                reply = {"request_id": request["request_id"], **reply}
                consultations.append({**request, "reply": reply, "model_calls": model_calls})
                self._log(case, f"Vendor Agent consulted Enrollment Agent about {benefit or 'an unknown benefit'}"
                                f" ({reply['status']})")
                self._activity(case, "vendor_agent", f"Asked the Enrollment Agent about the approved {benefit} intent",
                               request["question"], evidence_refs=[request["approved_snapshot_ref"]],
                               next_step="Enrollment Agent answers from the frozen approved packet")
                self._activity(case, "enrollment_agent" if reply["status"] == "answered" else "code",
                               "Answered the Vendor Agent" if reply["status"] == "answered"
                               else "Consultation unavailable", reply.get("finding") or "",
                               evidence_refs=reply.get("evidence_refs", []), unknowns=reply.get("unknowns", []),
                               next_step=reply.get("proposed_next_action", ""))
                return reply

            def unavailable(reason):
                return finish({"status": "unavailable", "finding": None, "evidence_refs": [], "unknowns": [reason],
                               "proposed_next_action": "HR reviews the approved handoff directly"})

            if used["count"] >= MAX_CONSULTATIONS_PER_RUN:
                return unavailable("Consultation budget for this run is already used")
            used["count"] += 1
            if question_type not in CONSULT_QUESTION_TYPES:
                return unavailable(f"Question type '{question_type}' is not allowed")
            snapshot = checks.approved_snapshot_record(handoff, benefit)
            if snapshot is None or snapshot["record"].get("employee_id") != case["employee_id"]:
                return unavailable(f"No approved {benefit or 'benefit'} record exists in this case's snapshot")
            if snapshot["record"].get("plan"):
                plan_entry = self.data["plans"][benefit].get(snapshot["record"]["plan"], {})
                snapshot["plan_costs_by_tier"] = {k: v for k, v in plan_entry.items() if isinstance(v, (int, float))}
            hire = self.data["new_hires"][case["employee_id"]]
            dependents = {"employee_id": case["employee_id"], "as_of": self.data["as_of"],
                          "dependents_on_record": [{k: d[k] for k in ("name", "relationship", "proof_received")}
                                                   for d in hire["dependents"]],
                          "documents": [{"evidence_ref": e["id"], "requirement": e["requirement"],
                                         "dependent": e["dependent"], "state": e["state"]}
                                        for e in checks.evidence_for(case["employee_id"], self.data)]}
            result = agents.run_enrollment_specialist(snapshot, dependents, request["question"],
                                                      client=self.client, data=self.data)
            if result["ai"] is None:
                return finish({"status": "unavailable", "finding": None, "evidence_refs": [],
                               "unknowns": [f"The Enrollment Agent could not answer: {result['ai_error']}"],
                               "proposed_next_action": "HR reviews the approved handoff directly"},
                              result.get("model_calls", 0))
            reply = {k: result["ai"].get(k) for k in ("status", "finding", "evidence_refs", "unknowns",
                                                      "proposed_next_action")}
            return finish(reply, result.get("model_calls", 0))

        return consult

    def check_vendor_confirmations(self, case_id):
        case = self.get(case_id)
        if case["status"] not in ("sent_to_vendors", "vendor_follow_up"):
            raise WorkflowError("Records must be sent to vendors before confirmations can be checked")
        before = len(case.get("consultations", []))
        activity_start = len(case.get("activity", []))
        try:
            consult = self._consultation_router(case) if case.get("handoff") else None
            result = agents.run_vendor_agent(case.get("handoff"), client=self.client, data=self.data,
                                             consult=consult)
        except agents.HandoffError as exc:
            self._log(case, f"Vendor Agent stopped: bad handoff ({exc})")
            raise WorkflowError(f"The handoff to the Vendor Agent is not valid: {exc}") from exc
        result["consultations"] = case.get("consultations", [])[before:]
        case["vendor"] = result
        all_confirmed = all(r["result"] == "confirmed" for r in result["reconciliation"])
        case["status"] = "vendor_confirmed" if all_confirmed else "vendor_follow_up"
        self._log(case, "Vendor confirmations checked: "
                  + ("all confirmed" if all_confirmed else f"{len(result['follow_ups'])} need follow-up"))
        counts = {}
        for item in result["reconciliation"]:
            counts[item["result"]] = counts.get(item["result"], 0) + 1
        self._activity(case, "code", "Compared vendor confirmations with the approved packet",
                       ", ".join(f"{n} {k.replace('_', ' ')}" for k, n in counts.items()),
                       evidence_refs=[case["handoff"].get("snapshot_ref")])
        # The comparison happens before the agent runs: show it before any consultation steps.
        case["activity"].insert(activity_start, case["activity"].pop())
        for number, item in enumerate(case["activity"], 1):
            item["step"] = number
        discrepancy = counts.get("discrepancy", 0) > 0
        unknowns = []
        if result["ai"] and discrepancy and not result["consultations"]:
            unknowns.append("The Vendor Agent did not consult the Enrollment Agent about the discrepancy")
        self._activity(case, "vendor_agent" if result["ai"] else "code",
                       "Summarized vendor results and drafted follow-ups for HR" if result["ai"]
                       else "Prepared rule-based follow-up templates (AI unavailable)",
                       (result["ai"] or {}).get("hr_summary") or f"{len(result['follow_ups'])} follow-up drafts",
                       evidence_refs=sorted({r for f in result["follow_ups"] for r in f.get("evidence_refs", [])}),
                       unknowns=unknowns + ([result["ai_error"]] if result["ai_error"] else []),
                       next_step="HR reviews the drafts and sends them through its own channel"
                       if result["follow_ups"] else "No vendor action needed")
        if all_confirmed:
            case["employee_update"] = "Your benefits enrollment is complete and confirmed by every vendor."
            self._activity(case, "code", "All vendors confirmed the approved enrollment",
                           case["employee_update"], visibility="employee")
        return case

    # --- Workflow B: leave -------------------------------------------------------------
    def submit_leave(self, request):
        result = agents.run_leave_agent(request, client=self.client, data=self.data, lookup=self.lookup)
        case = self._new_case("leave", request.get("employee_id"), status="ready_for_hr_review",
                              request=request, check=result["check"], ai=result["ai"], ai_error=result["ai_error"])
        self._log(case, "Leave request submitted"
                  + ("" if result["check"]["complete"] else " (incomplete: items missing)"))
        check = result["check"]
        missing = check["missing_fields"] + [f"Upload: {d}" for d in check["missing_documents"]]
        self._activity(case, "leave_agent" if result["ai"] else "code",
                       "Checked the request for completeness" + ("" if result["ai"] else " (AI explanation unavailable)"),
                       "Missing: " + "; ".join(missing) if missing else "Nothing missing",
                       next_step="HR reviews the request and decides", visibility="employee")
        fmla = check["fmla_precheck"]
        self._activity(case, "code", "Ran the FMLA pre-check (not a decision)", fmla["detail"],
                       evidence_refs=["DEMO-LEAVE-FMLA-BASICS@v1"],
                       unknowns=["Employment facts could not be retrieved"] if fmla["status"] == "cannot_determine" else [],
                       next_step="HR checks FMLA, state leave and company policy before deciding")
        return result, case

    # --- Workflow B: intake from a free-text description, before any draft exists -------
    def intake_leave(self, employee_id, description):
        """A suggestion only: creates no draft, no case, and never changes anything.

        The employee still picks the final leave type themselves on the form that follows.
        """
        if employee_id not in load_fake_hr_data()["employees"]:
            raise WorkflowError("Leave requests are available for current-employee profiles (E1001-E1005)")
        description = str(description or "").strip()
        if not description:
            raise WorkflowError("Describe your situation for the Leave Agent")
        if len(description) > MAX_REASON_CHARS:
            raise WorkflowError(f"Keep the description under {MAX_REASON_CHARS} characters")
        leave_types = [{"id": key, "label": value["label"], "required_documents": value["required_documents"]}
                       for key, value in self.data["leave_policy"]["leave_types"].items()]
        lookup = self.lookup or lookup_employee_leave_balance
        lookup_result = lookup(employee_id)
        balances = lookup_result["facts"]["leave_balances"]["value"] if lookup_result["status"] == "ok" else None
        result = agents.run_leave_intake(description, leave_types, balances, client=self.client, data=self.data)
        ai = result["ai"] or {}
        outcome = {"suggested_leave_type": ai.get("suggested_leave_type"), "reason": ai.get("reason"),
                  "documents_likely_needed": ai.get("documents_likely_needed", []),
                  "balance_note": ai.get("balance_note"), "follow_up_question": ai.get("follow_up_question") or "",
                  "policy_refs": ai.get("policy_refs", []), "ai_error": result["ai_error"]}
        self.intake_results[employee_id] = outcome
        return outcome

    # --- Workflow B (new journey): draft -> clarification -> employee confirmation ------
    def save_leave_draft(self, employee_id, fields):
        """Create or update the employee's open draft and ask the Leave Agent to clarify it.

        A draft is not a case: HR does not see it and no formal state changes.
        """
        if employee_id not in load_fake_hr_data()["employees"]:
            raise WorkflowError("Leave requests are available for current-employee profiles (E1001-E1005)")
        reason = str(fields.get("reason") or "").strip()
        if len(reason) > MAX_REASON_CHARS:
            raise WorkflowError(f"Keep the note under {MAX_REASON_CHARS} characters")
        leave_type = fields.get("leave_type") or ""
        known_docs = self.data["leave_policy"]["leave_types"].get(leave_type, {}).get("required_documents", [])
        schedule = fields.get("schedule") if fields.get("schedule") in LEAVE_SCHEDULES else ""
        request = {"employee_id": employee_id, "leave_type": leave_type,
                   "start_date": fields.get("start_date") or "", "end_date": fields.get("end_date") or "",
                   "schedule": schedule, "reason": reason,
                   "documents_attached": [d for d in (fields.get("documents_attached") or []) if d in known_docs]}
        draft = next((d for d in self.drafts.values()
                      if d["employee_id"] == employee_id and d["status"] == "draft"), None)
        if draft is None:
            draft = {"id": f"D{self._next_draft}", "employee_id": employee_id, "status": "draft",
                     "clarifications": [], "case_id": None}
            self._next_draft += 1
            self.drafts[draft["id"]] = draft
        kwargs = {"lookup": self.lookup} if self.lookup else {}
        check = checks.leave_request_check(request, self.data, **kwargs)
        missing_fields = check["missing_fields"] + ([] if schedule else ["Add the leave schedule"])
        result = agents.run_leave_clarifier(request, check, not schedule, client=self.client, data=self.data)
        ai = result["ai"] or {}
        draft.update(request=request, leave_type_label=check["leave_type_label"], missing_fields=missing_fields,
                     missing_documents=check["missing_documents"], ready_to_confirm=not missing_fields)
        draft["clarifications"].append({"message": ai.get("employee_message"), "question": ai.get("question") or "",
                                        "policy_refs": ai.get("policy_refs", []), "ai_error": result["ai_error"]})
        del draft["clarifications"][:-5]
        return draft

    def confirm_leave_draft(self, employee_id, draft_id, confirmed):
        """The employee confirms the exact saved draft; only then does a formal HR case exist."""
        draft = self.drafts.get(draft_id)
        if draft is None or draft["employee_id"] != employee_id:
            raise WorkflowError("That draft was not found for this employee")
        if draft["status"] != "draft":
            raise WorkflowError(f"This draft was already submitted as case {draft['case_id']}")
        if confirmed is not True:
            raise WorkflowError("Confirm that the details are correct before submitting")
        if not draft["ready_to_confirm"]:
            raise WorkflowError("Add the leave type, valid dates and schedule before submitting")
        result, case = self.submit_leave(dict(draft["request"]))
        case["draft_id"] = draft_id
        draft.update(status="submitted", case_id=case["id"])
        case["activity"].insert(0, {"step": 0, "actor": "employee", "action": "Confirmed the draft and submitted it to HR",
                                    "finding": f"Draft {draft_id}, after {len(draft['clarifications'])} "
                                               f"clarification{'s' if len(draft['clarifications']) != 1 else ''}",
                                    "evidence_refs": [], "unknowns": [], "next_step": "", "visibility": "employee"})
        for number, item in enumerate(case["activity"], 1):
            item["step"] = number
        return result, case, draft

    # --- HR decisions ------------------------------------------------------------------
    def hr_decide(self, case_id, decision, reason=""):
        case = self.get(case_id)
        reason = (reason or "").strip()
        if decision not in DECISIONS:
            raise WorkflowError("Decision must be approve, deny, request_info or approved_pending_documents")
        if decision in LEAVE_ONLY_DECISIONS and case["kind"] != "leave":
            raise WorkflowError("approved_pending_documents is only for leave requests")
        if case["status"] not in ("ready_for_hr_review", "incomplete"):
            raise WorkflowError(f"This case is already {case['status'].replace('_', ' ')}")
        if decision in ("deny", "request_info", "approved_pending_documents") and not reason:
            raise WorkflowError("A reason is required for this decision")

        if case["kind"] == "enrollment":
            if decision == "approve":
                if case["enrollment"]["missing"]:
                    raise WorkflowError("Can't approve: the employee still has missing items")
                if case["enrollment"]["hr_flags"] and not reason:
                    raise WorkflowError("This enrollment has HR flags: add a reason to approve an exception")
            labels = {"approve": "Your benefits elections were approved by HR and will be sent to the vendors.",
                      "deny": f"HR could not approve your elections: {reason}",
                      "request_info": f"HR needs more information: {reason}"}
        else:
            if decision == "approve" and not case["check"]["complete"] and not reason:
                raise WorkflowError("This request is incomplete: add a reason to approve it anyway")
            labels = {"approve": "Your leave request was approved by HR.",
                      "deny": f"Your leave request was not approved: {reason}",
                      "request_info": f"HR needs more information about your leave request: {reason}",
                      "approved_pending_documents": f"Your leave request was approved. Please also provide: {reason}"}

        case["status"] = {"approve": "approved", "deny": "denied", "request_info": "info_requested",
                          "approved_pending_documents": "approved_pending_documents"}[decision]
        case["decision"] = {"decision": decision, "reason": reason}
        case["employee_update"] = labels[decision]
        self._log(case, f"HR decision: {decision}" + (f" ({reason})" if reason else ""))
        self._activity(case, "hr", f"Recorded the HR decision: {decision.replace('_', ' ')}", labels[decision],
                       next_step={"approve": "Prepare vendor records" if case["kind"] == "enrollment" else "",
                                  "deny": "", "request_info": "Employee provides the requested information",
                                  "approved_pending_documents": "Employee provides the requested document"}[decision],
                       visibility="employee")
        if case["kind"] == "enrollment" and decision == "approve":
            # The handoff: freeze what HR approved for the Vendor Agent.
            case["handoff"] = checks.build_vendor_handoff(
                case["id"], case["employee_id"], self.data, reason, (case.get("ai") or {}).get("hr_summary"))
            self._log(case, f"Handoff to Vendor Agent created ({len(case['handoff']['records'])} records)")
            self._activity(case, "code", "Froze the approved packet for the Vendor Agent",
                           f"{len(case['handoff']['records'])} approved records",
                           evidence_refs=[case["handoff"]["snapshot_ref"]], next_step="Prepare vendor records")
        return case

    # --- views -------------------------------------------------------------------------
    def hr_queue(self):
        return list(self.cases.values())

    def employee_cases(self, employee_id):
        """Employees only ever see their own cases."""
        return [c for c in self.cases.values() if c["employee_id"] == employee_id]
