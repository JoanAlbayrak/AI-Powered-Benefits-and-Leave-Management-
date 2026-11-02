"""A pretend Claude that follows a small script, so multi-step agent behavior can be tested offline."""

import json
from types import SimpleNamespace as NS


def tool_use(name, tool_input=None, id_=None):
    return NS(type="tool_use", id=id_ or f"{name}-id", name=name, input=tool_input or {})


class ScriptedClient:
    """`script(request, results)` returns a list of tool_use blocks for each model turn.

    `results` maps tool name -> parsed JSON tool result seen so far in this run.
    Every request is recorded so tests can check what each agent was allowed to see.
    """

    def __init__(self, script):
        self.script = script
        self.requests = []
        self.messages = NS(create=self._create)

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        results = {}
        names = {}
        for message in kwargs["messages"]:
            content = message["content"]
            if message["role"] == "assistant":
                names.update({b.id: b.name for b in content if getattr(b, "type", "") == "tool_use"})
            elif isinstance(content, list):
                for item in content:
                    try:
                        results[names[item["tool_use_id"]]] = json.loads(item["content"])
                    except (ValueError, KeyError):
                        results[names.get(item["tool_use_id"], "?")] = item["content"]
        return NS(stop_reason="tool_use", content=self.script(kwargs, results))

    def runs_for(self, submit_name):
        return [r for r in self.requests if r["tools"][-1]["name"] == submit_name]


def submit_name(request):
    return request["tools"][-1]["name"]


def read_all_then(request, results, answer):
    """Call every no-input read tool once, then submit `answer` (a dict or a function of results)."""
    reads = [t["name"] for t in request["tools"][:-1] if not t["input_schema"]["properties"]]
    if not all(name in results for name in reads):
        return [tool_use(name) for name in reads]
    return [tool_use(submit_name(request), answer(results) if callable(answer) else answer)]
