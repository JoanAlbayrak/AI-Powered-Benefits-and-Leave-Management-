"""The two workflows and the HR review queue. Plain code, not an agent.

Workflow A (enrollment): employee checks enrollment -> Enrollment Agent -> HR review
  -> HR approves (this freezes the handoff packet) -> Vendor Agent prepares records -> HR marks sent -> confirmations tracked.
Workflow B (leave): employee submits -> Leave Agent -> HR review -> HR decides -> employee update.

Only HR actions move a case past review. Every step is logged in the case history.
"""

from benefits_leave import agents, checks

DECISIONS = {"approve", "deny", "request_info"}


class WorkflowError(Exception):
    """An action that isn't allowed in the case's current state."""


class CaseStore:
    def __init__(self, data=None, client=None, lookup=None):
        self.data = data or checks.load_data()
        self.client = client          # None = real Claude; tests pass a pretend client
        self.lookup = lookup          # None = the real leave lookup tool
        self.cases = {}
        self._next = 1
        self._seed()

    # --- helpers -----------------------------------------------------------------------
    def _new_case(self, kind, employee_id, **fields):
        case_id = f"C{self._next}"
        self._next += 1
        self.cases[case_id] = {"id": case_id, "kind": kind, "employee_id": employee_id,
                               "history": [], "employee_update": None, **fields}
        return self.cases[case_id]

    def _log(self, case, event):
        case["history"].append(event)

    def get(self, case_id):
        if case_id not in self.cases:
            raise WorkflowError(f"No case {case_id}")
        return self.cases[case_id]

    def _seed(self):
        """One enrollment that HR already approved and sent, so vendor tracking can be shown."""
        case = self._new_case("enrollment", "E2004", status="sent_to_vendors",
                              enrollment=checks.enrollment_status("E2004", self.data), ai=None)
        case["handoff"] = checks.build_vendor_handoff(case["id"], "E2004", self.data, "Demo approval")
        self._log(case, "Demo: approved by HR and sent to vendors")

    # --- Workflow A: enrollment --------------------------------------------------------
    def check_enrollment(self, employee_id):
        """Employee checks their enrollment. Creates or updates their case."""
        result = agents.run_enrollment_agent(employee_id, client=self.client, data=self.data)
        status = result["status"]
        if status["status"] != "ok":
            raise WorkflowError("No enrollment found for this employee")
        case = next((c for c in self.cases.values()
                     if c["kind"] == "enrollment" and c["employee_id"] == employee_id), None)
        if case and case["status"] not in ("incomplete", "ready_for_hr_review", "info_requested"):
            return result, case   # already decided or with vendors: nothing to reopen
        new_status = "incomplete" if status["missing"] else "ready_for_hr_review"
        if case is None:
            case = self._new_case("enrollment", employee_id, status=new_status, enrollment=status, ai=result["ai"])
        else:
            case.update(status=new_status, enrollment=status, ai=result["ai"])
        self._log(case, f"Enrollment checked: {status['enrollment_state']}")
        return result, case

    def prepare_vendor_records(self, case_id):
        case = self.get(case_id)
        if case["kind"] != "enrollment" or case["status"] != "approved":
            raise WorkflowError("Vendor records can only be prepared after HR approves the enrollment")
        case["vendor"] = {"records": case["handoff"]["records"]}   # exactly what HR approved
        case["status"] = "vendor_records_ready"
        self._log(case, "Vendor-ready records prepared (not sent)")
        return case

    def mark_sent(self, case_id):
        case = self.get(case_id)
        if case["status"] != "vendor_records_ready":
            raise WorkflowError("Prepare vendor records before marking them sent")
        case["status"] = "sent_to_vendors"
        self._log(case, "HR marked records as sent to vendors")
        return case

    def check_vendor_confirmations(self, case_id):
        case = self.get(case_id)
        if case["status"] not in ("sent_to_vendors", "vendor_follow_up"):
            raise WorkflowError("Records must be sent to vendors before confirmations can be checked")
        try:
            result = agents.run_vendor_agent(case.get("handoff"), client=self.client, data=self.data)
        except agents.HandoffError as exc:
            self._log(case, f"Vendor Agent stopped: bad handoff ({exc})")
            raise WorkflowError(f"The handoff to the Vendor Agent is not valid: {exc}") from exc
        case["vendor"] = result
        all_confirmed = all(r["result"] == "confirmed" for r in result["reconciliation"])
        case["status"] = "vendor_confirmed" if all_confirmed else "vendor_follow_up"
        self._log(case, "Vendor confirmations checked: "
                  + ("all confirmed" if all_confirmed else f"{len(result['follow_ups'])} need follow-up"))
        if all_confirmed:
            case["employee_update"] = "Your benefits enrollment is complete and confirmed by every vendor."
        return case

    # --- Workflow B: leave -------------------------------------------------------------
    def submit_leave(self, request):
        result = agents.run_leave_agent(request, client=self.client, data=self.data, lookup=self.lookup)
        case = self._new_case("leave", request.get("employee_id"), status="ready_for_hr_review",
                              request=request, check=result["check"], ai=result["ai"])
        self._log(case, "Leave request submitted"
                  + ("" if result["check"]["complete"] else " (incomplete: items missing)"))
        return result, case

    # --- HR decisions ------------------------------------------------------------------
    def hr_decide(self, case_id, decision, reason=""):
        case = self.get(case_id)
        reason = (reason or "").strip()
        if decision not in DECISIONS:
            raise WorkflowError("Decision must be approve, deny or request_info")
        if case["status"] not in ("ready_for_hr_review", "incomplete"):
            raise WorkflowError(f"This case is already {case['status'].replace('_', ' ')}")
        if decision in ("deny", "request_info") and not reason:
            raise WorkflowError("A reason is required to deny or request more information")

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
                      "request_info": f"HR needs more information about your leave request: {reason}"}

        case["status"] = {"approve": "approved", "deny": "denied", "request_info": "info_requested"}[decision]
        case["decision"] = {"decision": decision, "reason": reason}
        case["employee_update"] = labels[decision]
        self._log(case, f"HR decision: {decision}" + (f" ({reason})" if reason else ""))
        if case["kind"] == "enrollment" and decision == "approve":
            # The handoff: freeze what HR approved for the Vendor Agent.
            case["handoff"] = checks.build_vendor_handoff(
                case["id"], case["employee_id"], self.data, reason, (case.get("ai") or {}).get("hr_summary"))
            self._log(case, f"Handoff to Vendor Agent created ({len(case['handoff']['records'])} records)")
        return case

    # --- views -------------------------------------------------------------------------
    def hr_queue(self):
        return list(self.cases.values())

    def employee_cases(self, employee_id):
        """Employees only ever see their own cases."""
        return [c for c in self.cases.values() if c["employee_id"] == employee_id]
