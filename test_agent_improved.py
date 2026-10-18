
import importlib.util
import json
import sys
import types
from pathlib import Path


def load_agent_with_fake_falkordb():
    # Create a fake FalkorDB module for this test file only.
    fake = types.ModuleType("falkordb")

    class FakeFalkorDB:
        def __init__(self, **kwargs):
            pass

        def select_graph(self, name):
            return object()

    fake.FalkorDB = FakeFalkorDB

    # Save the real module and temporarily install the fake.
    original_module = sys.modules.get("falkordb")
    sys.modules["falkordb"] = fake

    try:
        spec = importlib.util.spec_from_file_location(
            "agent_improved_test_module",
            Path(__file__).with_name("agent_improved.py"),
        )
        agent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent)
        return agent
    finally:
        # Restore the original module after importing the agent.
        if original_module is None:
            sys.modules.pop("falkordb", None)
        else:
            sys.modules["falkordb"] = original_module


agent = load_agent_with_fake_falkordb()


def test_validate_decision_rejects_bad_json():
    try:
        agent._validate_decision("not json", {"Payment"})
    except ValueError:
        return
    assert False, "Invalid decision should be rejected"


def test_final_report_requires_summary():
    try:
        agent._validate_decision({"action": "final"}, {"Payment"})
    except ValueError:
        return
    assert False, "Missing summary should be rejected"


def test_depth_is_clamped(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        agent,
        "query_graph",
        lambda query, params=None: (
            captured.update({"query": query, "params": params}) or []
        ),
    )

    result = agent.trace_dependencies("Payment", 99)

    assert result == {"paths": []}
    assert "1..4" in captured["query"]
    assert captured["params"]["service_name"] == "Payment"


def test_unknown_incident_returns_none(monkeypatch):
    monkeypatch.setattr(agent, "get_incident_evidence", lambda: [])
    assert agent.investigate_for_api("INC-DOES-NOT-EXIST") is None


def test_unknown_service_is_not_executed(monkeypatch):
    monkeypatch.setattr(
        agent,
        "get_incident_evidence",
        lambda: [{"incident_id": "INC-1", "service": "Payment"}],
    )
    monkeypatch.setattr(
        agent,
        "ask_model",
        lambda messages: json.dumps({
            "action": "tool",
            "tool": "inspect_deployment",
            "arguments": {"service_name": "Imaginary"},
            "reason": "test",
        }),
    )

    result = agent.investigate_for_api("INC-1")

    assert result["status"] == "incomplete"
    assert result["tool_history"] == []
    assert "not present" in result["stop_reason"]
