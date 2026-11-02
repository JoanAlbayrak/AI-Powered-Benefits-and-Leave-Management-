"""Check the local AI setup before a demo.

    .venv/bin/python -m benefits_leave.readiness          # configuration only, no model call
    .venv/bin/python -m benefits_leave.readiness --live   # one small structured call to the model

Never prints the API key.
"""

import sys
import time

from benefits_leave import runner


def live_check(client=None):
    """One small tool-use call that must return a structured answer. Returns a non-secret result."""
    config = runner.settings()
    started = time.monotonic()
    try:
        outcome = runner.run(
            "You are a connectivity check. Call submit_check exactly once with ok set to true.",
            "Run the check.",
            [],
            {},
            runner.submit_tool("submit_check", "Report the check result.", {"ok": {"type": "boolean"}}),
            client=client,
            max_turns=2,
        )
    except Exception as exc:  # report the error class only; messages can echo request details
        return {"ok": False, "model": config["model"], "seconds": round(time.monotonic() - started, 1),
                "error": type(exc).__name__, "detail": str(exc)[:300]}
    ok = bool(outcome["answer"] and outcome["answer"].get("ok") is True)
    return {"ok": ok, "model": config["model"], "seconds": round(time.monotonic() - started, 1),
            "error": None if ok else outcome["stop_reason"], "detail": None}


def main(argv):
    status = runner.readiness()
    print("Benefits & Leave AI readiness")
    for key in ("provider", "model", "effort", "timeout_seconds", "max_retries", "action_budget_seconds", "key_configured", "sdk_installed"):
        print(f"  {key:22} {status[key]}")
    for problem in status["problems"]:
        print(f"  ! {problem}")
    if "--live" not in argv:
        print("Configuration " + ("looks ready." if status["ready"] else "is not ready.")
              + " Run with --live to make one real model call.")
        return 0 if status["ready"] else 1
    if not status["ready"]:
        print("Live check skipped: fix the problems above first.")
        return 1
    result = live_check()
    if result["ok"]:
        print(f"Live check passed: {result['model']} returned a structured answer in {result['seconds']}s.")
        return 0
    print(f"Live check failed ({result['error']}): {result['detail'] or 'no structured answer'}")
    print("Hints: check the key, that ANTHROPIC_MODEL is available to it, and your internet connection.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
