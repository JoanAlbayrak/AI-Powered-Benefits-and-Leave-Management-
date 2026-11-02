"""Task 4: agent advice rests on approved policy, and every user action has a shared time budget."""
import re
import unittest
from pathlib import Path

from benefits_leave import agents, checks, runner
from benefits_leave.web import handle
from benefits_leave.workflow import CaseStore
from tests.scripted_client import ScriptedClient, read_all_then, submit_name, tool_use
from tests.test_consultation import collaboration
from tests.test_leave_journey import intake_answer, intake_script

ROOT = Path(__file__).resolve().parent.parent


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class SlowClient(ScriptedClient):
    """Every model call takes `seconds` of (fake) time, and records the per-attempt timeout it was given."""

    def __init__(self, script, clock, seconds):
        super().__init__(script)
        self.clock, self.seconds, self.timeouts = clock, seconds, []

    def _create(self, **kwargs):
        self.timeouts.append(kwargs.get("timeout"))
        response = super()._create(**kwargs)
        self.clock.now += self.seconds
        return response


class ConsiderIsGrounded(unittest.TestCase):
    def test_the_consider_agent_can_read_the_approved_policy(self):
        seen = {}

        def script(request, results):
            return read_all_then(request, results, lambda r: seen.update(r) or
                                 {"explanation": "ok", "evidence_refs": [], "policy_refs": ["DEMO-ENR-ELIGIBILITY@v1"]})
        store = CaseStore(client=ScriptedClient(script))
        out = handle(store, "/api/employee/enrollment/consider",
                     {"employee_id": "E2003", "benefit": "dental", "status": "elected", "plan": "Basic Dental", "tier": "employee"})
        self.assertIn("get_enrollment_policy", seen)                         # it used to receive none
        refs = {entry["ref"] for entry in seen["get_enrollment_policy"]}
        self.assertIn("DEMO-ENR-DEPENDENT-PROOF@v1", refs)
        self.assertEqual(out["policy_refs"], ["DEMO-ENR-ELIGIBILITY@v1"])
        self.assertIn("only if get_enrollment_policy gives it to you", agents.CONSIDER_PROMPT)


class LeaveIntakeIsGrounded(unittest.TestCase):
    def intake(self, answer):
        seen = {}

        def script(request, results):
            return read_all_then(request, results, lambda r: seen.update(r) or answer)
        store = CaseStore(client=ScriptedClient(script))
        return store.intake_leave("E1001", "I need surgery and will be out a while"), seen

    def test_the_agent_receives_policy_content_not_just_ids(self):
        _, seen = self.intake(intake_answer())
        entries = {e["ref"]: e for e in seen["get_approved_leave_policy"]}
        self.assertIn("DEMO-LEAVE-BALANCES@v1", entries)
        self.assertIn("sick balance first", entries["DEMO-LEAVE-BALANCES@v1"]["text"])
        self.assertFalse([r for r in entries if "FMLA" in r], "the intake agent must not be handed FMLA policy")

    def test_the_prompt_no_longer_invents_a_generic_sick_vs_pto_rule(self):
        self.assertNotIn("preserves their pto", agents.LEAVE_INTAKE_PROMPT)
        self.assertIn("using only get_approved_leave_policy", agents.LEAVE_INTAKE_PROMPT)

    def test_a_balance_claim_with_no_policy_citation_is_replaced(self):
        answer = {**intake_answer(), "balance_note": "Use PTO and save your sick days.",
                  "policy_refs": ["DEMO-LEAVE-DOCUMENTS@v1"]}
        out, _ = self.intake(answer)
        self.assertEqual(out["balance_note"], agents.BALANCE_FALLBACK_NOTE)

    def test_a_balance_claim_that_cites_the_balances_policy_is_kept(self):
        out, _ = self.intake(intake_answer())
        self.assertIn("sick balance", out["balance_note"])
        self.assertIn("DEMO-LEAVE-BALANCES@v1", out["policy_refs"])

    def test_a_citation_that_is_not_in_the_policy_does_not_count(self):
        answer = {**intake_answer(), "policy_refs": ["DEMO-LEAVE-BALANCES@v9"]}     # a version that doesn't exist
        out, _ = self.intake(answer)
        self.assertEqual(out["balance_note"], agents.BALANCE_FALLBACK_NOTE)

    def test_required_documents_come_from_the_policy_table(self):
        answer = {**intake_answer(), "documents_likely_needed": ["a passport", "a notarized letter"]}
        out, _ = self.intake(answer)
        self.assertEqual(out["documents_likely_needed"], ["medical certification"])

    def test_the_balances_policy_is_an_approved_synthetic_entry(self):
        entry = next(e for e in checks.policy_entries("leave") if e["id"] == "DEMO-LEAVE-BALANCES")
        self.assertEqual(entry["source"], "Synthetic demo employer policy")


class VestingComesFromData(unittest.TestCase):
    def setUp(self):
        self.store = CaseStore()

    def test_the_summary_states_the_plans_vesting_note_and_cites_the_policy(self):
        summary = self.store.enrollment_cost_summary("E2002")           # elects a 4% retirement contribution
        data_note = self.store.data["retirement_plan"]["vesting_schedule"]["note"]
        self.assertEqual(summary["retirement_vesting"], {"text": data_note, "ref": "DEMO-401K-VESTING@v1"})
        self.assertNotIn("vests", summary["retirement_employer_match"])

    def test_it_is_not_hardcoded(self):
        self.store.data["retirement_plan"]["vesting_schedule"]["note"] = "Vesting is immediate under this plan."
        self.assertEqual(self.store.enrollment_cost_summary("E2002")["retirement_vesting"]["text"],
                         "Vesting is immediate under this plan.")

    def test_no_vesting_data_means_no_vesting_claim(self):
        del self.store.data["retirement_plan"]["vesting_schedule"]
        self.assertIsNone(self.store.enrollment_cost_summary("E2002")["retirement_vesting"])

    def test_no_claim_without_a_retirement_election(self):
        self.assertIsNone(self.store.enrollment_cost_summary("E2001")["retirement_vesting"])


class TimeBudgetBoundsExecution(unittest.TestCase):
    def test_the_budget_counts_down(self):
        clock = FakeClock()
        budget = runner.TimeBudget(90, clock)
        self.assertEqual(budget.remaining(), 90)
        clock.now += 60
        self.assertEqual(budget.remaining(), 30)
        self.assertFalse(budget.expired())
        clock.now += 40
        self.assertEqual(budget.remaining(), 0)
        self.assertTrue(budget.expired())

    def test_an_agent_stops_when_the_budget_is_spent_even_with_turns_left(self):
        clock = FakeClock()
        client = SlowClient(lambda request, results: [tool_use("get_x", id_=f"t{len(results)}{id(request)}")], clock, 40)
        out = runner.run("system", "go", [runner.read_tool("get_x", "reads x")], {"get_x": lambda: {}},
                         runner.submit_tool("submit_y", "submits", {}), client=client,
                         budget=runner.TimeBudget(90, clock))
        self.assertEqual(out["stop_reason"], "time_budget")
        self.assertEqual(out["model_calls"], 3)                      # not the 6 the turn limit would allow
        self.assertIsNone(out["answer"])

    def test_each_attempt_is_limited_to_its_share_so_retries_cannot_overrun(self):
        clock = FakeClock()
        client = SlowClient(lambda request, results: read_all_then(request, results, {}), clock, 1)
        config = runner.settings()
        runner.run("s", "go", [], {}, runner.submit_tool("submit_y", "x", {}), client=client,
                   budget=runner.TimeBudget(90, clock))
        limit = min(config["timeout_seconds"], 90 / (config["max_retries"] + 1))
        self.assertLessEqual(client.timeouts[0], limit)

    def test_an_expired_budget_means_no_model_call_at_all(self):
        clock = FakeClock()
        budget = runner.TimeBudget(10, clock)
        clock.now += 20
        client = SlowClient(lambda request, results: [], clock, 1)
        out = runner.run("s", "go", [], {}, runner.submit_tool("submit_y", "x", {}), client=client, budget=budget)
        self.assertEqual((out["stop_reason"], out["model_calls"], client.requests), ("time_budget", 0, []))

    def test_a_timed_out_agent_reports_a_clear_recoverable_message(self):
        clock = FakeClock()
        budget = runner.TimeBudget(10, clock)
        clock.now += 20
        out = agents.run_enrollment_agent("E2002", client=SlowClient(lambda r, s: [], clock, 1), budget=budget)
        self.assertIsNone(out["ai"])
        self.assertIn("time budget", out["ai_error"])
        self.assertIn("try again", out["ai_error"])
        self.assertEqual(out["status"]["enrollment_state"], "complete")          # the checks still stand

    def test_the_specialist_shares_the_vendor_runs_budget(self):
        clock = FakeClock()
        client = SlowClient(collaboration(), clock, 50)               # each model call "takes" 50 s of a 90 s budget
        store = CaseStore(client=client)
        store.new_budget = lambda: runner.TimeBudget(90, clock)
        case = store.check_vendor_confirmations("C1")
        # The vendor's first model call ends at t+50 and its second at t+100: nothing is left for a specialist.
        self.assertEqual(client.runs_for("submit_specialist_finding"), [])
        self.assertEqual(case["consultations"][0]["reply"]["status"], "unavailable")
        self.assertIn("time budget", case["consultations"][0]["reply"]["unknowns"][0])
        # HR still gets the comparison and a draft for every issue, and a clear message about the AI.
        self.assertEqual(case["status"], "vendor_follow_up")
        self.assertTrue(case["vendor"]["follow_ups"])
        self.assertIn("time budget", case["vendor"]["ai_error"])

    def test_a_specialist_is_not_started_with_only_a_few_seconds_left(self):
        clock = FakeClock()
        client = SlowClient(collaboration(), clock, 43)               # the vendor's two calls leave 4 s of 90
        store = CaseStore(client=client)
        store.new_budget = lambda: runner.TimeBudget(90, clock)
        case = store.check_vendor_confirmations("C1")
        self.assertEqual(client.runs_for("submit_specialist_finding"), [])       # 4 s is under MIN_CONSULT_SECONDS
        self.assertEqual(case["consultations"][0]["reply"]["status"], "unavailable")

    def test_with_time_left_the_specialist_still_runs(self):
        clock = FakeClock()
        client = SlowClient(collaboration(), clock, 5)
        store = CaseStore(client=client)
        store.new_budget = lambda: runner.TimeBudget(90, clock)
        case = store.check_vendor_confirmations("C1")
        self.assertTrue(client.runs_for("submit_specialist_finding"))
        self.assertEqual(case["consultations"][0]["reply"]["status"], "answered")

    def test_the_action_budget_is_shorter_than_the_pages_action_timeout(self):
        js = (ROOT / "benefits_leave" / "frontend" / "js" / "api.js").read_text()
        page_timeout = int(re.search(r"mutation \? (\d+)", js).group(1)) / 1000
        self.assertLess(runner.settings()["action_budget_seconds"], page_timeout)
        self.assertLess(110, page_timeout)                                       # the largest value the setting allows

    def test_out_of_range_settings_are_ignored_with_a_note(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"ANTHROPIC_ACTION_BUDGET_SECONDS": "500"}):
            config = runner.settings()
        self.assertEqual(config["action_budget_seconds"], 90.0)
        self.assertTrue(any("ANTHROPIC_ACTION_BUDGET_SECONDS" in p for p in config["problems"]))

    def test_readiness_reports_the_budget(self):
        self.assertIn("action_budget_seconds", runner.readiness())


if __name__ == "__main__":
    unittest.main()
