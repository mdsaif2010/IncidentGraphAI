# IncidentGraph AI

AI-assisted incident investigation using FalkorDB, FastAPI, and Ollama.

## Features
- Graph-based service dependency tracing
- Deployment status inspection
- AI agent tool-calling
- Evidence, hypotheses, missing evidence, and recommended next checks

## Tech Stack
- Python
- FastAPI
- FalkorDB
- Ollama
- Pytest

## Run the API
Activate the project environment, ensure FalkorDB and Ollama are running, then execute:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --reload
```

Open http://127.0.0.1:8000/docs

## Demo
Use `POST /api/incidents/{incident_id}/investigate` with incident ID `INC-1042`.

## Tests
```powershell
.\.venv\Scripts\python.exe -m pytest -q .\test_agent_improved.py
```

## Limitations
Live service health monitoring is not integrated. The root cause remains a hypothesis until verified with deployment logs and monitoring metrics.


## 🏗️ System Architecture

```mermaid
flowchart TB
    %% User Interface
    subgraph UI["🖥️ Presentation Layer"]
        A["👨‍💻 Engineer / SRE"]
        B["React + Vite<br/>IncidentGraphAI Dashboard"]
        A --> B
    end

    %% Backend
    subgraph API["⚙️ Backend Layer"]
        C["FastAPI<br/>Investigation API"]
        D["Incident Analysis<br/>& Evidence Processing"]
        E["Report Assembly<br/>Facts · Hypotheses · Next Checks"]
        C --> D
        D --> E
    end

    %% Intelligence
    subgraph AI["🧠 AI Reasoning"]
        F["Ollama<br/>Qwen3:4b"]
    end

    %% Graph Database
    subgraph GRAPH["🕸️ Graph Intelligence — FalkorDB"]
        G[("FalkorDB")]
        H["Service Nodes"]
        I["Dependency Relationships"]
        J["Incident Context"]
        G --- H
        G --- I
        G --- J
    end

    %% Main request flow
    B -->|"HTTP requests"| C
    D -->|"AI analysis request"| F
    F -->|"Model response"| D
    D -->|"Retrieve graph context"| G
    G -->|"Related services & dependencies"| D
    E -->|"Investigation results"| B

    %% Styling
    classDef frontend fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:2px
    classDef backend fill:#d1fae5,stroke:#059669,color:#064e3b,stroke-width:2px
    classDef ai fill:#f3e8ff,stroke:#9333ea,color:#581c87,stroke-width:2px
    classDef graph fill:#ffedd5,stroke:#ea580c,color:#7c2d12,stroke-width:2px

    class A,B frontend
    class C,D,E backend
    class F ai
    class G,H,I,J graph
```

### 🔍 How It Works

1. **Incident Input:** Engineers investigate incidents through the React dashboard.
2. **Backend Orchestration:** FastAPI coordinates the investigation workflow.
3. **AI-Assisted Analysis:** Ollama runs Qwen3:4b to support analysis of available evidence.
4. **Graph Context:** FalkorDB represents service dependencies and helps retrieve related graph context.
5. **Structured Results:** The application presents investigation findings, hypotheses, missing evidence, and suggested next checks.

### 🚀 Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Frontend | React + Vite | Interactive investigation dashboard |
| Backend | FastAPI | API and investigation orchestration |
| AI Model | Ollama + Qwen3:4b | Local AI-assisted analysis |
| Graph Database | FalkorDB | Service relationships and graph context |
```

**Important:** The diagram assumes the backend calls both Ollama and FalkorDB during investigation. Keep those arrows only if they match your actual code.

### Now, bro — fast

1. Copy the section into `README.md`.
2. Commit the README update on GitHub.
3. Check that the Mermaid graph renders.
4. Get straight back to recording your demo.

Don't spend the remaining time chasing perfect styling. A clear, accurate architecture diagram is what matters.
