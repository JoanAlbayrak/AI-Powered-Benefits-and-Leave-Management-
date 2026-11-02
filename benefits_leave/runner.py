"""A small tool-use loop shared by all three agents.

Each agent gets only its own tools, already scoped to one employee or case in
code, plus one submit tool for its structured answer. No agent has a tool that
sends, approves, or changes anything.

Runtime settings come from the private .env file (never from the browser):

    ANTHROPIC_API_KEY           required for live AI
    ANTHROPIC_MODEL             default claude-opus-5-5
    ANTHROPIC_EFFORT            low | medium | high (default medium); "none" omits it
    ANTHROPIC_TIMEOUT_SECONDS   per request, default 60
    ANTHROPIC_MAX_RETRIES       SDK retries for transient errors, default 2
    BENEFITS_AI_DISABLED        set to 1 to force the deterministic fallback
"""

import json
import os
import time
from pathlib import Path

DEFAULT_MODEL = "claude-opus-5-5"
MODEL = DEFAULT_MODEL           # kept for older imports; use settings()["model"]
MAX_TURNS = 6
MAX_TOKENS = 8000
PLACEHOLDER_KEYS = {"", "your-anthropic-api-key-here"}
EFFORTS = {"low", "medium", "high"}
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# The most recent live outcome in this server process. Never contains secrets.
LAST_LIVE_RESULT = {"status": "not_run", "model": None, "at": None, "detail": None}


class AIUnavailable(RuntimeError):
    """Live AI cannot run with the current local configuration."""


def load_env(path=None):
    """Read KEY=value lines from .env into the environment (no extra installs needed)."""
    path = Path(path) if path else ENV_FILE
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _number(name, default, cast, low, high):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default, None
    try:
        value = cast(raw)
    except ValueError:
        return default, f"{name} must be a number; using {default}"
    if not low <= value <= high:
        return default, f"{name} must be between {low} and {high}; using {default}"
    return value, None


def settings():
    """Non-secret runtime settings plus any configuration problems."""
    load_env()
    problems = []
    effort = os.environ.get("ANTHROPIC_EFFORT", "medium").strip().lower() or "medium"
    if effort == "none":
        effort = None
    elif effort not in EFFORTS:
        problems.append(f"ANTHROPIC_EFFORT must be low, medium, high or none; using medium")
        effort = "medium"
    timeout, problem = _number("ANTHROPIC_TIMEOUT_SECONDS", 60.0, float, 5, 600)
    problems += [problem] if problem else []
    retries, problem = _number("ANTHROPIC_MAX_RETRIES", 2, int, 0, 5)
    problems += [problem] if problem else []
    return {
        "model": os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_MODEL,
        "effort": effort,
        "timeout_seconds": timeout,
        "max_retries": retries,
        "disabled": os.environ.get("BENEFITS_AI_DISABLED", "").strip().lower() in ("1", "true", "yes"),
        "problems": problems,
    }


def _key_configured():
    load_env()
    return os.environ.get("ANTHROPIC_API_KEY", "").strip() not in PLACEHOLDER_KEYS


def _sdk_installed():
    try:
        import anthropic  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def readiness():
    """Can live AI run? Reads local configuration only: never calls the model or returns the key."""
    config = settings()
    problems = list(config["problems"])
    if config["disabled"]:
        problems.append("Live AI is turned off (BENEFITS_AI_DISABLED); deterministic results only")
    if not _key_configured():
        problems.append("No API key: copy .env.example to .env and set ANTHROPIC_API_KEY")
    if not _sdk_installed():
        problems.append("The anthropic library isn't installed: .venv/bin/pip install -r requirements.txt")
    ready = not config["disabled"] and _key_configured() and _sdk_installed()
    return {
        "ready": ready,
        "provider": "Anthropic",
        "model": config["model"],
        "effort": config["effort"],
        "timeout_seconds": config["timeout_seconds"],
        "max_retries": config["max_retries"],
        "key_configured": _key_configured(),
        "sdk_installed": _sdk_installed(),
        "problems": problems,
        "last_live_result": dict(LAST_LIVE_RESULT),
    }


def make_client():
    """A real client built from local settings, or AIUnavailable with a clear reason."""
    config = settings()
    if config["disabled"]:
        raise AIUnavailable("Live AI is turned off (BENEFITS_AI_DISABLED).")
    if not _key_configured():
        raise AIUnavailable("No API key is configured. Set ANTHROPIC_API_KEY in your .env file.")
    import anthropic  # imported here so tests run without installing anything

    return anthropic.Anthropic(timeout=config["timeout_seconds"], max_retries=config["max_retries"])


def record_live_result(status, model, detail=None):
    LAST_LIVE_RESULT.update(status=status, model=model, detail=detail,
                            at=time.strftime("%Y-%m-%d %H:%M:%S"))


def _schema(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required, "additionalProperties": False}


def read_tool(name, description):
    """A read-only tool with no inputs: what it reads is fixed by code."""
    return {"name": name, "description": description, "strict": True, "input_schema": _schema({})}


def input_tool(name, description, properties):
    """A tool with inputs. Code validates every input before acting on it."""
    return {"name": name, "description": description, "strict": True, "input_schema": _schema(properties)}


def submit_tool(name, description, properties):
    return {"name": name, "description": description, "strict": True, "input_schema": _schema(properties)}


def _call_tool(impl, tool_input):
    try:
        result = impl(**tool_input) if tool_input else impl()
        return json.dumps(result), False
    except Exception as exc:  # a tool failure is reported to the model, never hidden
        return f"Tool failed: {type(exc).__name__}: {exc}", True


def run(system, user_message, tools, tool_impls, submit, client=None, max_turns=MAX_TURNS):
    """Run one agent until it calls its submit tool.

    Returns {"answer": dict or None, "tool_calls": [names], "stop_reason": str, "model_calls": int}.
    """
    live = client is None
    config = settings()
    if live:
        client = make_client()

    tools = list(tools) + [submit]
    messages = [{"role": "user", "content": user_message}]
    calls = []
    request = {"model": config["model"], "max_tokens": MAX_TOKENS, "system": system, "tools": tools}
    if config["effort"]:
        request["output_config"] = {"effort": config["effort"]}

    def done(answer, stop_reason, turns):
        if live:
            record_live_result("ok" if answer is not None else "no_answer", config["model"],
                               None if answer is not None else stop_reason)
        return {"answer": answer, "tool_calls": calls, "stop_reason": stop_reason, "model_calls": turns}

    for turn in range(1, max_turns + 1):
        try:
            response = client.messages.create(messages=messages, **request)
        except Exception as exc:
            if live:
                record_live_result("error", config["model"], type(exc).__name__)
            raise
        if response.stop_reason == "refusal":
            return done(None, "refusal", turn)

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            return done(None, response.stop_reason, turn)

        messages.append({"role": "assistant", "content": response.content})
        results, answer = [], None
        for block in tool_uses:
            calls.append(block.name)
            if block.name == submit["name"]:
                answer = dict(block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Received."})
            elif block.name in tool_impls:
                content, is_error = _call_tool(tool_impls[block.name], dict(block.input or {}))
                result = {"type": "tool_result", "tool_use_id": block.id, "content": content}
                if is_error:
                    result["is_error"] = True
                results.append(result)
            else:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"Unknown tool: {block.name}", "is_error": True})
        if answer is not None:
            return done(answer, "submitted", turn)
        messages.append({"role": "user", "content": results})

    return done(None, "max_turns", max_turns)
