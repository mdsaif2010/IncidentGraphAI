
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
  Network,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function getItems(data, keys) {
  for (const key of keys) {
    const value = data?.[key];
    if (Array.isArray(value)) return value;
    if (typeof value === "string" && value.trim()) return [value];
  }
  return [];
}

function itemText(item) {
  if (typeof item === "string" || typeof item === "number") {
    return String(item);
  }

  if (item && typeof item === "object") {
    return (
      item.description ||
      item.detail ||
      item.reason ||
      item.finding ||
      item.evidence ||
      item.recommendation ||
      item.action ||
      item.name ||
      item.message ||
      JSON.stringify(item)
    );
  }

  return String(item ?? "");
}

function ReportSection({ title, icon: Icon, items, tone }) {
  if (!items.length) return null;

  return (
    <section className="report-section">
      <div className="report-section-heading">
        <span className={`report-icon ${tone}`}>
          <Icon size={15} />
        </span>
        <h3>{title}</h3>
        <span className="item-count">{items.length}</span>
      </div>

      <div className="report-items">
        {items.map((item, index) => (
          <div className="report-item" key={`${title}-${index}`}>
            <span className={`item-dot ${tone}`} />
            <div>
              <p>{itemText(item)}</p>
              {typeof item === "object" && item?.source && (
                <span className="item-source">Source: {item.source}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function App() {
  const [incidentId, setIncidentId] = useState("INC-1042");
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [activeNav, setActiveNav] = useState("Investigate");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState("Findings");

  async function investigate(value = incidentId) {
    const id = value.trim();
    if (!id || loading) return;

    setIncidentId(id);
    setLoading(true);
    setError("");
    setReport(null);
    setActiveNav("Investigate");

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
            : `Investigation failed (${response.status}).`
        );
      }

      setReport(data);
      setActiveTab("Findings");

      requestAnimationFrame(() => {
        document.getElementById("investigation-report")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    } catch (err) {
      setError(
        err.message || "Could not connect to the local investigation API."
      );
    } finally {
      setLoading(false);
    }
  }

  const facts = getItems(report, ["facts", "observations", "findings"]);
  const hypotheses = getItems(report, [
    "hypotheses",
    "possible_causes",
    "potential_causes",
  ]);
  const missing = getItems(report, [
    "missing_evidence",
    "evidence_gaps",
    "unknowns",
  ]);
  const nextChecks = getItems(report, [
    "next_checks",
    "recommended_checks",
    "recommendations",
    "next_steps",
  ]);
  const evidence = getItems(report, ["evidence", "evidence_items"]);
  const history = getItems(report, ["tool_history", "tool_calls", "steps"]);

  const summary =
    report?.summary ||
    report?.conclusion ||
    report?.message ||
    report?.investigation_summary;

  const navItems = [
    { label: "Investigate", icon: Sparkles },
    { label: "Incidents", icon: Layers3 },
    { label: "Service graph", icon: Network },
    { label: "History", icon: Clock3 },
  ];

  function selectNav(label) {
    setActiveNav(label);
    if (label === "Investigate") {
      setError("");
    } else {
      setError(`${label} is not available yet. Use Investigate to run an analysis.`);
    }
  }

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <aside className="sidebar">
          <a className="brand" href="#" onClick={(e) => e.preventDefault()}>
            <span className="brand-mark"><Network size={19} /></span>
            <span className="brand-name">
              IncidentGraph
              <small>AI INVESTIGATION</small>
            </span>
          </a>

          <button className="workspace-switch" onClick={() => setError("")}>
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
                className={`nav-item ${activeNav === label ? "active" : ""}`}
                onClick={() => selectNav(label)}
              >
                <Icon size={16} strokeWidth={1.8} />
                <span>{label}</span>
                {label === "Investigate" && <span className="nav-key">↵</span>}
              </button>
            ))}
          </nav>

          <div className="nav-label recent-label">RECENT</div>
          <button
            className="recent-incident"
            onClick={() => {
              setIncidentId("INC-1042");
              setError("");
              setActiveNav("Investigate");
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
      )}

      <main className={`main-content ${sidebarOpen ? "" : "full-width"}`}>
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="sidebar-toggle"
              aria-label="Toggle sidebar"
              onClick={() => setSidebarOpen((value) => !value)}
            >
              <Menu size={17} />
            </button>
            <span>Workspace</span>
            <span className="breadcrumb-slash">/</span>
            <strong>{activeNav}</strong>
          </div>

          <a
            className="api-link"
            href={`${API}/docs`}
            target="_blank"
            rel="noreferrer"
          >
            <span className="online-dot" />
            API docs
            <ArrowUpRight size={13} />
          </a>
        </header>

        <div className="page-container">
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
              deployments. Find the evidence, understand the possibilities,
              and decide what to check next.
            </p>

            <form
              className="investigation-form"
              onSubmit={(event) => {
                event.preventDefault();
                investigate();
              }}
            >
              <label htmlFor="incident-id">START AN INVESTIGATION</label>

              <div className="input-row">
                <Search size={17} className="search-icon" />
                <input
                  id="incident-id"
                  value={incidentId}
                  onChange={(event) => setIncidentId(event.target.value)}
                  placeholder="Enter an incident ID"
                />
                <button type="submit" disabled={loading}>
                  {loading ? (
                    <>
                      <span className="spinner" /> Investigating
                    </>
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
                  onClick={() => {
                    setIncidentId("INC-1042");
                    setError("");
                  }}
                >
                  Try INC-1042 <ArrowUpRight size={12} />
                </button>
              </div>
            </form>

            {error && (
              <div className="error-message">
                <CircleAlert size={16} />
                <span>{error}</span>
                <button onClick={() => setError("")} aria-label="Dismiss">
                  <X size={14} />
                </button>
              </div>
            )}

            {loading && (
              <div className="loading-message">
                <span className="loading-symbol"><Sparkles size={18} /></span>
                <div>
                  <strong>Investigating {incidentId}</strong>
                  <p>Tracing dependencies and examining available evidence…</p>
                </div>
              </div>
            )}
          </section>

          {report && (
            <section className="report-panel" id="investigation-report">
              <div className="report-header">
                <div>
                  <div className="eyebrow">
                    <span className="eyebrow-rule" />
                    INVESTIGATION REPORT
                  </div>
                  <h2>{report.incident_id || incidentId}</h2>
                  <p>Review what the agent observed and what remains uncertain.</p>
                </div>
                <span className="status-badge">
                  <Check size={13} />
                  {report.status || "Completed"}
                </span>
              </div>

              {summary && <div className="summary-box">{itemText(summary)}</div>}

              <div className="report-tabs">
                {["Findings", "Evidence", "Tool history", "Raw response"].map((tab) => (
                  <button
                    key={tab}
                    className={activeTab === tab ? "selected" : ""}
                    onClick={() => setActiveTab(tab)}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {activeTab === "Findings" && (
                <div className="report-grid">
                  <ReportSection title="Observed facts" icon={Check} items={facts} tone="green" />
                  <ReportSection title="Possible explanations" icon={Activity} items={hypotheses} tone="terracotta" />
                  <ReportSection title="Recommended checks" icon={ArrowRight} items={nextChecks} tone="blue" />
                  <ReportSection title="Missing evidence" icon={CircleAlert} items={missing} tone="amber" />
                  {!facts.length && !hypotheses.length && !nextChecks.length && !missing.length && (
                    <pre className="raw-response">{JSON.stringify(report, null, 2)}</pre>
                  )}
                </div>
              )}

              {activeTab === "Evidence" && (
                <div className="report-grid">
                  <ReportSection title="Evidence returned" icon={Search} items={evidence} tone="blue" />
                  <ReportSection title="Observed facts" icon={Check} items={facts} tone="green" />
                  <ReportSection title="Missing evidence" icon={CircleAlert} items={missing} tone="amber" />
                  {!evidence.length && !facts.length && !missing.length && (
                    <p className="empty-note">No separate evidence list was returned. Check the raw response for details.</p>
                  )}
                </div>
              )}

              {activeTab === "Tool history" && (
                <div className="report-grid">
                  <ReportSection title="Agent tool history" icon={GitBranch} items={history} tone="terracotta" />
                  {!history.length && (
                    <p className="empty-note">No separate tool-history list was returned.</p>
                  )}
                </div>
              )}

              {activeTab === "Raw response" && (
                <pre className="raw-response">{JSON.stringify(report, null, 2)}</pre>
              )}
            </section>
          )}

          <section className="how-it-works">
            <div className="section-header">
              <div>
                <div className="eyebrow">
                  <span className="eyebrow-rule" />
                  HOW IT WORKS
                </div>
                <h2>A clearer path from <em>signal to solution.</em></h2>
              </div>
              <span className="section-number">01 — 03</span>
            </div>

            <div className="feature-grid">
              <article className="feature-card">
                <div className="feature-top">
                  <span className="feature-icon"><GitBranch size={18} /></span>
                  <span className="feature-number">01</span>
                </div>
                <h3>Trace connections</h3>
                <p>Explore service dependencies to understand which systems may be related to the incident.</p>
                <div className="feature-foot">SERVICE RELATIONSHIPS</div>
              </article>

              <article className="feature-card">
                <div className="feature-top">
                  <span className="feature-icon"><Search size={18} /></span>
                  <span className="feature-number">02</span>
                </div>
                <h3>Examine evidence</h3>
                <p>Connect incident details with deployment records while keeping facts separate from theories.</p>
                <div className="feature-foot">EVIDENCE FIRST</div>
              </article>

              <article className="feature-card">
                <div className="feature-top">
                  <span className="feature-icon"><Sparkles size={18} /></span>
                  <span className="feature-number">03</span>
                </div>
                <h3>Find the next step</h3>
                <p>Surface missing information and practical checks without overstating what is known.</p>
                <div className="feature-foot">AI-ASSISTED REASONING</div>
              </article>
            </div>
          </section>

          <footer className="page-footer">
            <span>INCIDENTGRAPH <b>AI</b></span>
            <span>GRAPH-POWERED INCIDENT INVESTIGATION</span>
            <a href={`${API}/docs`} target="_blank" rel="noreferrer">
              API documentation <ArrowUpRight size={12} />
            </a>
          </footer>
        </div>
      </main>
    </div>
  );
}
