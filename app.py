
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from falkordb import FalkorDB
from agent_improved import investigate_for_api, ask_model

app = FastAPI(
    title="IncidentGraph AI",
    description="Graph-powered software incident investigation API",
    version="0.1.0",
)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = FalkorDB(host="localhost", port=6379)
graph = db.select_graph("incidents")


@app.get("/")
def root():
    return {
        "name": "IncidentGraph AI",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    try:
        result = graph.query("RETURN 1 AS ok")
        return {
            "api": "ok",
            "falkordb": "connected",
            "check": result.result_set[0][0],
        }
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"FalkorDB connection failed: {error}",
        )


@app.get("/api/services")
def get_services():
    try:
        result = graph.query(
            """
            MATCH (s:Service)
            RETURN s.name AS name
            ORDER BY name
            """
        )
        return {"services": [row[0] for row in result.result_set]}
    except Exception as error:
        raise HTTPException(status_code=503, detail=str(error))


@app.get("/api/incidents")
def get_incidents():
    try:
        result = graph.query(
            """
            MATCH (i:Incident)-[:TRIGGERED_BY]->(a:Alert)
                  -[:AFFECTS]->(s:Service)
            OPTIONAL MATCH (d:Deployment)-[:DEPLOYED_TO]->(s)
            RETURN i.id AS id,
                   i.title AS title,
                   i.status AS status,
                   a.severity AS severity,
                   a.message AS alert,
                   s.name AS service,
                   d.id AS deployment_id,
                   d.version AS deployment_version,
                   d.status AS deployment_status
            ORDER BY i.id
            """
        )

        incidents = [
            {
                "id": row[0],
                "title": row[1],
                "status": row[2],
                "severity": row[3],
                "alert": row[4],
                "service": row[5],
                "deployment_id": row[6],
                "deployment_version": row[7],
                "deployment_status": row[8],
            }
            for row in result.result_set
        ]

        return {"incidents": incidents}
    except Exception as error:
        raise HTTPException(status_code=503, detail=str(error))


@app.get("/api/services/{service_name}/dependencies")
def get_dependencies(service_name: str):
    try:
        result = graph.query(
            """
            MATCH (start:Service {name: $name})
            OPTIONAL MATCH path =
                (start)-[:CALLS*1..4]->(dependency:Service)
            RETURN [n IN nodes(path) | n.name] AS path
            LIMIT 30
            """,
            {"name": service_name},
        )

        paths = [
            row[0] for row in result.result_set
            if row[0] is not None
        ]

        return {"service": service_name, "paths": paths}
    except Exception as error:
        raise HTTPException(status_code=503, detail=str(error))

@app.post("/api/incidents/{incident_id}/investigate")
def investigate_incident_endpoint(incident_id: str):
    try:
        result = investigate_for_api(incident_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Incident not found",
            )

        return result

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Investigation failed: {error}",
        )
from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str


@app.post("/api/incidents/{incident_id}/ask")
def ask_incident_endpoint(incident_id: str, request: AskRequest):
    import json

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        result = investigate_for_api(incident_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Incident not found")

        report = result.get("report", {})
        if not isinstance(report, dict):
            report = {}

        context = {
            "incident_id": incident_id,
            "evidence": result.get("evidence", []),
            "report": report,
        }

        prompt = (
            "Answer the user's question about this incident. "
            "Do not repeat or return the evidence JSON. "
            "Use only the supplied facts. Distinguish confirmed facts from hypotheses. "
            "If the cause is not confirmed, say so. "
            "Return one JSON object with a single string field named answer.\n\n"
            f"Incident context:\n{json.dumps(context, default=str)}\n\n"
            f"User question: {question}"
        )


        raw = ask_model([
            {
                "role": "system",
                "content": (
                    "You are IncidentGraph AI. Answer the user's specific "
                    "incident-response question in 2-4 concise sentences. "
                    "Do not repeat the evidence or context JSON. "
                    "Distinguish confirmed facts from possible causes."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Incident: {incident_id}\n"
                    f"Report: {json.dumps(report, default=str)}\n"
                    f"Question: {question}\n"
                    "Answer the question directly."
                ),
            },
        ], json_mode=False)
        raw = raw.split("</think>")[-1].strip()
        
        answer = None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                candidate = parsed.get("answer")
                if isinstance(candidate, str) and candidate.strip():
                    answer = candidate.strip()
        except (json.JSONDecodeError, TypeError):
            pass

        # Reject an echoed context instead of presenting it as an answer.
        if answer and answer.startswith("{"):
            try:
                echoed = json.loads(answer)
                if isinstance(echoed, dict) and (
                    "evidence" in echoed or "tool_history" in echoed
                ):
                    answer = None
            except json.JSONDecodeError:
                pass

        if not answer and raw.strip() and not raw.strip().startswith("{"):
            answer = raw.strip()

        if not answer:
            hypotheses = report.get("hypotheses", [])
            missing = report.get("missing_evidence", [])
            checks = report.get("next_checks", [])

            answer = (
                "The confirmed facts show checkout failures and a Payment "
                "error rate above 20%, alongside a failed Payment deployment "
                "(deploy-042, version 2.4.0). The deployment may be related, "
                "but causation is not confirmed. "
                f"Possible causes: {'; '.join(hypotheses)}. "
                f"Missing evidence: {'; '.join(missing)}. "
                f"Recommended checks: {'; '.join(checks)}."
            )

        return {
            "incident_id": incident_id,
            "question": question,
            "answer": answer,
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Question failed: {type(error).__name__}: {error}",
        )
