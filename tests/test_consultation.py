"""T05: bounded Vendor-to-Enrollment consultation routed by workflow code."""

import unittest

from benefits_leave.web import employee_view, handle
from benefits_leave.workflow import CaseStore
from tests.scripted_client import ScriptedClient, read_all_then, submit_name, tool_use

SPECIALIST_ANSWER = {
    "status": "answered",
    "finding": "HR approved Silver PPO, employee-only. No dependents or proof are on record, so a family tier "
               "is not supported ($230.00 vs $78.00 per paycheck).",
    "evidence_refs": ["C1:approved:1/records/medical", "DEMO-VENDOR-SOURCE-OF-TRUTH@v1", "EV-NOT-REAL"],
    "unknowns": ["Whether the carrier processed a later change"],
    "proposed_next_action": "Ask Acme Health to correct the tier to employee-only",
}


def collaboration(consults=(("approved_enrollment_intent", "medical"),), specialist_fails=False):
    """Vendor reads, consults as listed, then drafts using the specialist's reply."""
    def script(request, results):
        name = submit_name(request)
        if name == "submit_specialist_finding":
            if specialist_fails:
                raise ConnectionError("specialist offline")
            return read_all_then(request, results, SPECIALIST_ANSWER)
        if name != "submit_vendor_summary":
            return read_all_then(request, results, {})
        reads = ["get_handoff", "get_vendor_confirmations", "get_vendor_policy"]
        if not all(r in results for r in reads):
            return [tool_use(r) for r in reads]
        if "consult_enrollment_specialist" not in results and consults:
            return [tool_use("consult_enrollment_specialist", {"question_type": qt, "benefit": b,
                                                               "question": "What tier did HR approve?"}, f"c{i}")
                    for i, (qt, b) in enumerate(consults)]
        reply = results.get("consult_enrollment_specialist") or {}
        refs = reply.get("evidence_refs", []) if isinstance(reply, dict) else []
        return [tool_use("submit_vendor_summary", {
            "hr_summary": f"Specialist: {reply.get('finding') if isinstance(reply, dict) else 'n/a'}",
            "follow_ups": [{"vendor": "Acme Health (medical carrier)", "issue": "tier mismatch",
                            "draft_message": f"Please correct the tier. {reply.get('finding') if isinstance(reply, dict) else ''}",
                            "evidence_refs": refs}]})]
    return script


class Consultation(unittest.TestCase):
    def run_c1(self, **kwargs):
        client = ScriptedClient(collaboration(**kwargs))
        store = CaseStore(client=client)
        case = store.check_vendor_confirmations("C1")
        return store, client, case

    def test_e2004_consultation_changes_the_final_draft(self):
        store, client, case = self.run_c1()
        consultation = case["consultations"][0]
        self.assertEqual(consultation["approved_snapshot_ref"], "C1:approved:1")
        self.assertEqual(consultation["employee_id"], "E2004")
        self.assertEqual(consultation["reply"]["status"], "answered")
        self.assertEqual(consultation["reply"]["evidence_refs"],
                         ["C1:approved:1/records/medical", "DEMO-VENDOR-SOURCE-OF-TRUTH@v1"])  # invented ref dropped
        draft = next(f for f in case["vendor"]["follow_ups"] if f["vendor"].startswith("Acme"))
        self.assertIn("employee-only", draft["draft_message"])
        self.assertIn("C1:approved:1/records/medical", draft["evidence_refs"])
        self.assertIn("employee-only", case["vendor"]["ai"]["hr_summary"])
        self.assertEqual(case["vendor"]["consultations"], case["consultations"])
        self.assertEqual(case["status"], "vendor_follow_up")

    def test_specialist_sees_frozen_record_costs_and_dependents_only(self):
        store, client, _ = self.run_c1()
        specialist = client.runs_for("submit_specialist_finding")
        self.assertTrue(specialist)
        tool_names = [t["name"] for t in specialist[0]["tools"]]
        self.assertNotIn("consult_enrollment_specialist", tool_names)        # no recursion
        seen = " ".join(str(m["content"]) for m in specialist[-1]["messages"])
        self.assertIn('"tier": "employee"', seen)
        self.assertIn('"family": 230.0', seen)
        self.assertIn('"dependents_on_record": []', seen)

    def test_budget_allows_one_consultation_per_run(self):
        store, client, case = self.run_c1(consults=(("approved_enrollment_intent", "medical"),
                                                    ("approved_enrollment_intent", "dental")))
        statuses = [c["reply"]["status"] for c in case["consultations"]]
        self.assertEqual(statuses, ["answered", "unavailable"])
        self.assertIn("budget", case["consultations"][1]["reply"]["unknowns"][0])
        self.assertGreater(case["consultations"][0]["model_calls"], 0)
        self.assertEqual(case["consultations"][1]["model_calls"], 0)       # no second specialist run

    def test_rechecking_gets_a_fresh_budget_and_keeps_history(self):
        store, client, case = self.run_c1()
        store.check_vendor_confirmations("C1")
        self.assertEqual([c["request_id"] for c in case["consultations"]], ["CONSULT-C1-1", "CONSULT-C1-2"])
        self.assertEqual(len(case["vendor"]["consultations"]), 1)

    def test_out_of_scope_requests_are_rejected_without_a_specialist_run(self):
        for consults in ((("approved_enrollment_intent", "life"),), (("current_elections", "medical"),)):
            store, client, case = self.run_c1(consults=consults)
            self.assertEqual(case["consultations"][0]["reply"]["status"], "unavailable")
            self.assertEqual(client.runs_for("submit_specialist_finding"), [])

    def test_specialist_failure_is_an_explicit_unknown(self):
        store, client, case = self.run_c1(specialist_fails=True)
        reply = case["consultations"][0]["reply"]
        self.assertEqual(reply["status"], "unavailable")
        self.assertIn("could not answer", reply["unknowns"][0])
        self.assertEqual(case["status"], "vendor_follow_up")
        self.assertEqual(len(case["vendor"]["follow_ups"]), 2)   # medical discrepancy + dental pending

    def test_snapshot_not_current_elections(self):
        client = ScriptedClient(collaboration())
        store = CaseStore(client=client)
        store.data["new_hires"]["E2004"]["elections"]["medical"]["tier"] = "family"   # edited after approval
        store.check_vendor_confirmations("C1")
        seen = " ".join(str(m["content"]) for m in client.runs_for("submit_specialist_finding")[-1]["messages"])
        self.assertIn('"tier": "employee"', seen)

    def test_activity_shows_question_and_answer_for_hr_only(self):
        store, _, case = self.run_c1()
        actors = [(a["actor"], a["action"]) for a in case["activity"]]
        self.assertIn(("vendor_agent", "Asked the Enrollment Agent about the approved medical intent"), actors)
        self.assertIn(("enrollment_agent", "Answered the Vendor Agent"), actors)
        view = employee_view(case)
        self.assertNotIn("consultations", view)
        self.assertFalse(any("Vendor Agent" in a["action"] for a in view["activity"]))
        self.assertNotIn("Acme", str(handle(store, "/api/employee/cases", {"employee_id": "E2004"})))

    def test_model_work_is_bounded_and_recorded(self):
        _, client, case = self.run_c1()
        self.assertLessEqual(len(client.runs_for("submit_vendor_summary")), 6)
        self.assertLessEqual(case["consultations"][0]["model_calls"], 4)

    def test_no_consultation_flagged_when_agent_skips_it(self):
        _, _, case = self.run_c1(consults=())
        self.assertEqual(case.get("consultations", []), [])
        vendor_step = [a for a in case["activity"] if a["actor"] == "vendor_agent"][-1]
        self.assertIn("did not consult", vendor_step["unknowns"][0])


if __name__ == "__main__":
    unittest.main()
