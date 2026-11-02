"""The realistic demo people behave as docs/FUNCTIONAL-TEST-GUIDE.md says they do, and the demo can be reset.

These use deterministic checks and the scripted (offline) model: no API key, no live AI.
"""
import unittest
from unittest import mock

from benefits_leave import checks
from benefits_leave.web import employee_overview, handle
from benefits_leave.workflow import CaseStore, WorkflowError
from tests.test_privacy import client


def new_store():
    return CaseStore(client=client())


def walk_to_vendor_check(store, employee_id, reason=""):
    _, case = store.check_enrollment(employee_id)
    store.hr_decide(case["id"], "approve", reason)
    store.prepare_vendor_records(case["id"])
    store.mark_sent(case["id"])
    return store.check_vendor_confirmations(case["id"])


class NewHires(unittest.TestCase):
    def test_e2007_aisha_complete_and_fully_confirmed_by_every_vendor(self):
        self.assertEqual(checks.enrollment_status("E2007")["enrollment_state"], "complete")
        case = walk_to_vendor_check(new_store(), "E2007")
        self.assertEqual(case["status"], "vendor_confirmed")
        self.assertEqual({r["benefit"] for r in case["handoff"]["records"]},
                         {"medical", "dental", "vision", "retirement"})
        self.assertIn("confirmed by every vendor", case["employee_update"])

    def test_e2008_tomas_family_with_mixed_document_states(self):
        store = new_store()
        states = {(e["dependent"], e["state"]) for e in checks.evidence_status("E2008", store.data)}
        self.assertEqual(states, {("Camila Ferreira", "verified"), ("Mateo Ferreira", "received"),
                                  ("Lucia Ferreira", "absent")})
        _, case = store.check_enrollment("E2008")
        self.assertEqual(case["status"], "incomplete")
        self.assertEqual(sorted(case["enrollment"]["missing"]),
                         ["Upload birth certificate for Lucia Ferreira", "Upload birth certificate for Mateo Ferreira"])
        self.assertTrue(any("below the 4%" in n for n in case["enrollment"]["notes"]))
        with self.assertRaises(WorkflowError):
            store.hr_decide(case["id"], "approve")
        # HR verifies the received certificate; the absent one still blocks approval
        store.hr_verify_document(case["id"], "EV-E2008-02")
        self.assertEqual(case["enrollment"]["missing"], ["Upload birth certificate for Lucia Ferreira"])
        with self.assertRaises(WorkflowError):
            store.hr_decide(case["id"], "approve")
        summary = store.enrollment_cost_summary("E2008")
        self.assertGreater(summary["employee_per_paycheck"], 0)
        self.assertGreater(summary["employer_per_paycheck"], 0)

    def test_e2009_chloe_part_time_needs_a_reasoned_exception(self):
        store = new_store()
        status = checks.enrollment_status("E2009")
        self.assertEqual(status["enrollment_state"], "needs_hr_exception")
        self.assertTrue(any("24 hours/week is under the 30-hour" in f for f in status["hr_flags"]))
        self.assertEqual(status["missing"], [])
        _, case = store.check_enrollment("E2009")
        with self.assertRaises(WorkflowError):
            store.hr_decide(case["id"], "approve")                       # a flag needs a reason
        self.assertEqual(store.hr_decide(case["id"], "approve", "Documented variable-hour exception")["status"], "approved")

    def test_e2010_jamal_missed_the_enrollment_window(self):
        status = checks.enrollment_status("E2010")
        self.assertEqual(status["deadline"], "2026-10-22")
        self.assertEqual(status["days_left"], -4)
        self.assertIn("Enrollment deadline passed on 2026-10-22", status["hr_flags"])
        self.assertEqual(len(status["missing"]), 2)                      # dental and retirement still open
        store = new_store()
        _, case = store.check_enrollment("E2010")
        self.assertEqual(case["status"], "incomplete")
        with self.assertRaises(WorkflowError):
            store.hr_decide(case["id"], "approve", "Late, but approve anyway")
        self.assertEqual(store.hr_decide(case["id"], "request_info", "Please choose dental and retirement")["status"],
                         "info_requested")

    def test_e2011_elif_starts_from_nothing_and_can_finish_by_electing(self):
        status = checks.enrollment_status("E2011")
        self.assertEqual((status["days_left"], len(status["missing"])), (30, 4))
        store = new_store()
        store.set_election("E2011", "medical", {"status": "elected", "plan": "Silver PPO", "tier": "employee"})
        store.set_election("E2011", "dental", {"status": "waived"})
        store.set_election("E2011", "vision", {"status": "waived"})
        store.set_election("E2011", "retirement", {"status": "elected", "percent": 4})
        _, case = store.check_enrollment("E2011")
        self.assertEqual(case["status"], "ready_for_hr_review")
        self.assertEqual(case["enrollment"]["missing"], [])

    def test_e2012_rosa_approved_then_two_carrier_discrepancies_and_a_missing_confirmation(self):
        case = walk_to_vendor_check(new_store(), "E2012")
        self.assertEqual(case["status"], "vendor_follow_up")
        results = {r["benefit"]: r["result"] for r in case["vendor"]["reconciliation"]}
        self.assertEqual(results, {"medical": "confirmed", "dental": "no_confirmation",
                                   "vision": "discrepancy", "retirement": "discrepancy"})
        self.assertEqual(len(case["vendor"]["follow_ups"]), 3)           # one draft for every open issue

    def test_the_new_people_appear_in_the_employee_pickers_without_changing_the_old_ones(self):
        people = {p["id"]: p for p in handle(new_store(), "/api/people", {})["people"]}
        for new_hire in ("E2007", "E2008", "E2009", "E2010", "E2011", "E2012"):
            self.assertEqual(people[new_hire]["kind"], "new hire")
        for employee in ("E1006", "E1007", "E1008", "E1009"):
            self.assertEqual(people[employee]["kind"], "current employee")
        self.assertEqual(people["E2001"]["name"], "Priya Nair")           # the original rehearsal records are intact
        self.assertEqual(people["E1001"]["name"], "Elena Rossi")


class CurrentEmployees(unittest.TestCase):
    def check(self, employee_id):
        request = {"employee_id": employee_id, "leave_type": "personal", "start_date": "2026-11-09",
                   "end_date": "2026-11-10", "documents_attached": []}
        return checks.leave_request_check(request, checks.load_data())["fmla_precheck"]

    def test_e1006_hannah_clearly_meets_the_fmla_basics(self):
        self.assertEqual(self.check("E1006")["status"], "meets_basics")

    def test_e1007_mateo_is_short_on_both_service_and_hours(self):
        fmla = self.check("E1007")
        self.assertEqual((fmla["status"], fmla["months_of_service"], fmla["hours_worked_12mo"]),
                         ("does_not_meet_basics", 11, 1180))
        self.assertIn("state leave and company policy", fmla["detail"])      # not a denial of every option

    def test_e1008_grace_misses_only_the_hours_test_by_ten(self):
        fmla = self.check("E1008")
        self.assertEqual((fmla["status"], fmla["months_of_service"], fmla["hours_worked_12mo"]),
                         ("does_not_meet_basics", 30, 1240))

    def test_e1009_ibrahim_has_a_real_zero_pto_balance_not_an_unknown_one(self):
        balance = employee_overview(new_store(), "E1009")["leave_balance"]
        self.assertEqual(balance["status"], "ok")
        self.assertEqual(balance["balances"], {"pto": 0, "sick": 80, "personal": 12})
        unknown = employee_overview(new_store(), "E1005")["leave_balance"]      # missing data stays "cannot determine"
        self.assertEqual(unknown["status"], "cannot_determine")


class ResetDemo(unittest.TestCase):
    def test_reset_forgets_cases_drafts_edits_and_chat(self):
        store = new_store()
        store.check_enrollment("E2002")
        store.set_election("E2011", "dental", {"status": "waived"})
        store.add_dependent("E2011", "spouse", "Someone")
        draft = handle(store, "/api/employee/leave/draft", {"employee_id": "E1001", "leave_type": "personal",
                                                            "start_date": "2026-11-09", "end_date": "2026-11-10",
                                                            "schedule": "continuous"})["draft"]
        store.help_threads["E2002"] = [{"question": "q"}]
        self.assertGreater(len(store.cases), 1)
        out = handle(store, "/api/demo/reset", {})["reset"]
        self.assertEqual(out["cases"], 1)                                       # only the seeded demo case remains
        self.assertEqual(list(store.cases), ["C1"])
        self.assertEqual(store.drafts, {})
        self.assertEqual(store.help_threads, {})
        self.assertEqual(store.data["new_hires"]["E2011"]["elections"]["dental"], {"status": "not_started"})
        self.assertEqual(store.data["new_hires"]["E2011"]["dependents"], [])
        self.assertIsNotNone(draft)

    def test_case_numbers_start_again_after_a_reset(self):
        store = new_store()
        store.check_enrollment("E2002")
        store.reset()
        _, case = store.check_enrollment("E2002")
        self.assertEqual(case["id"], "C2")

    def test_reset_rereads_the_data_files_so_edits_take_effect_without_a_restart(self):
        store = new_store()
        edited = checks.load_data()
        edited["new_hires"]["E2011"]["name"] = "Elif Demir-Yilmaz"          # a tester edits the JSON file
        edited["new_hires"]["E2011"]["weekly_hours"] = 20
        with mock.patch("benefits_leave.checks.load_data", return_value=edited):
            store.reset()
        self.assertEqual(store.data["new_hires"]["E2011"]["name"], "Elif Demir-Yilmaz")
        store.set_election("E2011", "medical", {"status": "elected", "plan": "Silver PPO", "tier": "employee"})
        flags = checks.enrollment_status("E2011", store.data)["hr_flags"]
        self.assertTrue(any("20 hours/week is under the 30-hour" in f for f in flags), flags)   # the edit is live

    def test_a_reset_keeps_the_ai_client_and_time_budget_settings(self):
        store = new_store()
        marker = object()
        store.new_budget = marker
        store.reset()
        self.assertIs(store.new_budget, marker)
        self.assertIsNotNone(store.client)

    def test_reset_of_a_store_built_from_given_data_returns_to_that_data(self):
        data = checks.load_data()
        store = CaseStore(data=data, client=client())
        store.set_election("E2011", "dental", {"status": "waived"})
        store.reset()
        self.assertEqual(store.data["new_hires"]["E2011"]["elections"]["dental"], {"status": "not_started"})


if __name__ == "__main__":
    unittest.main()
