"""T02: local AI configuration and readiness. No network or real key is used."""

import os
import unittest
from types import SimpleNamespace as NS
from unittest import mock

from benefits_leave import agents, readiness, runner
from benefits_leave.web import handle
from benefits_leave.workflow import CaseStore

SECRET = "sk-ant-test-secret-value"


def env(**values):
    """Patch the environment and skip the developer's real .env file."""
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("ANTHROPIC_", "BENEFITS_AI"))}
    clean.update(values)
    return mock.patch.multiple(os, environ=clean), mock.patch.object(runner, "ENV_FILE", runner.ENV_FILE.with_name("missing.env"))


class Recorder:
    def __init__(self, submit_input=None):
        self.requests = []
        self.messages = NS(create=self._create)
        self.submit_input = submit_input or {"ok": True}

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        submit = kwargs["tools"][-1]["name"]
        return NS(stop_reason="tool_use", content=[NS(type="tool_use", id="s", name=submit, input=self.submit_input)])


class Settings(unittest.TestCase):
    def setUp(self):
        for patch in env():
            patch.start()
            self.addCleanup(patch.stop)

    def test_defaults(self):
        s = runner.settings()
        self.assertEqual((s["model"], s["effort"], s["timeout_seconds"], s["max_retries"]),
                         ("claude-opus-5-5", "medium", 60.0, 2))
        self.assertEqual(s["problems"], [])

    def test_overrides_and_invalid_values(self):
        os.environ.update(ANTHROPIC_MODEL="claude-sonnet-5-5", ANTHROPIC_EFFORT="none",
                          ANTHROPIC_TIMEOUT_SECONDS="abc", ANTHROPIC_MAX_RETRIES="99")
        s = runner.settings()
        self.assertEqual(s["model"], "claude-sonnet-5-5")
        self.assertIsNone(s["effort"])
        self.assertEqual((s["timeout_seconds"], s["max_retries"]), (60.0, 2))
        self.assertEqual(len(s["problems"]), 2)

    def test_placeholder_key_is_not_configured(self):
        os.environ["ANTHROPIC_API_KEY"] = "your-anthropic-api-key-here"
        status = runner.readiness()
        self.assertFalse(status["key_configured"])
        self.assertFalse(status["ready"])
        self.assertTrue(any("API key" in p for p in status["problems"]))

    def test_readiness_never_returns_the_key_or_calls_a_model(self):
        os.environ["ANTHROPIC_API_KEY"] = SECRET
        with mock.patch.object(runner, "make_client", side_effect=AssertionError("no model call")):
            status = runner.readiness()
            response = handle(CaseStore(client=Recorder()), "/api/ai/status", {})
        self.assertTrue(status["key_configured"])
        self.assertNotIn(SECRET, repr(status) + repr(response))

    def test_disabled_ai_uses_deterministic_results(self):
        os.environ.update(ANTHROPIC_API_KEY=SECRET, BENEFITS_AI_DISABLED="1")
        result = agents.run_enrollment_agent("E2001")
        self.assertIsNone(result["ai"])
        self.assertIn("turned off", result["ai_error"])
        self.assertTrue(result["status"]["missing"])

    def test_missing_key_message_is_actionable(self):
        result = agents.run_enrollment_agent("E2002")
        self.assertIn("ANTHROPIC_API_KEY", result["ai_error"])
        self.assertEqual(result["status"]["enrollment_state"], "complete")


class Requests(unittest.TestCase):
    def setUp(self):
        for patch in env(ANTHROPIC_MODEL="claude-test-model", ANTHROPIC_EFFORT="low"):
            patch.start()
            self.addCleanup(patch.stop)

    def test_uses_standard_messages_api_with_configured_model(self):
        client = Recorder()
        outcome = runner.run("system", "hi", [], {}, runner.submit_tool("submit_check", "d", {"ok": {"type": "boolean"}}),
                             client=client)
        request = client.requests[0]
        self.assertEqual(outcome["answer"], {"ok": True})
        self.assertEqual(request["model"], "claude-test-model")
        self.assertEqual(request["output_config"], {"effort": "low"})
        self.assertNotIn("betas", request)
        self.assertNotIn("fallbacks", request)

    def test_tool_inputs_are_passed_and_failures_reported(self):
        seen = []

        class TwoStep(Recorder):
            def _create(self, **kwargs):
                self.requests.append(kwargs)
                if len(kwargs["messages"]) == 1:
                    return NS(stop_reason="tool_use", content=[
                        NS(type="tool_use", id="a", name="echo", input={"text": "x"}),
                        NS(type="tool_use", id="b", name="boom", input={})])
                return super()._create(**kwargs)

        client = TwoStep()
        runner.run("s", "u", [runner.input_tool("echo", "d", {"text": {"type": "string"}}), runner.read_tool("boom", "d")],
                   {"echo": lambda text: seen.append(text) or {"ok": text}, "boom": lambda: 1 / 0},
                   runner.submit_tool("submit_check", "d", {"ok": {"type": "boolean"}}), client=client)
        results = client.requests[1]["messages"][2]["content"]
        self.assertEqual(seen, ["x"])
        self.assertTrue(results[1]["is_error"])
        self.assertIn("ZeroDivisionError", results[1]["content"])

    def test_live_check_reports_structured_success(self):
        result = readiness.live_check(client=Recorder())
        self.assertTrue(result["ok"])
        self.assertEqual(result["model"], "claude-test-model")

    def test_live_check_reports_failure_without_raising(self):
        broken = NS(messages=NS(create=lambda **_: (_ for _ in ()).throw(ConnectionError("down"))))
        result = readiness.live_check(client=broken)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "ConnectionError")


class FriendlyErrors(unittest.TestCase):
    def test_named_sdk_errors(self):
        def err(name):
            return type(name, (Exception,), {})()
        self.assertIn("ANTHROPIC_MODEL", agents._friendly_error(err("NotFoundError")))
        self.assertIn("rate limited", agents._friendly_error(err("RateLimitError")))
        self.assertIn("TIMEOUT", agents._friendly_error(err("APITimeoutError")))
        self.assertIn("readiness", agents._friendly_error(err("BadRequestError")))


if __name__ == "__main__":
    unittest.main()
