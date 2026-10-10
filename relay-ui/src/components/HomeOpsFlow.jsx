import React, { useEffect, useMemo, useState } from "react";
import { createHomeOpsApi } from "../lib/homeopsApi";
import "../styles/relay-improvements.css";

const unwrap = (v) => v?.result ?? v?.data ?? v?.content ?? v ?? {};

const asItems = (v) => {
  const x = unwrap(v);
  if (Array.isArray(x)) return x;
  return x.assets ?? x.items ?? x.result ?? [];
};

export default function HomeOpsFlow({
  callTool,
  onContractPrepared,
  defaultSymptom = "The AC is not cooling properly",
}) {
  const api = useMemo(() => createHomeOpsApi(callTool), [callTool]);

  const [assets, setAssets] = useState([]);
  const [assetId, setAssetId] = useState("");
  const [asset, setAsset] = useState(null);
  const [warranty, setWarranty] = useState(null);
  const [symptom, setSymptom] = useState(defaultSymptom);
  const [troubleshooting, setTroubleshooting] = useState(null);
  const [contract, setContract] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    setBusy(true);

    api.listAssets()
      .then((r) => {
        if (!live) return;
        const next = asItems(r);
        setAssets(next);
        const first = next?.[0];
        const id = first?.asset_id ?? first?.id ?? first?.assetId ?? "";
        if (id) setAssetId(id);
      })
      .catch((e) => live && setError(e.message))
      .finally(() => live && setBusy(false));

    return () => {
      live = false;
    };
  }, [api]);

  async function loadContext() {
    if (!assetId) return;

    setError("");
    setBusy(true);

    try {
      const [a, w] = await Promise.all([
        api.getAsset(assetId),
        api.checkWarranty(assetId),
      ]);

      setAsset(unwrap(a));
      setWarranty(unwrap(w));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function runTroubleshooting() {
    if (!assetId || !symptom.trim()) return;

    setError("");
    setBusy(true);

    try {
      const result = unwrap(
        await api.troubleshoot(assetId, symptom.trim())
      );
      setTroubleshooting(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function prepareContract() {
    if (!assetId || !symptom.trim()) return;

    setError("");
    setBusy(true);

    try {
      const value = unwrap(
        await api.prepareService(
          assetId,
          symptom.trim(),
          {
            budget: 2000,
            deadline: "2026-10-10",
            excluded_days: ["Thursday"],
          }
        )
      );

      setContract(value);
      onContractPrepared?.(value);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const selected =
    asset ||
    assets.find(
      (x) => (x.asset_id ?? x.id ?? x.assetId) === assetId
    );

  const warrantyActive =
    warranty?.warranty_active ??
    warranty?.active ??
    warranty?.is_active;

  const warrantyRecommendation =
    warranty?.recommended_path ??
    warranty?.recommended ??
    warranty?.recommendation ??
    warranty?.recommended_action ??
    "Review warranty path before paid service";

  return (
    <section className="relay-panel">
      <div className="relay-panel__heading">
        <div>
          <p className="relay-eyebrow">HomeOps • Public MCP backend</p>
          <h2>From household context to durable service execution</h2>
          <p className="relay-muted">
            Household/provider data is simulated demo data. MCP execution,
            policy, persistence, recovery and AWS resume are real.
          </p>
        </div>

        <span className="relay-badge relay-badge--real">
          REAL MCP
        </span>
      </div>

      {error && <div className="relay-alert">{error}</div>}

      <div className="relay-grid">
        <article className="relay-card">
          <span className="relay-step">1</span>
          <h3>Known household asset</h3>

          <select
            value={assetId}
            onChange={(e) => {
              setAssetId(e.target.value);
              setAsset(null);
              setWarranty(null);
              setTroubleshooting(null);
              setContract(null);
              setError("");
            }}
          >
            <option value="">Choose asset</option>

            {assets.map((x) => {
              const id = x.asset_id ?? x.id ?? x.assetId;

              return (
                <option key={id} value={id}>
                  {x.name ??
                    x.product ??
                    x.product_name ??
                    "Household asset"}
                </option>
              );
            })}
          </select>

          <button
            disabled={!assetId || busy}
            onClick={loadContext}
          >
            Load asset + warranty
          </button>

          {selected && (
            <dl className="relay-kv">
              <div>
                <dt>Product</dt>
                <dd>
                  {selected.name ??
                    selected.product ??
                    selected.product_name ??
                    "CoolBreeze Split AC"}
                </dd>
              </div>

              <div>
                <dt>Model</dt>
                <dd>
                  {selected.model ??
                    selected.model_number ??
                    "CB-24X"}
                </dd>
              </div>

              <div>
                <dt>Location</dt>
                <dd>{selected.location ?? "Bedroom"}</dd>
              </div>
            </dl>
          )}
        </article>

        <article className="relay-card">
          <span className="relay-step">2</span>
          <h3>Warranty context</h3>

          {warranty ? (
            <div className="relay-success">
              <strong>
                {warrantyActive
                  ? "Warranty active"
                  : "Warranty status loaded"}
              </strong>

              <span>{warrantyRecommendation}</span>
            </div>
          ) : (
            <p className="relay-placeholder">
              Load the selected asset first.
            </p>
          )}
        </article>

        <article className="relay-card">
          <span className="relay-step">3</span>
          <h3>Conservative troubleshooting</h3>

          <textarea
            rows={3}
            value={symptom}
            onChange={(e) => setSymptom(e.target.value)}
          />

          <button
            disabled={!assetId || !symptom.trim() || busy}
            onClick={runTroubleshooting}
          >
            Run safe troubleshooting
          </button>

          {troubleshooting && (
            <div className="relay-success">
              <strong>
                {troubleshooting.high_risk
                  ? "Escalation required"
                  : "Safe troubleshooting available"}
              </strong>

              {Array.isArray(troubleshooting.steps) ? (
                <ul className="relay-list">
                  {troubleshooting.steps.map((step, index) => (
                    <li key={index}>{step}</li>
                  ))}
                </ul>
              ) : (
                <pre className="relay-json">
                  {JSON.stringify(troubleshooting, null, 2)}
                </pre>
              )}
            </div>
          )}
        </article>

        <article className="relay-card relay-card--accent">
          <span className="relay-step">4</span>
          <h3>Prepare durable service contract</h3>

          <ul className="relay-list">
            <li>Budget cap: ₹2,000</li>
            <li>Deadline: 10 Oct 2026</li>
            <li>Excluded day: Thursday</li>
            <li>Spend authority: human only</li>
          </ul>

          <button
            disabled={!assetId || !symptom.trim() || busy}
            onClick={prepareContract}
          >
            Prepare Relay contract
          </button>

          {contract && (
            <div className="relay-success">
              <strong>Contract prepared</strong>
              <span>
                Continuing into provider → approval → recovery → resume.
              </span>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
