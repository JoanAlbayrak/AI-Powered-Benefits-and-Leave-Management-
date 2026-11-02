"""Employee-facing responses never carry HR-only data (task 2)."""
import json
import unittest

from benefits_leave import agents
from benefits_leave.web import handle
from benefits_leave.workflow import CaseStore
from tests.scripted_client import ScriptedClient, read_all_then, submit_name

# Keys that exist only for HR. A key anywhere in an employee response is a leak.
HR_ONLY_KEYS = ("hr_flags", "enrollment_state", "hr_summary", "history", "handoff", "fmla_precheck",
                "review_revision", "review_fingerprint", "ai_stale", "decision", "reviewed_revision")
# Text that only appears in HR-side material for these demo people.
HR_ONLY_TEXT = ("under the 30-hour", "needs_hr_exception", "Does not meet the FMLA basics", "FMLA basics")


def keys_of(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from keys_of(v)
    elif isinstance(value, list):
        for v in value:
            yield from keys_of(v)


def answer_for(request):
    return {
        "submit_enrollment_guidance": {"employee_message": "Here is your checklist.", "hr_summary": "HR summary."},
        "submit_enrollment_answer": {"answer": "Here is the answer.", "evidence_refs": [], "policy_refs": [],
                                     "follow_up_question": "", "unresolved": []},
        "submit_consideration": {"explanation": "That choice costs this much.", "evidence_refs": [], "policy_refs": []},
        "submit_leave_summary": {"employee_message": "We received it.", "hr_summary": "HR leave summary."},
        "submit_leave_intake": {"suggested_type": "personal", "reason": "Personal time", "question": "",
                                "policy_refs": []},
        "submit_leave_clarification": {"message": "Thanks.", "question": "", "policy_refs": []},
    }.get(submit_name(request), {})


def client():
    return ScriptedClient(lambda request, results: read_all_then(request, results, answer_for(request)))


class EmployeeResponsesAreFree(unittest.TestCase):
    def setUp(self):
        self.store = CaseStore(client=client())
        self.seen = []

    def call(self, path, **body):
        out = handle(self.store, path, body)
        if path.startswith("/api/employee/"):      # HR endpoints may return HR data; only employees are checked
            self.seen.append((path, out))
        return out

    def assert_clean(self):
        for path, out in self.seen:
            blob = json.dumps(out)
            leaked = {k for k in keys_of(out) if k in HR_ONLY_KEYS}
            self.assertFalse(leaked, f"{path} exposes HR-only keys {leaked}")
            for text in HR_ONLY_TEXT:
                self.assertNotIn(text, blob, f"{path} exposes HR-only text {text!r}")

    def test_every_enrollment_response_for_an_employee_with_an_hr_flag(self):
        eid = "E2003"   # 20 hours/week: an HR-only eligibility flag
        self.call("/api/employee/overview", employee_id=eid)
        self.call("/api/employee/enrollment", employee_id=eid)
        self.call("/api/employee/enrollment/help", employee_id=eid, question="Am I eligible?")
        self.call("/api/employee/enrollment/consider", employee_id=eid, benefit="medical", status="elected",
                  plan="Silver PPO", tier="employee")
        self.call("/api/employee/enrollment/elect", employee_id=eid, benefit="medical", status="elected",
                  plan="Silver PPO", tier="employee")
        self.call("/api/employee/enrollment/dependent/add", employee_id=eid, relationship="spouse", name="Spouse")
        self.call("/api/employee/enrollment/dependent/upload", employee_id=eid, relationship="spouse", name="Spouse")
        self.call("/api/employee/cases", employee_id=eid)
        self.call("/api/employee/overview", employee_id=eid)
        self.assert_clean()
        # ...while the HR queue, which only HR uses, still has the flag
        queue = json.dumps(self.call("/api/hr/queue"))
        self.assertIn("hr_flags", queue)

    def test_the_reported_elect_endpoint_no_longer_returns_hr_flags(self):
        out = self.call("/api/employee/enrollment/elect", employee_id="E2003", benefit="dental", status="waived")
        self.assertNotIn("hr_flags", out["enrollment"])
        self.assertEqual(set(out["enrollment"]), {"name", "deadline", "days_left", "done", "missing", "notes", "as_of"})

    def test_leave_responses_and_decided_cases_stay_clean(self):
        eid = "E1003"   # does not meet the FMLA basics: an HR-only pre-check
        self.call("/api/employee/overview", employee_id=eid)
        self.call("/api/employee/leave/intake", employee_id=eid, description="I need a few days off")
        draft = self.call("/api/employee/leave/draft", employee_id=eid, leave_type="personal",
                          start_date="2026-11-09", end_date="2026-11-10", schedule="continuous", reason="Personal")
        self.call("/api/employee/leave/confirm", employee_id=eid, draft_id=draft["draft"]["id"], confirmed=True)
        self.call("/api/employee/leave", employee_id=eid, leave_type="personal", start_date="2026-12-01",
                  end_date="2026-12-02")
        case_id = next(c["id"] for c in self.call("/api/employee/cases", employee_id=eid)["cases"])
        self.call("/api/hr/decide", case_id=case_id, decision="request_info", reason="Please add a date range")
        self.call("/api/employee/cases", employee_id=eid)
        self.call("/api/employee/overview", employee_id=eid)
        # the last two responses are the employee views after HR acted
        self.assert_clean()

    def test_enrollment_agent_that_copies_a_flag_into_the_employee_message_is_filtered(self):
        flag = checks_flag("E2003")
        leaky = ScriptedClient(lambda request, results: read_all_then(
            request, results,
            {"employee_message": f"Heads up: {flag}", "hr_summary": "HR summary."}))
        out = agents.run_enrollment_agent("E2003", client=leaky)
        self.assertEqual(out["ai"]["employee_message"], agents.GENERIC_HR_REVIEW_NOTE)
        self.assertTrue(out["ai"]["employee_message_filtered"])
        self.assertEqual(out["ai"]["hr_summary"], "HR summary.")       # HR still gets its own summary

    def test_a_clean_employee_message_is_left_alone(self):
        out = agents.run_enrollment_agent("E2003", client=client())
        self.assertEqual(out["ai"]["employee_message"], "Here is your checklist.")
        self.assertNotIn("employee_message_filtered", out["ai"])

    def test_the_agent_prompt_forbids_quoting_flags(self):
        self.assertIn("never quote, paraphrase or hint at a flag", agents.ENROLLMENT_PROMPT)


def checks_flag(employee_id):
    from benefits_leave import checks
    return checks.enrollment_status(employee_id)["hr_flags"][0]


if __name__ == "__main__":
    unittest.main()
