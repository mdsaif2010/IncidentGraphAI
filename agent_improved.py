"""IncidentGraph AI: bounded, evidence-grounded incident investigation.

This module only reads from the existing FalkorDB graph. It never seeds or resets data.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from falkordb import FalkorDB

# Connect to the existing graph; do not reseed/reset it.
db = FalkorDB(host="localhost", port=6379)
graph = db.select_graph("incidents")

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:4b"
MAX_STEPS = 4
MODEL_TIMEOUT_SECONDS = 180
MAX_DEPENDENCY_DEPTH = 4


def query_graph(cypher: str, params: dict | None = None) -> list:
    """Run a predefined read-only Cypher query with parameterized values."""
    result = graph.query(cypher, params or {})
    return result.result_set


def trace_dependencies(service_name: str, max_depth: int = 3) -> dict:
    """Find downstream services reachable through CALLS relationships."""
    depth = max(1, min(int(max_depth), MAX_DEPENDENCY_DEPTH))
    rows = query_graph(
        f"""
        MATCH (start:Service {{name: $service_name}})
        MATCH path = (start)-[:CALLS*1..{depth}]->(dep:Service)
        RETURN [n IN nodes(path) | n.name] AS path
        LIMIT 30
        """,
        {"service_name": service_name},
    )
    return {"paths": [row[0] for row in rows if row and row[0] is not None]}


def inspect_deployment(service_name: str) -> dict:
    """Retrieve deployments linked to a service."""
    rows = query_graph(
        """
        MATCH (d:Deployment)-[:DEPLOYED_TO]->(s:Service {name: $name})
        RETURN d.id, d.version, d.status
        LIMIT 20
        """,
        {"name": service_name},
    )
    return {
        "deployments": [
            {"id": row[0], "version": row[1], "status": row[2]}
            for row in rows
        ]
    }


def check_service_health(service_name: str) -> dict:
    """Health is unknown until a real monitoring integration is configured."""
    return {
        "service": service_name,
        "status": "unknown",
        "source": "no real health-monitoring integration configured",
    }


TOOLS = {
    "trace_dependencies": trace_dependencies,
    "inspect_deployment": inspect_deployment,
    "check_service_health": check_service_health,
}


SYSTEM_PROMPT = """
You are IncidentGraph AI, an evidence-grounded software incident investigator.
You may choose one approved tool per step:
- trace_dependencies: {"service_name": string, "max_depth": integer}
- inspect_deployment: {"service_name": string}
- check_service_health: {"service_name": string}

Return exactly one JSON object, with one of these shapes:
Tool call: {"action":"tool","tool":"trace_dependencies","arguments":{"service_name":"Payment","max_depth":3},"reason":"why this check is useful"}
Final: {"action":"final","summary":"...","facts":["..."],"hypotheses":["..."],"missing_evidence":["..."],"next_checks":["..."]}

Rules:
- Use only facts supported by supplied graph evidence and tool results.
- A failed deployment is a clue, not proof of causation.
- Unknown health data must remain unknown.
- Never invent logs, metrics, timestamps, or events.
- Do not request arbitrary code or arbitrary Cypher queries.
- Choose checks that add new information; do not repeat a successful identical check.
- If evidence is insufficient or the step budget is nearly exhausted, return a cautious final report.
- Keep each list in the final report a list of short strings.
""".strip()


def ask_model(messages: list[dict[str, str]], json_mode: bool = True) -> str:
    """Ask local Ollama for a response."""
    payload_data = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0},
    }

    if json_mode:
        payload_data["format"] = "json"

    payload = json.dumps(payload_data).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(
        request, timeout=MODEL_TIMEOUT_SECONDS
    ) as response:
        result = json.loads(response.read().decode("utf-8"))

    content = result.get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Ollama returned an empty model response")

    return content.strip()


def get_incident_evidence() -> list[dict[str, Any]]:
    """Read incident, alert, affected service, and linked deployment evidence."""
    rows = query_graph(
        """
        MATCH (i:Incident)-[:TRIGGERED_BY]->(a:Alert)-[:AFFECTS]->(s:Service)
        OPTIONAL MATCH (d:Deployment)-[:DEPLOYED_TO]->(s)
        RETURN i.id, i.title, a.severity, a.message,
               s.name, d.id, d.version, d.status
        LIMIT 20
        """
    )
    return [
        {
            "incident_id": row[0],
            "title": row[1],
            "severity": row[2],
            "alert": row[3],
            "service": row[4],
            "deployment_id": row[5],
            "deployment_version": row[6],
            "deployment_status": row[7],
        }
        for row in rows
    ]


def _validate_decision(decision: Any, known_services: set[str]) -> tuple[str, str | None, dict]:
    """Validate model output and tool arguments before execution."""
    if not isinstance(decision, dict):
        raise ValueError("Model decision must be a JSON object")
    action = decision.get("action")
    if action == "final":
        report = decision
        if not isinstance(report.get("summary"), str):
            raise ValueError("Final report is missing a string summary")
        for key in ("facts", "hypotheses", "missing_evidence", "next_checks"):
            if not isinstance(report.get(key, []), list):
                raise ValueError(f"Final report field '{key}' must be a list")
        return "final", None, {}
    if action != "tool":
        raise ValueError("Unsupported agent action")

    tool_name = decision.get("tool")
    arguments = decision.get("arguments", {})
    if tool_name not in TOOLS or not isinstance(arguments, dict):
        raise ValueError("Unapproved tool or invalid arguments")
    service_name = arguments.get("service_name")
    if not isinstance(service_name, str) or service_name not in known_services:
        raise ValueError("Service name is not present in this incident's evidence")

    if tool_name == "trace_dependencies":
        depth = arguments.get("max_depth", 3)
        if not isinstance(depth, int) or isinstance(depth, bool):
            raise ValueError("max_depth must be an integer")
        safe_args = {"service_name": service_name, "max_depth": max(1, min(depth, MAX_DEPENDENCY_DEPTH))}
    else:
        safe_args = {"service_name": service_name}
    return "tool", tool_name, safe_args


def _fallback_report(evidence: list[dict], tool_history: list[dict], reason: str) -> dict:
    """Return a transparent report when the model cannot finish cleanly."""
    facts = []
    for item in evidence:
        if item.get("alert"):
            facts.append(f"Alert recorded for {item.get('service')}: {item['alert']}")
        if item.get("deployment_id"):
            facts.append(
                f"Deployment {item.get('deployment_id')} version {item.get('deployment_version')} "
                f"has recorded status '{item.get('deployment_status')}'."
            )
    return {
        "summary": "Investigation stopped before a model-generated diagnosis could be validated. Root cause is unconfirmed.",
        "facts": facts,
        "hypotheses": [],
        "missing_evidence": [reason, "Service logs and monitoring metrics are not connected to this prototype."],
        "next_checks": ["Inspect application logs around the alert time.", "Compare service error metrics before and after the recorded deployment."],
    }


def investigate_for_api(incident_id: str) -> dict | None:
    """Run a bounded adaptive investigation for one incident and return a report."""
    incidents = get_incident_evidence()
    evidence = [item for item in incidents if item.get("incident_id") == incident_id]
    if not evidence:
        return None

    known_services = {item["service"] for item in evidence if item.get("service")}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Investigate this incident using the supplied evidence:\n" + json.dumps(evidence)},
    ]
    tool_history: list[dict] = []
    seen_calls: set[str] = set()
    stop_reason = "Investigation step budget exhausted."

    for step in range(MAX_STEPS):
        try:
            raw = ask_model(messages)
            decision = json.loads(raw)
            action, tool_name, arguments = _validate_decision(decision, known_services)
        except (urllib.error.URLError, TimeoutError) as error:
            stop_reason = f"Local model unavailable or timed out: {type(error).__name__}."
            break
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as error:
            stop_reason = f"Model response could not be validated: {error}."
            messages.append({
                "role": "user",
                "content": (
                    "Your previous response was invalid: " + str(error) +
                    ". Reply with ONLY a valid JSON object. Use action 'tool' "
                    "with an approved tool and valid arguments, or action 'final' "
                    "with summary, facts, hypotheses, missing_evidence, and next_checks."
                ),
            })
            continue

        if action == "final":
            return {
                "incident_id": incident_id,
                "evidence": evidence,
                "tool_history": tool_history,
                "report": {
                    "summary": decision["summary"],
                    "facts": decision.get("facts", []),
                    "hypotheses": decision.get("hypotheses", []),
                    "missing_evidence": decision.get("missing_evidence", []),
                    "next_checks": decision.get("next_checks", []),
                },
                "status": "completed",
            }

        call_key = json.dumps([tool_name, arguments], sort_keys=True)
        if call_key in seen_calls:
            stop_reason = f"Agent repeated the same tool call ({tool_name}); stopped to avoid a loop."
            break
        seen_calls.add(call_key)

        try:
            result = TOOLS[tool_name](**arguments)
        except Exception as error:
            # Keep the investigation alive while making the tool failure explicit.
            result = {"error": f"{type(error).__name__}: {error}"}

        tool_history.append({
            "step": step + 1,
            "reason": decision.get("reason", "No reason provided"),
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
        })
        messages.append({"role": "assistant", "content": json.dumps(decision)})
        messages.append({
            "role": "user",
            "content": (
                "Tool result (treat errors as missing evidence):\n"
                + json.dumps(result)
                + "\nChoose a different useful approved check or return the final report."
            ),
        })

    return {
        "incident_id": incident_id,
        "evidence": evidence,
        "tool_history": tool_history,
        "report": _fallback_report(evidence, tool_history, stop_reason),
        "status": "incomplete",
        "stop_reason": stop_reason,
    }


def run_agent() -> None:
    """CLI entry point that uses the same investigation logic as the API."""
    try:
        incidents = get_incident_evidence()
    except Exception as error:
        print(f"Could not read FalkorDB: {type(error).__name__}: {error}")
        return
    if not incidents:
        print("No matching incidents found in the graph.")
        return

    print("\n=== INCIDENTGRAPH AI AGENT ===")
    print(json.dumps(incidents, indent=2))
    incident_ids = list(dict.fromkeys(item.get("incident_id") for item in incidents if item.get("incident_id")))
    incident_id = incident_ids[0]
    try:
        result = investigate_for_api(incident_id)
    except Exception as error:
        print(f"Investigation failed: {type(error).__name__}: {error}")
        return
    print("\n=== INVESTIGATION REPORT ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run_agent()
