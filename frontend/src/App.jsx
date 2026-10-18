import { useState } from "react";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  CircleAlert,
  Clock3,
  GitBranch,
  Layers3,
  Menu,
  MessageCircle,
  Network,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  X,
  RotateCcw,
} from "lucide-react";
import "./App.css";

const API = "http://127.0.0.1:8000";

const navItems = [
  { label: "Investigate", icon: Sparkles },
  { label: "Incidents", icon: Layers3 },
  { label: "Service graph", icon: Network },
  { label: "History", icon: Clock3 },
];

const suggestions = [
  "What should I check first?",
  "Why might deploy-042 be related?",
  "What evidence is missing?",
];

const textOf = (x) =>
  typeof x === "string" || typeof x === "number"
    ? String(x)
    : x?.description ||
      x?.detail ||
      x?.reason ||
      x?.finding ||
      x?.evidence ||
      x?.recommendation ||
      x?.action ||
      x?.name ||
      x?.message ||
      JSON.stringify(x);

function App() {
  const [page, setPage] = useState("Investigate");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [incidentId, setIncidentId] = useState("INC-1042");

  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState("");
  const [askError, setAskError] = useState("");

  const [tab, setTab] = useState("Findings");
  const [history, setHistory] = useState([]);
  const [selectedService, setSelectedService] = useState("Payment");

const investigation = report?.report || report || {};

const facts =
  investigation.facts ||
  investigation.observations ||
  investigation.findings ||
  [];

const hypotheses =
  investigation.hypotheses ||
  investigation.possible_causes ||
  [];

const missing =
  investigation.missing_evidence ||
  investigation.evidence_gaps ||
  investigation.unknowns ||
  [];

const checks =
  investigation.next_checks ||
  investigation.recommended_checks ||
  investigation.recommendations ||
  investigation.next_steps ||
  [];

const evidence =
  report?.evidence || investigation.evidence || report?.evidence_items || [];

const toolHistory =
  report?.tool_history ||
  investigation.tool_history ||
  report?.tool_calls ||
  report?.steps ||
  [];

const summary =
  investigation.summary ||
  investigation.conclusion ||
  investigation.message ||
  report?.summary ||
  "";

  // Navigation only changes the page.
  // It does not automatically run an investigation.
  function go(nextPage) {
    setPage(nextPage);
    setError("");
    setAskError("");
  }

  async function investigate(value = incidentId) {
    const id = value.trim();

    if (!id || loading) return;

    setIncidentId(id);
    setLoading(true);
    setError("");
    setReport(null);
    setAnswer("");

    try {
      const response = await fetch(
        `${API}/api/incidents/${encodeURIComponent(id)}/investigate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : `Investigation failed (${response.status})`
        );
      }

      setReport(data);
      setTab("Findings");

      setHistory((previous) => [
        {
          incidentId: id,
          time: new Date().toLocaleString(),
          summary:
            data.summary ||
            data.conclusion ||
            data.message ||
            "Investigation completed",
          report: data,
        },
        ...previous.filter((item) => item.incidentId !== id),
      ]);
    } catch (err) {
      setError(
        err.message || "Could not connect to the investigation API."
      );
    } finally {
      setLoading(false);
    }
  }

  async function askAI(value = question) {
    const prompt = value.trim();

    if (!prompt || asking) return;

    setQuestion(prompt);
    setAsking(true);
    setAskError("");
    setAnswer("");

    try {
      const response = await fetch(
        `${API}/api/incidents/${encodeURIComponent(incidentId)}/ask`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: prompt }),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : `AI request failed (${response.status})`
        );
      }

      setAnswer(
        typeof data === "string"
          ? data
          : data.answer ||
              data.response ||
              data.message ||
              data.result ||
              data.content ||
              JSON.stringify(data, null, 2)
      );
    } catch (err) {
      setAskError(
        err.message || "Could not connect to the AI endpoint."
      );
    } finally {
      setAsking(false);
    }
  }

  function Section({ title, values, icon: Icon = Check }) {
    if (!Array.isArray(values) || values.length === 0) return null;

    return (
      <section className="report-section">
        <div className="report-section-heading">
          <span className="report-icon green">
            <Icon size={15} />
          </span>
          <h3>{title}</h3>
          <span className="item-count">{values.length}</span>
        </div>

        <div className="report-items">
          {values.map((item, index) => (
            <div className="report-item" key={index}>
              <span className="item-dot green" />
              <div>
                <p>{textOf(item)}</p>
                {item?.source && (
                  <small className="item-source">
                    Source: {item.source}
                  </small>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  function ServiceMap() {
    return (
      <div className="dependency-map">
        <button
          className={`service-node payment-node ${
            selectedService === "Payment" ? "selected" : ""
          }`}
          onClick={() => {
            setSelectedService("Payment");
            setQuestion(
              "Explain how the Payment service and deploy-042 relate to the incident."
            );
          }}
        >
          <span className="node-status" />
          <strong>Payment</strong>
          <small>DEPLOY FAILED</small>
        </button>

        <div className="dependency-link">
          <span>DEPENDS ON</span>
          <div className="link-line">
            <i />
          </div>
        </div>

        <button
          className={`service-node database-node ${
            selectedService === "Database" ? "selected" : ""
          }`}
          onClick={() => {
            setSelectedService("Database");
            setQuestion(
              "What evidence should I check to determine whether the Database contributed to this incident?"
            );
          }}
        >
          <span className="node-status" />
          <strong>Database</strong>
          <small>HEALTH UNKNOWN</small>
        </button>
      </div>
    );
  }

  function AskPanel() {
    return (
      <section className="ask-panel">
        <div className="ask-panel-header">
          <div className="ask-heading-icon">
            <Sparkles size={19} />
          </div>

          <div className="ask-heading-copy">
            <div className="eyebrow">
              <span className="eyebrow-rule" />
              AI INCIDENT ASSISTANT
            </div>
            <h2>Ask IncidentGraph AI</h2>
            <p>
              Ask a question about <strong>{incidentId}</strong>. Answers use
              your existing backend.
            </p>
          </div>

          <span className="ai-ready">
            <span className="online-dot" />
            AI READY
          </span>
        </div>

        <div className="question-chips">
          {suggestions.map((suggestion) => (
            <button
              className="question-chip"
              key={suggestion}
              disabled={asking}
              onClick={() => askAI(suggestion)}
            >
              <MessageCircle size={13} />
              {suggestion}
              <ArrowUpRight size={12} />
            </button>
          ))}
        </div>

        <form
          className="ask-form"
          onSubmit={(event) => {
            event.preventDefault();
            askAI();
          }}
        >
          <label htmlFor="incident-question">YOUR QUESTION</label>

          <div className="ask-input-row">
            <MessageCircle size={17} className="ask-input-icon" />

            <input
              id="incident-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a question about the incident..."
              disabled={asking}
            />

            <button
              type="submit"
              disabled={asking || !question.trim()}
            >
              {asking ? (
                "Thinking..."
              ) : (
                <>
                  Ask AI <Send size={14} />
                </>
              )}
            </button>
          </div>
        </form>

        {askError && (
          <div className="ai-error">
            <CircleAlert size={16} />
            {askError}
          </div>
        )}

        {answer && (
          <div className="ai-response">
            <Sparkles size={16} />
            <div>
              <strong>IncidentGraph AI</strong>
              <p>{answer}</p>
            </div>
          </div>
        )}
      </section>
    );
  }

  function ReportView() {
    if (!report) return null;

    return (
      <section className="report-panel">
        <div className="report-header">
          <div>
            <div className="eyebrow">
              <span className="eyebrow-rule" />
              INVESTIGATION REPORT
            </div>
            <h2>{report.incident_id || incidentId}</h2>
            <p>
              {summary ||
                "Review the evidence and next steps returned by the investigation."}
            </p>
          </div>

          <span className="status-badge">
            <Check size={13} />
            {report.status || "Completed"}
          </span>
        </div>

        <div className="report-tabs">
          {["Findings", "Evidence", "Tool history", "Raw response"].map(
            (item) => (
              <button
                key={item}
                className={tab === item ? "selected" : ""}
                onClick={() => setTab(item)}
              >
                {item}
              </button>
            )
          )}
        </div>

        {tab === "Findings" && (
          <div className="report-grid">
            <Section title="Observed facts" values={facts} />
            <Section
              title="Possible explanations"
              values={hypotheses}
              icon={Activity}
            />
            <Section
              title="Recommended checks"
              values={checks}
              icon={ArrowRight}
            />
            <Section
              title="Missing evidence"
              values={missing}
              icon={CircleAlert}
            />
          </div>
        )}

        {tab === "Evidence" && (
          <div className="report-grid">
            <Section
              title="Evidence returned"
              values={evidence}
              icon={Search}
            />
            <Section title="Observed facts" values={facts} />
            <Section
              title="Missing evidence"
              values={missing}
              icon={CircleAlert}
            />
          </div>
        )}

        {tab === "Tool history" && (
          <Section
            title="Agent tool history"
            values={toolHistory}
            icon={GitBranch}
          />
        )}

        {tab === "Raw response" && (
          <pre className="raw-response">
            {JSON.stringify(report, null, 2)}
          </pre>
        )}
      </section>
    );
  }

  return (
    <div className="app-shell">
      {/* SIDEBAR */}
      <aside className={`sidebar ${sidebarOpen ? "" : "sidebar-hidden"}`}>
        <a
          className="brand"
          href="#home"
          onClick={(event) => {
            event.preventDefault();
            go("Investigate");
          }}
        >
          <span className="brand-mark">
            <Network size={19} />
          </span>
          <span className="brand-name">
            IncidentGraph
            <small>AI INVESTIGATION</small>
          </span>
        </a>

        <button className="workspace-switch">
          <span className="workspace-avatar">I</span>
          <span className="workspace-info">
            <strong>My workspace</strong>
            <small>Local environment</small>
          </span>
          <ChevronDown size={14} />
        </button>

        <div className="nav-label">WORKSPACE</div>

        <nav className="side-nav">
          {navItems.map(({ label, icon: Icon }) => (
            <button
              key={label}
              className={`nav-item ${page === label ? "active" : ""}`}
              onClick={() => go(label)}
            >
              <Icon size={16} />
              <span>{label}</span>
              {page === label && <Check size={13} />}
            </button>
          ))}
        </nav>

        <div className="nav-label recent-label">RECENT</div>

        <button
          className="recent-incident"
          onClick={() => {
            setIncidentId("INC-1042");
            go("Investigate");
          }}
        >
          <span className="severity-dot" />
          <span>
            <strong>Checkout failures</strong>
            <small>INC-1042 · Critical</small>
          </span>
        </button>

        <div className="sidebar-bottom">
          <div className="connection-label">
            <span className="online-dot" />
            Local development
          </div>
          <div className="privacy-note">
            <ShieldCheck size={14} />
            Investigation through local API
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main
        className={`main-content ${sidebarOpen ? "" : "full-width"}`}
      >
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="sidebar-toggle"
              aria-label="Toggle sidebar"
              onClick={() => setSidebarOpen((open) => !open)}
            >
              <Menu size={17} />
            </button>
            <span>Workspace</span>
            <span className="breadcrumb-slash">/</span>
            <strong>{page}</strong>
          </div>

          <a
            className="api-link"
            href={`${API}/docs`}
            target="_blank"
            rel="noreferrer"
          >
            <span className="online-dot" />
            API docs <ArrowUpRight size={13} />
          </a>
        </header>

        <div className="page-container">
          {/* PAGE 1: INVESTIGATE */}
          {page === "Investigate" && (
            <>
              <section className="hero">
                <div className="eyebrow">
                  <span className="eyebrow-rule" />
                  INCIDENT INTELLIGENCE
                </div>

                <h1>
                  Make sense of
                  <br />
                  <em>what went wrong.</em>
                </h1>

                <p className="hero-description">
                  Follow the connections between incidents, services, and
                  deployments. Find evidence, understand possibilities, and
                  decide what to check next.
                </p>

                <form
                  className="investigation-form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    investigate();
                  }}
                >
                  <label htmlFor="incident-id">
                    START AN INVESTIGATION
                  </label>

                  <div className="input-row">
                    <Search size={17} className="search-icon" />

                    <input
                      id="incident-id"
                      value={incidentId}
                      onChange={(event) =>
                        setIncidentId(event.target.value)
                      }
                      placeholder="Enter an incident ID"
                    />

                    <button type="submit" disabled={loading}>
                      {loading ? (
                        "Investigating..."
                      ) : (
                        <>
                          Investigate <ArrowRight size={15} />
                        </>
                      )}
                    </button>
                  </div>

                  <div className="form-footer">
                    <span>Not sure where to start?</span>
                    <button
                      type="button"
                      className="example-link"
                      onClick={() => setIncidentId("INC-1042")}
                    >
                      Try INC-1042 <ArrowUpRight size={12} />
                    </button>
                  </div>
                </form>

                {error && (
                  <div className="error-message">
                    <CircleAlert size={16} />
                    <span>{error}</span>
                    <button onClick={() => setError("")}>
                      <X size={14} />
                    </button>
                  </div>
                )}
              </section>

              <section className="command-grid">
                <article className="command-card dependency-card">
                  <div className="command-card-heading">
                    <div>
                      <div className="eyebrow">
                        <span className="eyebrow-rule" />
                        LIVE INVESTIGATION
                      </div>
                      <h2>Service dependency map</h2>
                    </div>
                    <span className="command-tag">GRAPH VIEW</span>
                  </div>

                  <ServiceMap />

                  <p className="graph-note">
                    {selectedService === "Payment"
                      ? "Payment is the affected service; deploy-042 failed."
                      : "Database health is unknown; verify it before confirming a root cause."}
                  </p>

                  <button
                    className="page-action"
                    onClick={() => go("Service graph")}
                  >
                    Open service graph <ArrowRight size={15} />
                  </button>
                </article>

                <article className="command-card timeline-card">
                  <div className="command-card-heading">
                    <div>
                      <div className="eyebrow">
                        <span className="eyebrow-rule" />
                        EVENT SEQUENCE
                      </div>
                      <h2>Incident timeline</h2>
                    </div>
                    <Clock3 size={17} />
                  </div>

                  <div className="timeline">
                    <div className="timeline-event critical-event">
                      <span className="timeline-marker">
                        <CircleAlert size={13} />
                      </span>
                      <div>
                        <strong>Payment error alert</strong>
                        <p>Error rate exceeded 20%</p>
                      </div>
                      <span className="timeline-state">ALERT</span>
                    </div>

                    <div className="timeline-event critical-event">
                      <span className="timeline-marker">
                        <GitBranch size={13} />
                      </span>
                      <div>
                        <strong>Deployment failed</strong>
                        <p>deploy-042 · version 2.4.0</p>
                      </div>
                      <span className="timeline-state">FAILED</span>
                    </div>

                    <div className="timeline-event next-event">
                      <span className="timeline-marker">
                        <Search size={13} />
                      </span>
                      <div>
                        <strong>Verify database health</strong>
                        <p>Recommended next evidence check</p>
                      </div>
                      <span className="timeline-state">NEXT</span>
                    </div>
                  </div>

                  <button
                    className="page-action"
                    onClick={() => {
                      setQuestion(
                        "What should I check next after the deployment failure?"
                      );
                      document
                        .getElementById("incident-question")
                        ?.focus();
                    }}
                  >
                    Ask about next steps <ArrowRight size={15} />
                  </button>
                </article>
              </section>

              <AskPanel />
              <ReportView />
            </>
          )}

          {/* PAGE 2: INCIDENTS */}
          {page === "Incidents" && (
            <section className="page-view">
              <div className="eyebrow">
                <span className="eyebrow-rule" />
                INCIDENT MANAGEMENT
              </div>

              <h1 className="page-heading">Incidents</h1>

              <p className="page-description">
                Browse the incident data available in your current
                workspace and open an investigation.
              </p>

              <div className="report-grid">
                <article className="command-card">
                  <div className="eyebrow">KNOWN INCIDENTS</div>
                  <h2>01</h2>
                  <p>Checkout failures</p>
                </article>

                <article className="command-card">
                  <div className="eyebrow">AFFECTED SERVICE</div>
                  <h2>Payment</h2>
                  <p>Deployment deploy-042 · version 2.4.0</p>
                </article>
              </div>

              <article className="command-card page-card">
                <div className="command-card-heading">
                  <div>
                    <div className="eyebrow">
                      <span className="eyebrow-rule" />
                      INCIDENT REGISTER
                    </div>
                    <h2>Checkout failures</h2>
                    <p>
                      INC-1042 · Critical · Payment error rate exceeded
                      20%.
                    </p>
                  </div>
                  <span className="status-badge">Critical</span>
                </div>

                <button
                  className="page-action"
                  onClick={() => {
                    setIncidentId("INC-1042");
                    go("Investigate");
                  }}
                >
                  Open investigation <ArrowRight size={15} />
                </button>
              </article>
            </section>
          )}

          {/* PAGE 3: SERVICE GRAPH */}
          {page === "Service graph" && (
            <section className="page-view">
              <div className="eyebrow">
                <span className="eyebrow-rule" />
                DEPENDENCY EXPLORER
              </div>

              <h1 className="page-heading">Service graph</h1>

              <p className="page-description">
                Explore the known relationships connected to the checkout
                failure. Select a service to prepare a question for the AI.
              </p>

              <article className="command-card page-card">
                <div className="command-card-heading">
                  <div>
                    <div className="eyebrow">
                      <span className="eyebrow-rule" />
                      SERVICE RELATIONSHIPS
                    </div>
                    <h2>Dependency map</h2>
                  </div>
                  <span className="command-tag">2 SERVICES</span>
                </div>

                <ServiceMap />

                <p className="graph-note">
                  <strong>{selectedService}</strong>:{" "}
                  {selectedService === "Payment"
                    ? "The payment service is associated with deploy-042 (version 2.4.0) and elevated checkout errors."
                    : "Database health has not been confirmed. Check its metrics and logs before concluding it caused the incident."}
                </p>

                <button
                  className="page-action"
                  onClick={() => go("Investigate")}
                >
                  Ask AI about this service <ArrowRight size={15} />
                </button>
              </article>
            </section>
          )}

          {/* PAGE 4: HISTORY */}
          {page === "History" && (
            <section className="page-view">
              <div className="eyebrow">
                <span className="eyebrow-rule" />
                INVESTIGATION ACTIVITY
              </div>

              <h1 className="page-heading">History</h1>

              <p className="page-description">
                Review investigations completed during this browser
                session.
              </p>

              <article className="command-card page-card">
                <div className="command-card-heading">
                  <div>
                    <div className="eyebrow">
                      <span className="eyebrow-rule" />
                      RECENT ACTIVITY
                    </div>
                    <h2>Investigation history</h2>
                  </div>

                  <button
                    className="page-action subtle"
                    onClick={() => setHistory([])}
                    disabled={!history.length}
                  >
                    <RotateCcw size={14} />
                    Clear
                  </button>
                </div>

                {!history.length ? (
                  <p className="empty-note">
                    No investigations recorded yet. Run an investigation
                    and it will appear here. This history is kept only in
                    the current browser session.
                  </p>
                ) : (
                  history.map((item, index) => (
                    <div
                      className="report-item history-row"
                      key={`${item.incidentId}-${index}`}
                    >
                      <span className="item-dot green" />

                      <div>
                        <strong>{item.incidentId}</strong>
                        <p>{item.summary}</p>
                        <small>{item.time}</small>
                      </div>

                      <button
                        className="page-action subtle"
                        onClick={() => {
                          setIncidentId(item.incidentId);
                          setReport(item.report);
                          setTab("Findings");
                          go("Investigate");
                        }}
                      >
                        View report <ArrowRight size={14} />
                      </button>
                    </div>
                  ))
                )}
              </article>
            </section>
          )}

          <footer className="page-footer">
            <span>
              INCIDENTGRAPH <b>AI</b>
            </span>
            <span>GRAPH-POWERED INCIDENT INVESTIGATION</span>
            <a
              href={`${API}/docs`}
              target="_blank"
              rel="noreferrer"
            >
              API documentation <ArrowUpRight size={12} />
            </a>
          </footer>
        </div>
      </main>

      {/* Small layout fixes that do not require changing App.css */}
      <style>{`
        .sidebar-hidden {
          transform: translateX(-100%);
        }

        .main-content.full-width {
          margin-left: 0;
        }

        .page-view {
          min-height: 65vh;
          padding-top: 6px;
        }

        .page-heading {
          font-size: clamp(34px, 4vw, 48px);
          letter-spacing: -1.8px;
          margin: 16px 0 8px;
        }

        .page-description {
          color: var(--muted, #91a3bc);
          line-height: 1.7;
          max-width: 720px;
          margin: 0 0 28px;
        }

        .page-card {
          margin-top: 18px;
        }

        .page-action {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 10px 13px;
          background: #5ce6ad;
          color: #071b14;
          border: 0;
          border-radius: 7px;
          font-weight: 700;
          font-size: 12px;
          cursor: pointer;
          margin-top: 12px;
        }

        .page-action.subtle {
          background: #142233;
          color: #d8e5f4;
          border: 1px solid #2a3b50;
        }

        .page-action:disabled {
          opacity: 0.45;
          cursor: not-allowed;
        }

        .service-node {
          cursor: pointer;
        }

        .service-node.selected {
          outline: 1px solid #5ce6ad;
          outline-offset: 2px;
        }

        .history-row {
          align-items: center;
        }

        .history-row > div {
          flex: 1;
          min-width: 0;
        }

        .history-row p {
          margin: 5px 0;
          overflow-wrap: anywhere;
        }

        .history-row small,
        .empty-note {
          color: #91a3bc;
        }

        .empty-note {
          line-height: 1.7;
        }

        .ai-response {
          display: flex;
          gap: 10px;
          margin-top: 14px;
          padding: 14px;
          border: 1px solid #245444;
          background: #10221f;
          border-radius: 9px;
        }

        .ai-response p {
          white-space: pre-wrap;
          overflow-wrap: anywhere;
          line-height: 1.65;
        }

        .ai-error {
          display: flex;
          gap: 9px;
          padding: 12px;
          margin-top: 12px;
          color: #ffb5bd;
          background: #2a171d;
          border: 1px solid #5b303b;
          border-radius: 8px;
        }

        .report-item p {
          overflow-wrap: anywhere;
        }

        @media (max-width: 600px) {
          .history-row {
            flex-wrap: wrap;
          }
        }
      `}</style>
    </div>
  );
}

export default App;