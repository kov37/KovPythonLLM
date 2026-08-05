import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Metrics = {
  modelCalls: number;
  meanLatencyMs: number | null;
  inputTokens: number | null;
  outputTokens: number | null;
  latencyLabel: string;
  tokenLabel: string;
};

type Overview = {
  operationMode: "continuous";
  workConserving: boolean;
  activeRuns: number;
  testPassingRuns: number;
  approvedCandidates: number;
  rejectedCandidates: number;
  totalEvents: number;
  latestDecision: Record<string, unknown> | null;
  latestDecisionActive: boolean;
  latestDecisionAt: string | null;
  latestOutcome: {type: string; payload: Record<string, unknown>} | null;
  metrics: Metrics;
};

type TimelineEvent = {
  eventId: string;
  runId: string;
  sequence: number;
  type: string;
  actor: string;
  at: string;
  payload: Record<string, unknown>;
};

type ControlStatus = { paused: boolean; emergencyStopped: boolean };

const EMPTY: Overview = {
  operationMode: "continuous",
  workConserving: true,
  activeRuns: 0,
  testPassingRuns: 0,
  approvedCandidates: 0,
  rejectedCandidates: 0,
  totalEvents: 0,
  latestDecision: null,
  latestDecisionActive: false,
  latestDecisionAt: null,
  latestOutcome: null,
  metrics: { modelCalls: 0, meanLatencyMs: null, inputTokens: null, outputTokens: null, latencyLabel: "unavailable", tokenLabel: "unavailable" },
};

function App() {
  const [token, setToken] = useState(localStorage.getItem("kov-token") ?? "");
  const [overview, setOverview] = useState<Overview>(EMPTY);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [control, setControl] = useState<ControlStatus>({ paused: false, emergencyStopped: false });
  const [connected, setConnected] = useState(false);
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  useEffect(() => {
    if (!token) return;
    let active = true;
    const refresh = async () => {
      try {
        const [summary, timeline, controlStatus] = await Promise.all([
          fetch("/api/overview", { headers }),
          fetch("/api/timeline?limit=80", { headers }),
          fetch("/api/control", { headers }),
        ]);
        if (!summary.ok || !timeline.ok || !controlStatus.ok) throw new Error("authentication failed");
        if (active) {
          setOverview(await summary.json());
          setEvents(await timeline.json());
          setControl(await controlStatus.json());
          setConnected(true);
        }
      } catch {
        if (active) setConnected(false);
      }
    };
    refresh();
    const interval = window.setInterval(refresh, 2500);
    return () => { active = false; window.clearInterval(interval); };
  }, [headers, token]);

  if (!token || !connected) {
    return <main className="auth-shell">
      <section className="auth-card">
        <div className="mark">K</div>
        <p className="eyebrow">LOCAL CONTROL PLANE</p>
        <h1>Observe the machine<br/><i>thinking in evidence.</i></h1>
        <p className="muted">Paste the local operator token from <code>.kov-state/control/operator.token</code>. It is sent only to KOV on this computer at localhost.</p>
        <input aria-label="Operator token" type="password" value={token} onChange={(event) => setToken(event.target.value)} placeholder="Local operator token" />
        <button onClick={() => { localStorage.setItem("kov-token", token); location.reload(); }}>Enter studio</button>
        {token && <span className="error">Waiting for a valid local token…</span>}
      </section>
    </main>;
  }

  const decision = overview.latestDecisionActive ? overview.latestDecision : null;
  return <div className="app-shell">
    <header>
      <div className="brand"><span className="mark small">K</span><div><b>KOV</b><small>Autonomous Studio</small></div></div>
      <div className={`live ${control.paused || control.emergencyStopped ? "blocked" : ""}`}><span/> {control.emergencyStopped ? "emergency stopped" : control.paused ? "paused" : `${overview.operationMode} · evidence-gated`} · localhost</div>
    </header>
    <main>
      <section className="hero">
        <div><p className="eyebrow">SYSTEM PULSE</p><h1>Calm control.<br/><i>Visible reasoning.</i></h1></div>
        <div className="hero-state"><small>ACTIVE PIPELINES</small><strong>{overview.activeRuns.toString().padStart(2, "0")}</strong><span>{overview.totalEvents} durable events</span></div>
      </section>
      <section className="metrics" aria-label="Runtime metrics">
        <Metric label="Model calls" value={overview.metrics.modelCalls} note="measured" />
        <Metric label="Mean decision" value={overview.metrics.meanLatencyMs ? `${(overview.metrics.meanLatencyMs / 1000).toFixed(2)}s` : "—"} note={overview.metrics.latencyLabel} />
        <Metric label="Input tokens" value={overview.metrics.inputTokens ?? "—"} note={overview.metrics.tokenLabel} />
        <Metric label="Output tokens" value={overview.metrics.outputTokens ?? "—"} note={overview.metrics.tokenLabel} />
      </section>
      <section className="grid">
        <article className="decision panel">
          <p className="eyebrow">{overview.latestDecisionActive ? "LATEST ACTIVE MODEL CLAIM · NOT YET VERIFIED" : "SYSTEM STATUS · NO ACTIVE MODEL CLAIM"}</p>
          <h2>{String(decision?.summary ?? "KOV is quietly collecting deterministic evidence.")}</h2>
          <dl>
            <div><dt>Expected outcome</dt><dd>{String(decision?.expected_outcome ?? "No model action required")}</dd></div>
            <div><dt>Action</dt><dd>{String(decision?.action_kind ?? "idle")}</dd></div>
            <div><dt>Uncertainty</dt><dd>{String(decision?.uncertainty ?? "unavailable")}</dd></div>
          </dl>
          <div className="verified-outcome"><small>LATEST VERIFIED OUTCOME</small><b>{overview.latestOutcome?.type.replaceAll(".", " ") ?? "No candidate has cleared the new evidence gate"}</b><span>{String(overview.latestOutcome?.payload.summary ?? "Model activity alone is not counted as value.")}</span></div>
        </article>
        <article className="panel outcomes">
          <p className="eyebrow">VERIFICATION FUNNEL</p>
          <div><strong>{overview.testPassingRuns}</strong><span>test loops passed</span></div>
          <div><strong>{overview.approvedCandidates}</strong><span>candidates approved</span></div>
          <div><strong>{overview.rejectedCandidates}</strong><span>candidates rejected</span></div>
        </article>
      </section>
      <section className="legend panel" aria-label="How to interpret KOV activity">
        <p className="eyebrow">HOW TO READ THIS</p>
        <div><b>Model claim</b><span>A proposal, not proof.</span></div>
        <div><b>Action authorized</b><span>Safe to execute, not necessarily valuable.</span></div>
        <div><b>Evidence gate</b><span>Category-specific deterministic proof exists.</span></div>
        <div><b>Observer approved</b><span>Clean-context review found no concrete blocker.</span></div>
        <div><b>Candidate published</b><span>A draft PR exists; Research Tutor main is unchanged.</span></div>
      </section>
      <section className="timeline panel">
        <div className="section-head"><div><p className="eyebrow">CAUSAL TIMELINE</p><h2>What happened, and why</h2></div><span>{events.length} recent events</span></div>
        <ol>{events.map((event) => <li key={event.eventId}>
          <time>{new Date(event.at).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"})}</time>
          <span className={`dot ${event.type.includes("failed") || event.type.includes("rejected") ? "warn" : ""}`}/>
          <div><b>{event.type.replaceAll(".", " ")}</b><small>{event.actor} · run {event.runId.slice(-8)} · #{event.sequence}</small><p>{eventSummary(event)}</p></div>
        </li>)}</ol>
      </section>
    </main>
  </div>;
}

function Metric({ label, value, note }: {label: string; value: string | number; note: string}) {
  return <article><small>{label}</small><strong>{value}</strong><span>{note}</span></article>;
}

function eventSummary(event: TimelineEvent): string {
  const value = event.payload.summary ?? event.payload.reason ?? event.payload.status ?? event.payload.kind;
  return value ? String(value) : "Typed event recorded";
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
