import json
import urllib.request
import urllib.error

from falkordb import FalkorDB


# Connect to the existing FalkorDB graph.
db = FalkorDB(host="localhost", port=6379)
graph = db.select_graph("incidents")

# Local Ollama AI settings.
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:4b"


def ask_ai(evidence):
    """Ask the local AI to analyze incident evidence."""

    prompt = f"""
You are IncidentGraph AI, a software incident investigation assistant.

Analyze the incident evidence provided below.

Rules:
- Treat the evidence as facts, not proof of causation.
- Separate observed facts from hypotheses.
- Never invent logs, metrics, or events.
- Explain what the service dependencies may indicate.
- Recommend practical next checks.
- Clearly state when evidence is insufficient.

Incident evidence:
{json.dumps(evidence, indent=2)}

Respond using these sections:
1. Observed facts
2. Service dependencies
3. Most likely hypothesis
4. Why the hypothesis needs verification
5. Recommended next checks
"""

    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "The AI returned no response.")

    except urllib.error.URLError as error:
        print(f"\nCould not connect to Ollama: {error}")
        print("Make sure Ollama is running.")
        return None


def investigate_incident():
    """Collect incident evidence from the existing graph."""

    query = """
    MATCH (i:Incident)-[:TRIGGERED_BY]->(a:Alert)-[:AFFECTS]->(s:Service)
    OPTIONAL MATCH (d:Deployment)-[:DEPLOYED_TO]->(s)
    OPTIONAL MATCH (s)-[:CALLS]->(dependency:Service)
    RETURN i.id AS incident_id,
           i.title AS incident_title,
           a.severity AS severity,
           a.message AS alert,
           s.name AS affected_service,
           d.id AS deployment_id,
           d.version AS deployment_version,
           d.status AS deployment_status,
           collect(DISTINCT dependency.name) AS dependencies
    """

    try:
        result = graph.query(query)
    except Exception as error:
        print(f"Could not query FalkorDB: {error}")
        return

    if not result.result_set:
        print("No matching incident evidence found.")
        return

    for row in result.result_set:
        evidence = {
            "incident_id": row[0],
            "incident_title": row[1],
            "severity": row[2],
            "alert": row[3],
            "affected_service": row[4],
            "deployment_id": row[5],
            "deployment_version": row[6],
            "deployment_status": row[7],
            "dependencies": row[8] or []
        }

        print("\n=== INCIDENT INVESTIGATION ===")
        print(f"Incident: {evidence['incident_id']} - "
              f"{evidence['incident_title']}")
        print(f"Severity: {evidence['severity']}")
        print(f"Alert: {evidence['alert']}")
        print(f"Affected service: {evidence['affected_service']}")
        print(f"Related deployment: {evidence['deployment_id']}")
        print(f"Deployment version: {evidence['deployment_version']}")
        print(f"Deployment status: {evidence['deployment_status']}")
        print(f"Service dependencies: "
              f"{', '.join(evidence['dependencies']) or 'None found'}")

        print("\n=== AI ANALYSIS ===")
        analysis = ask_ai(evidence)

        if analysis:
            print(analysis)


if __name__ == "__main__":
    investigate_incident()
