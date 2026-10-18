
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from falkordb import FalkorDB

app = FastAPI(
    title="IncidentGraph AI",
    description="Graph-powered software incident investigation API",
    version="0.1.0",
)

# Allow the frontend development server to connect.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
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
