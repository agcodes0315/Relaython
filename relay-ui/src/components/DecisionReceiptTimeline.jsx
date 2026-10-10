import React from "react";
import "../styles/relay-improvements.css";

const labels = {
  TASK_CREATED: "Task contract stored",
  POLICY_EVALUATED: "Safety policy evaluated",
  PROVIDERS_FILTERED: "Providers filtered against constraints",
  OPTIONS_PROPOSED: "Compliant options proposed",
  PROVIDER_SELECTED: "Provider selected",
  USER_APPROVED: "Human approval recorded",
  PROVIDER_FAILED: "Provider became unavailable",
  APPROVAL_INVALIDATED: "Previous approval invalidated",
  RECOVERY_STARTED: "Recovery started",
  WAIT_SCHEDULED: "Future resume scheduled",
  RESUME_TRIGGERED: "AWS resume trigger fired",
  STATE_RESTORED: "Persisted state restored",
  TASK_RESUMED: "Task resumed",
};

export default function DecisionReceiptTimeline({ events = [] }) {
  const items = [...events].sort((a, b) =>
    String(a.timestamp ?? "").localeCompare(String(b.timestamp ?? ""))
  );

  return (
    <section className="relay-panel">
      <div className="relay-panel__heading">
        <div>
          <p className="relay-eyebrow">Decision Receipt</p>
          <h2>What Relay decided, preserved and changed</h2>
        </div>
        <span className="relay-badge relay-badge--real">AUDITABLE</span>
      </div>

      {items.length === 0 ? (
        <p className="relay-placeholder">No decision events yet.</p>
      ) : (
        <ol className="relay-timeline">
          {items.map((event, index) => {
            const type = event.event_type ?? event.type ?? "EVENT";
            const details = event.details ?? event.message ?? event.summary ?? "";
            return (
              <li key={`${type}-${event.timestamp ?? index}`}>
                <span className="relay-timeline__dot" />
                <div>
                  <strong>{labels[type] ?? type.replaceAll("_", " ")}</strong>
                  {details && (
                    <p>
                      {typeof details === "string"
                        ? details
                        : JSON.stringify(details)}
                    </p>
                  )}
                  {event.timestamp && (
                    <time>{new Date(event.timestamp).toLocaleString()}</time>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
