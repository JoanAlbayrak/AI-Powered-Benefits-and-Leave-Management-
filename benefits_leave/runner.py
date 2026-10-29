"""A small tool-use loop shared by all three agents.

Each agent gets only its own read-only tools, already scoped to one employee
or case in code, plus one submit tool for its structured answer. No agent has
a tool that sends, approves, or changes anything.
"""

import json
import os
from pathlib import Path

MODEL = "claude-opus-5-5"
MAX_TURNS = 6


def load_env(path=Path(__file__).resolve().parent.parent / ".env"):
    """Read KEY=value lines from .env into the environment (no extra installs needed)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def read_tool(name, description):
    """A read-only tool with no inputs: what it reads is fixed by code."""
    return {"name": name, "description": description, "strict": True, "input_schema": _schema({})}


def submit_tool(name, description, properties):
    return {"name": name, "description": description, "strict": True, "input_schema": _schema(properties)}


def run(system, user_message, read_tools, tool_impls, submit, client=None):
    """Run one agent until it calls its submit tool.

    Returns {"answer": dict or None, "tool_calls": [names], "stop_reason": str}.
    """
    if client is None:
        import anthropic  # imported here so tests run without installing anything

        load_env()
        client = anthropic.Anthropic()

    tools = read_tools + [submit]
    messages = [{"role": "user", "content": user_message}]
    calls = []

    for _ in range(MAX_TURNS):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=system,
            tools=tools,
            messages=messages,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            return {"answer": None, "tool_calls": calls, "stop_reason": "refusal"}

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            return {"answer": None, "tool_calls": calls, "stop_reason": response.stop_reason}

        messages.append({"role": "assistant", "content": response.content})
        results, answer = [], None
        for block in tool_uses:
            calls.append(block.name)
            if block.name == submit["name"]:
                answer = dict(block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Received."})
            elif block.name in tool_impls:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": json.dumps(tool_impls[block.name]())})
            else:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"Unknown tool: {block.name}", "is_error": True})
        if answer is not None:
            return {"answer": answer, "tool_calls": calls, "stop_reason": "submitted"}
        messages.append({"role": "user", "content": results})

    return {"answer": None, "tool_calls": calls, "stop_reason": "max_turns"}
