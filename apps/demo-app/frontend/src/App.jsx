import React, { useState, useCallback } from 'react';

const API_BASE = '/api';

const GRAFANA_BASE = window.GRAFANA_URL || 'https://grafana.86.38.238.224.nip.io';

const styles = {
  container: { maxWidth: 900, margin: '0 auto', padding: '2rem 1rem' },
  header: { marginBottom: '2rem', borderBottom: '1px solid #334155', paddingBottom: '1rem' },
  title: { fontSize: '1.8rem', fontWeight: 700, color: '#38bdf8' },
  subtitle: { color: '#94a3b8', marginTop: '0.25rem', fontSize: '0.9rem' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', marginBottom: '2rem' },
  card: (color) => ({
    background: '#1e293b', borderRadius: 8, padding: '1.5rem',
    border: `1px solid ${color}33`, display: 'flex', flexDirection: 'column', gap: '0.75rem',
  }),
  cardTitle: (color) => ({ fontSize: '1rem', fontWeight: 600, color }),
  cardDesc: { fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.4 },
  label: { fontSize: '0.75rem', color: '#94a3b8' },
  slider: { width: '100%', accentColor: '#38bdf8' },
  sliderVal: { fontSize: '0.8rem', color: '#38bdf8', fontWeight: 600 },
  button: (color, disabled) => ({
    padding: '0.6rem 1.2rem', borderRadius: 6, border: 'none', cursor: disabled ? 'not-allowed' : 'pointer',
    fontWeight: 600, fontSize: '0.85rem', background: disabled ? '#334155' : color,
    color: disabled ? '#64748b' : '#fff', transition: 'opacity 0.15s',
    opacity: disabled ? 0.6 : 1,
  }),
  history: { background: '#1e293b', borderRadius: 8, padding: '1rem', maxHeight: 400, overflowY: 'auto' },
  historyTitle: { fontSize: '0.9rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.75rem' },
  entry: (status) => ({
    background: status === 'ok' ? '#0f2a1e' : '#2a0f0f',
    border: `1px solid ${status === 'ok' ? '#16a34a44' : '#dc262644'}`,
    borderRadius: 6, padding: '0.75rem', marginBottom: '0.5rem', fontSize: '0.8rem',
  }),
  entryHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' },
  badge: (status) => ({
    padding: '0.1rem 0.5rem', borderRadius: 4, fontWeight: 700, fontSize: '0.7rem',
    background: status === 'ok' ? '#16a34a' : '#dc2626', color: '#fff',
  }),
  traceLink: { color: '#38bdf8', textDecoration: 'none', fontSize: '0.75rem' },
  mono: { fontFamily: 'monospace', color: '#a5f3fc', fontSize: '0.75rem', wordBreak: 'break-all' },
  emptyState: { color: '#475569', textAlign: 'center', padding: '2rem', fontSize: '0.85rem' },
  links: { display: 'flex', gap: '1rem', marginTop: '2rem', flexWrap: 'wrap' },
  extLink: {
    padding: '0.5rem 1rem', background: '#1e293b', borderRadius: 6,
    color: '#38bdf8', textDecoration: 'none', fontSize: '0.8rem', border: '1px solid #334155',
  },
};

function ScenarioCard({ title, description, color, onFire, loading, children }) {
  return (
    <div style={styles.card(color)}>
      <div style={styles.cardTitle(color)}>{title}</div>
      <div style={styles.cardDesc}>{description}</div>
      {children}
      <button style={styles.button(color, loading)} onClick={onFire} disabled={loading}>
        {loading ? 'Running…' : 'Fire'}
      </button>
    </div>
  );
}

function HistoryEntry({ entry }) {
  // Grafana 10+ Explore deep-link format using panes
  const panes = {
    p1: {
      datasource: 'tempo',
      queries: [{ refId: 'A', queryType: 'traceId', query: entry.trace_id }],
      range: { from: 'now-1h', to: 'now' },
    },
  };
  const traceUrl = `${GRAFANA_BASE}/explore?panes=${encodeURIComponent(JSON.stringify(panes))}&schemaVersion=1&orgId=1`;

  return (
    <div style={styles.entry(entry.status)}>
      <div style={styles.entryHeader}>
        <span style={{ fontWeight: 600, color: '#e2e8f0' }}>{entry.scenario}</span>
        <span style={styles.badge(entry.status)}>{entry.status.toUpperCase()}</span>
      </div>
      <div style={styles.mono}>trace_id: {entry.trace_id}</div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.4rem' }}>
        <span style={{ color: '#64748b' }}>{entry.duration_ms} ms</span>
        <a href={traceUrl} target="_blank" rel="noreferrer" style={styles.traceLink}>
          View in Grafana →
        </a>
      </div>
      {entry.message && <div style={{ color: '#94a3b8', marginTop: '0.25rem' }}>{entry.message}</div>}
    </div>
  );
}

export default function App() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState({ success: false, error: false, slow: false });
  const [slowDelay, setSlowDelay] = useState(2000);

  const fire = useCallback(async (scenario, body = {}) => {
    setLoading((l) => ({ ...l, [scenario]: true }));
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE}/simulate/${scenario}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      const payload = res.ok ? data : data.detail;
      setHistory((h) => [
        { ...payload, scenario, status: res.ok ? 'ok' : 'error', ts: new Date().toISOString() },
        ...h,
      ].slice(0, 50));
    } catch (err) {
      setHistory((h) => [
        { scenario, status: 'error', trace_id: 'n/a', span_id: 'n/a',
          duration_ms: Math.round(performance.now() - start), message: err.message, ts: new Date().toISOString() },
        ...h,
      ].slice(0, 50));
    } finally {
      setLoading((l) => ({ ...l, [scenario]: false }));
    }
  }, []);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.title}>Observability Playground</div>
        <div style={styles.subtitle}>
          Fire scenarios → traces appear in Grafana Tempo · logs in Loki · metrics in Prometheus
        </div>
      </div>

      <div style={styles.grid}>
        <ScenarioCard
          title="✅ Success"
          description="Fires a normal request with a parent + child span. Expect HTTP 200 and a green trace in Tempo."
          color="#16a34a"
          loading={loading.success}
          onFire={() => fire('success')}
        />

        <ScenarioCard
          title="💥 Error"
          description="Raises an exception inside a span. Expect HTTP 500, a red/error span, and an error log line in Loki."
          color="#dc2626"
          loading={loading.error}
          onFire={() => fire('error', { error_message: 'Demo error — check Tempo for the exception event' })}
        />

        <ScenarioCard
          title="🐢 Slow Request"
          description="Sleeps inside a 'slow-database-query' child span. Use the slider to control delay."
          color="#d97706"
          loading={loading.slow}
          onFire={() => fire('slow', { delay_ms: slowDelay })}
        >
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={styles.label}>Delay</span>
              <span style={styles.sliderVal}>{(slowDelay / 1000).toFixed(1)} s</span>
            </div>
            <input
              type="range" min={500} max={10000} step={500}
              value={slowDelay} onChange={(e) => setSlowDelay(Number(e.target.value))}
              style={styles.slider}
            />
          </div>
        </ScenarioCard>
      </div>

      <div style={styles.history}>
        <div style={styles.historyTitle}>Request history (last 50)</div>
        {history.length === 0
          ? <div style={styles.emptyState}>No requests yet — fire a scenario above.</div>
          : history.map((e, i) => <HistoryEntry key={i} entry={e} />)
        }
      </div>

      <div style={styles.links}>
        <a href={`${GRAFANA_BASE}/explore`} target="_blank" rel="noreferrer" style={styles.extLink}>Grafana Explore</a>
        <a href={`${GRAFANA_BASE}/dashboards`} target="_blank" rel="noreferrer" style={styles.extLink}>Dashboards</a>
        <a href="/docs" target="_blank" rel="noreferrer" style={styles.extLink}>API Docs (Swagger)</a>
      </div>
    </div>
  );
}
