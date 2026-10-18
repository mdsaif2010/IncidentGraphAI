
import json
import urllib.request
import urllib.error

from falkordb import FalkorDB

# Existing graph: do not reseed or reset it.
db = FalkorDB(host="localhost", port=6379)
graph = db.select_graph("incidents")

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:4b"
MAX_STEPS = 4


def query_graph(cypher, params=None):
    """Execute one predefined, read-only graph query."""
    result = graph.query(cypher, params or {})
    return result.result_set


def trace_dependencies(service_name, max_depth=3):
    """Find services reachable through CALLS relationships."""
    max_depth = max(1, min(int(max_depth), 4))

    rows = query_graph(
        f"""
        MATCH (start:Service {{name: $service_name}})
        MATCH path = (start)-[:CALLS*1..{max_depth}]->(dep:Service)
        RETURN [n IN nodes(path) | n.name] AS path
        LIMIT 30
        """,
        {"service_name": service_name},
    )

    return {"paths": [row[0] for row in rows]}


def inspect_deployment(service_name):
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


def check_service_health(service_name):
    """Report whether synthetic health data is available.

    No real monitoring integration exists yet.
    Never invent a health status.
    """
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


def ask_model(messages):
    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "format": "json",
        "think": False,
        "options": {"temperature": 0}
    }).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result["message"]["content"]


def get_incident_evidence():
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
            "incident_id": r[0],
            "title": r[1],
            "severity": r[2],
            "alert": r[3],
            "service": r[4],
            "deployment_id": r[5],
            "deployment_version": r[6],
            "deployment_status": r[7],
        }
        for r in rows
    ]


def run_agent():
    try:
        incidents = get_incident_evidence()
    except Exception as error:
        print(f"Could not read FalkorDB: {error}")
        return

    if not incidents:
        print("No matching incidents found in the graph.")
        return

    evidence = incidents
    print("\n=== INCIDENTGRAPH AI AGENT ===")
    print(json.dumps(incidents, indent=2))

    messages = [
        {
            "role": "system",
            "content": """
You are an incident investigation agent.

You must choose one approved diagnostic tool per step.
Available tools:
1. trace_dependencies: arguments {"service_name": string, "max_depth": integer}
2. inspect_deployment: arguments {"service_name": string}
3. check_service_health: arguments {"service_name": string}

Return JSON only, using one of these shapes:

For a tool call:
{"action":"tool","tool":"trace_dependencies","arguments":{"service_name":"Payment","max_depth":3},"reason":"why this check is useful"}

For a final report:
{"action":"final","summary":"...","facts":["..."],"hypotheses":["..."],"missing_evidence":["..."],"next_checks":["..."]}

Use only facts supported by the supplied evidence and tool results.
A failed deployment is not proof that it caused an incident.
Health status must remain unknown if no health data exists.
Do not request or execute arbitrary code or arbitrary queries.
After enough checks, return a final report.
"""
        },
        {
            "role": "user",
            "content": "Investigate this incident evidence:\n"
                       + json.dumps(evidence)
        },
    ]

    for step in range(1, MAX_STEPS + 1):
        print(f"\n--- Agent step {step}/{MAX_STEPS} ---")

        try:
            raw = ask_model(messages)
            decision = json.loads(raw)
        except (urllib.error.URLError, TimeoutError) as error:
            print(f"Ollama connection failed: {error}")
            return
        except (ValueError, KeyError) as error:
            print(f"Could not parse the model response: {error}")
            return

        if decision.get("action") == "final":
            print("\n=== INVESTIGATION REPORT ===")
            print(json.dumps(decision, indent=2))
            return

        if decision.get("action") != "tool":
            print("Stopped: model returned an unsupported action.")
            return

        tool_name = decision.get("tool")
        arguments = decision.get("arguments", {})

        if tool_name not in TOOLS or not isinstance(arguments, dict):
            print("Stopped: unapproved tool or invalid arguments.")
            return

        # Validate arguments before running the approved tool.
        service_name = arguments.get("service_name")
        known_services = {
            item["service"] for item in evidence if item.get("service")
        }

        if not isinstance(service_name, str) or service_name not in known_services:
            print("Stopped: service name is not in the incident evidence.")
            return

        if tool_name == "trace_dependencies":
            depth = arguments.get("max_depth", 3)
            if not isinstance(depth, int) or isinstance(depth, bool):
                print("Stopped: max_depth must be an integer.")
                return
            arguments["max_depth"] = max(1, min(depth, 4))

        print("Reason:", decision.get("reason", "Not provided"))
        print("Tool:", tool_name)
        print("Arguments:", json.dumps(arguments))

        try:
            tool_result = TOOLS[tool_name](**arguments)
        except Exception as error:
            tool_result = {"error": str(error)}

        print("Result:", json.dumps(tool_result, indent=2))

        messages.append({
            "role": "assistant",
            "content": json.dumps(decision)
        })
        messages.append({
            "role": "user",
            "content": (
                "Tool result:\n" + json.dumps(tool_result)
                + "\nChoose the next approved tool or return the final report."
            )
        })

    print("\nStep limit reached. Investigation stopped safely.")
    print("Review the tool results above; no root cause is confirmed.")


if __name__ == "__main__":
    run_agent()
