import { useEffect, useState } from "react";

const ATTESTATION_API = import.meta.env.VITE_ATTESTATION_API ?? "http://localhost:8100";
const DETECTOR_API = import.meta.env.VITE_DETECTOR_API ?? "http://localhost:8200";
const UNLEARNING_API = import.meta.env.VITE_UNLEARNING_API ?? "http://localhost:8300";

interface Attestation {
  dataset_id: string;
  root_hash: string;
  chunk_count: number;
  attested_at: number;
}

interface SimResult {
  label: string;
  verified: boolean;
  reason?: string;
}

async function safeJSON<T>(url: string, options: RequestInit, fallback: T): Promise<T> {
  try {
    const res = await fetch(url, options);
    if (!res.ok) return fallback;
    return await res.json();
  } catch {
    return fallback;
  }
}

export default function App() {
  const [attestations, setAttestations] = useState<Attestation[]>([]);
  const [simResults, setSimResults] = useState<SimResult[]>([]);
  const [simRunning, setSimRunning] = useState(false);
  const [servicesUp, setServicesUp] = useState({ attestation: false, detector: false, unlearning: false });

  useEffect(() => {
    const poll = async () => {
      const [a, attHealth, detHealth, unlHealth] = await Promise.all([
        safeJSON<Attestation[]>(`${ATTESTATION_API}/attestations`, {}, []),
        fetch(`${ATTESTATION_API}/health`).then((r) => r.ok).catch(() => false),
        fetch(`${DETECTOR_API}/health`).then((r) => r.ok).catch(() => false),
        fetch(`${UNLEARNING_API}/health`).then((r) => r.ok).catch(() => false),
      ]);
      setAttestations(a);
      setServicesUp({ attestation: attHealth, detector: detHealth, unlearning: unlHealth });
    };
    poll();
    const interval = setInterval(poll, 8000);
    return () => clearInterval(interval);
  }, []);

  async function runPoisoningSimulation() {
    setSimRunning(true);
    setSimResults([]);
    const datasetId = `sim-${Date.now()}`;
    const cleanChunks = ["record_1", "record_2", "record_3", "record_4", "record_5"];

    const results: SimResult[] = [];

    await safeJSON(
      `${ATTESTATION_API}/attest`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_id: datasetId, chunks: cleanChunks }),
      },
      null
    );

    const cleanCheck = await safeJSON<{ verified: boolean }>(
      `${ATTESTATION_API}/verify`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_id: datasetId, chunks: cleanChunks }),
      },
      { verified: false }
    );
    results.push({ label: "Verify unmodified dataset", verified: cleanCheck.verified });

    const poisonedChunks = [...cleanChunks];
    poisonedChunks[2] = "POISONED_INJECTED_RECORD";
    const poisonedCheck = await safeJSON<{ verified: boolean; reason?: string }>(
      `${ATTESTATION_API}/verify`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_id: datasetId, chunks: poisonedChunks }),
      },
      { verified: true }
    );
    results.push({
      label: "Verify dataset with injected poisoned record",
      verified: poisonedCheck.verified,
      reason: poisonedCheck.reason,
    });

    setSimResults(results);
    setSimRunning(false);
  }

  return (
    <div className="app">
      <header>
        <h1>AICG</h1>
        <span className="subtitle">AI Compliance &amp; Poisoning Guardrail</span>
      </header>

      <main>
        <section className="service-status">
          <h2>Service health</h2>
          <div className="status-row">
            <StatusPill label="Attestation Gateway" up={servicesUp.attestation} />
            <StatusPill label="Poisoning Detector" up={servicesUp.detector} />
            <StatusPill label="Unlearning Controller" up={servicesUp.unlearning} />
          </div>
        </section>

        <section>
          <h2>Live poisoning attack simulation</h2>
          <p className="hint">
            Attests a clean dataset, then attempts to verify a tampered version with a
            poisoned record swapped in — the way a real ingestion pipeline would catch it
            before training.
          </p>
          <button className="run-btn" onClick={runPoisoningSimulation} disabled={simRunning}>
            {simRunning ? "Running…" : "Run simulation"}
          </button>
          {simResults.length > 0 && (
            <ul className="sim-results">
              {simResults.map((r, i) => (
                <li key={i} className={r.verified ? "sim-pass" : "sim-block"}>
                  <span className="sim-icon">{r.verified ? "✓" : "✕"}</span>
                  <span>{r.label}</span>
                  {r.reason && <span className="sim-reason">— {r.reason}</span>}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h2>Data lineage — attested datasets</h2>
          <table>
            <thead>
              <tr>
                <th>Dataset ID</th>
                <th>Root hash</th>
                <th>Chunks</th>
                <th>Attested at</th>
              </tr>
            </thead>
            <tbody>
              {attestations.map((a) => (
                <tr key={a.dataset_id}>
                  <td>{a.dataset_id}</td>
                  <td className="mono">{a.root_hash.slice(0, 16)}…</td>
                  <td>{a.chunk_count}</td>
                  <td>{new Date(a.attested_at * 1000).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {attestations.length === 0 && <p className="empty">No datasets attested yet.</p>}
        </section>
      </main>
    </div>
  );
}

function StatusPill({ label, up }: { label: string; up: boolean }) {
  return (
    <div className={`pill ${up ? "pill-up" : "pill-down"}`}>
      <span className="dot" />
      {label}
    </div>
  );
}
