import { useEffect, useState } from "react";
import "./App.css";

const API = "http://localhost:8787/api";

const DEFAULT_REQUEST =
  "Alexa, get my AC serviced this week under ₹2,000, but not Thursday.";

function App() {
  const [connected, setConnected] = useState(false);
  const [request, setRequest] = useState(DEFAULT_REQUEST);

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text:
        "Hi, I’m Relay. Delegate a real-world task and I’ll carry it across services and decisions while keeping important commitments under your control.",
    },
  ]);

  const [task, setTask] = useState(null);
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [audit, setAudit] = useState([]);

  const [status, setStatus] = useState("READY");
  const [busy, setBusy] = useState(false);
  const [approvalPending, setApprovalPending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    checkConnection();
  }, []);

  async function checkConnection() {
    try {
      const response = await fetch(`${API}/health`);

      if (!response.ok) {
        throw new Error("Bridge unavailable");
      }

      await response.json();

      setConnected(true);
    } catch {
      setConnected(false);
    }
  }

  async function callTool(name, args) {
    const response = await fetch(`${API}/tool`, {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        name,
        arguments: args,
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(
        data.error || `${name} failed`,
      );
    }

    return data.result;
  }

  function addMessage(role, text) {
    setMessages((current) => [
      ...current,
      {
        role,
        text,
      },
    ]);
  }

  async function startTask() {
    if (busy) {
      return;
    }

    setBusy(true);
    setError("");
    setProviders([]);
    setSelectedProvider(null);
    setApprovalPending(false);
    setAudit([]);

    addMessage("user", request);

    try {
      setStatus("DELEGATED");

      const created = await callTool(
        "create_errand",
        {
          goal: "Get my AC serviced",
          budget: 2000,
          deadline: "2026-10-10",
          excluded_days: ["Thursday"],
        },
      );

      setTask(created);

      addMessage(
        "assistant",
        "Got it. I’ll search for AC servicing under ₹2,000 before October 10 and exclude Thursday.",
      );

      setStatus("SEARCHING");

      const found = await callTool(
        "find_providers",
        {
          task_id: created.task_id,
        },
      );

      const foundProviders =
        found.providers || [];

      setProviders(foundProviders);

      setStatus("OPTIONS_READY");

      if (foundProviders.length === 0) {
        addMessage(
          "assistant",
          "I couldn't find any providers that satisfy all of your constraints.",
        );

        return;
      }

      await callTool(
        "propose_options",
        {
          task_id: created.task_id,
        },
      );

      const cheapest = [...foundProviders].sort(
        (a, b) => a.price - b.price,
      )[0];

      const earliest = [...foundProviders].sort(
        (a, b) =>
          new Date(a.available_date) -
          new Date(b.available_date),
      )[0];

      addMessage(
        "assistant",
        `${cheapest.name} is cheapest at ₹${cheapest.price}. ${earliest.name} is earliest on ${formatDate(
          earliest.available_date,
        )}. Which would you prefer?`,
      );
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Something went wrong.";

      setError(message);
      setStatus("ERROR");

      addMessage(
        "assistant",
        `I couldn't continue: ${message}`,
      );
    } finally {
      setBusy(false);
    }
  }

  async function chooseProvider(provider) {
    if (!task || busy) {
      return;
    }

    setBusy(true);
    setError("");

    try {
      setStatus("SELECTING");

      await callTool(
        "select_provider",
        {
          task_id: task.task_id,
          provider_id: provider.provider_id,
        },
      );

      setSelectedProvider(provider);
      setApprovalPending(true);

      setStatus("NEEDS_APPROVAL");

      addMessage(
        "user",
        `Choose ${provider.name}.`,
      );

      addMessage(
        "assistant",
        `${provider.name} costs ₹${provider.price} and is available ${formatDate(
          provider.available_date,
        )}. Booking involves spending money, so I need your approval before continuing.`,
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Provider selection failed.",
      );

      setStatus("ERROR");
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!task || !selectedProvider || busy) {
      return;
    }

    setBusy(true);
    setError("");

    try {
      setStatus("APPROVING");

      await callTool(
        "approve_booking",
        {
          task_id: task.task_id,
          approve: true,
        },
      );

      setApprovalPending(false);
      setStatus("COMPLETED");

      addMessage(
        "user",
        `Approve ₹${selectedProvider.price}.`,
      );

      addMessage(
        "assistant",
        `${selectedProvider.name} has been approved for ${formatDate(
          selectedProvider.available_date,
        )}. The complete decision trail has been preserved.`,
      );

      await loadAudit(task.task_id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Approval failed.",
      );

      setStatus("ERROR");
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    if (!task || busy) {
      return;
    }

    setBusy(true);

    try {
      await callTool(
        "approve_booking",
        {
          task_id: task.task_id,
          approve: false,
        },
      );

      setApprovalPending(false);
      setStatus("REJECTED");

      addMessage(
        "user",
        "Don't approve it.",
      );

      addMessage(
        "assistant",
        "Understood. I stopped before making the commitment.",
      );

      await loadAudit(task.task_id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to reject booking.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function loadAudit(taskId = task?.task_id) {
    if (!taskId) {
      return;
    }

    try {
      const result = await callTool(
        "get_audit_log",
        {
          task_id: taskId,
        },
      );

      if (Array.isArray(result)) {
        setAudit(result);
      } else if (Array.isArray(result?.events)) {
        setAudit(result.events);
      }
    } catch (err) {
      console.error(err);
    }
  }

  function resetDemo() {
    setMessages([
      {
        role: "assistant",
        text:
          "Hi, I’m Relay. Delegate a real-world task and I’ll carry it across services and decisions while keeping important commitments under your control.",
      },
    ]);

    setTask(null);
    setProviders([]);
    setSelectedProvider(null);
    setApprovalPending(false);
    setAudit([]);
    setError("");
    setStatus("READY");
    setRequest(DEFAULT_REQUEST);
  }

  const cheapestId =
    providers.length > 0
      ? [...providers].sort(
          (a, b) => a.price - b.price,
        )[0].provider_id
      : null;

  const earliestId =
    providers.length > 0
      ? [...providers].sort(
          (a, b) =>
            new Date(a.available_date) -
            new Date(b.available_date),
        )[0].provider_id
      : null;

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <div className="logo">R</div>

          <div>
            <h2>Relay</h2>
            <span>
              Alexa+ Task Delegation
            </span>
          </div>
        </div>

        <div className="header-actions">
          <div
            className={`connection ${
              connected ? "online" : "offline"
            }`}
          >
            <span />
            {connected
              ? "AWS MCP Connected"
              : "MCP Offline"}
          </div>

          <button
            className="secondary-button"
            onClick={resetDemo}
          >
            Reset
          </button>
        </div>
      </header>

      <main className="layout">
        <section className="main-panel">
          <div className="hero">
            <div>
              <p className="label">
                SIMULATED ALEXA+ EXPERIENCE
              </p>

              <h1>
                Delegate the outcome.
                <br />
                Relay handles the work.
              </h1>

              <p className="description">
                A durable agent that works across time,
                services and decisions while keeping humans
                in control of meaningful commitments.
              </p>
            </div>

            <div className="protocol">
              MCP
              <strong>2025-11-25</strong>
            </div>
          </div>

          <div className="chat">
            {messages.map((message, index) => (
              <div
                className={`message ${message.role}`}
                key={index}
              >
                <div className="avatar">
                  {message.role === "assistant"
                    ? "R"
                    : "You"}
                </div>

                <div className="bubble">
                  {message.text}
                </div>
              </div>
            ))}

            {busy && (
              <div className="message assistant">
                <div className="avatar">R</div>

                <div className="bubble working">
                  <span />
                  <span />
                  <span />

                  Relay is working
                </div>
              </div>
            )}
          </div>

          {providers.length > 0 && (
            <div className="providers">
              <p className="section-title">
                VALID PROVIDERS
              </p>

              <div className="provider-grid">
                {providers.map((provider) => (
                  <article
                    className="provider-card"
                    key={provider.provider_id}
                  >
                    <div className="provider-header">
                      <div>
                        <h3>{provider.name}</h3>
                        <span>
                          AC service provider
                        </span>
                      </div>

                      <strong>
                        ₹{provider.price}
                      </strong>
                    </div>

                    <div className="badges">
                      {provider.provider_id ===
                        cheapestId && (
                        <span>Cheapest</span>
                      )}

                      {provider.provider_id ===
                        earliestId && (
                        <span>Earliest</span>
                      )}
                    </div>

                    <p>
                      Available{" "}
                      <strong>
                        {formatDate(
                          provider.available_date,
                        )}
                      </strong>
                    </p>

                    <button
                      disabled={
                        busy ||
                        approvalPending ||
                        status === "COMPLETED"
                      }
                      onClick={() =>
                        chooseProvider(provider)
                      }
                    >
                      Choose {provider.name}
                    </button>
                  </article>
                ))}
              </div>
            </div>
          )}

          {approvalPending &&
            selectedProvider && (
              <div className="approval">
                <div className="warning">
                  !
                </div>

                <div className="approval-content">
                  <p className="label orange">
                    HUMAN APPROVAL REQUIRED
                  </p>

                  <h3>
                    Approve ₹
                    {selectedProvider.price} commitment?
                  </h3>

                  <p>
                    Relay will not cross this financial
                    boundary without explicit permission.
                  </p>

                  <div className="approval-details">
                    <div>
                      <span>Provider</span>
                      <strong>
                        {selectedProvider.name}
                      </strong>
                    </div>

                    <div>
                      <span>Date</span>
                      <strong>
                        {formatDate(
                          selectedProvider.available_date,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>Amount</span>
                      <strong>
                        ₹{selectedProvider.price}
                      </strong>
                    </div>
                  </div>

                  <div className="approval-buttons">
                    <button
                      className="approve"
                      onClick={approve}
                    >
                      Approve ₹
                      {selectedProvider.price}
                    </button>

                    <button
                      className="reject"
                      onClick={reject}
                    >
                      Don't approve
                    </button>
                  </div>
                </div>
              </div>
            )}

          {!task && (
            <div className="composer">
              <textarea
                rows="3"
                value={request}
                onChange={(event) =>
                  setRequest(
                    event.target.value,
                  )
                }
              />

              <div className="composer-bottom">
                <span>
                  ◉ Voice-style Alexa+ simulation
                </span>

                <button
                  disabled={
                    busy || !connected
                  }
                  onClick={startTask}
                >
                  Delegate to Relay
                </button>
              </div>
            </div>
          )}

          {error && (
            <div className="error">
              {error}
            </div>
          )}
        </section>

        <aside className="sidebar">
          <div className="card">
            <div className="card-heading">
              <p className="label">
                DELEGATION CONTRACT
              </p>

              <span className="state">
                {status}
              </span>
            </div>

            <div className="rows">
              <Row
                label="Goal"
                value="AC servicing"
              />

              <Row
                label="Budget"
                value="≤ ₹2,000"
              />

              <Row
                label="Deadline"
                value="10 Oct 2026"
              />

              <Row
                label="Excluded"
                value="Thursday"
              />

              <Row
                label="Spend authority"
                value="Human only"
                highlight
              />
            </div>
          </div>

          <div className="card">
            <p className="label">
              TASK LIFECYCLE
            </p>

            <Timeline status={status} />
          </div>

          <div className="card">
            <p className="label">
              REAL AWS BACKEND
            </p>

            <div className="rows">
              <Row
                label="Protocol"
                value="MCP Streamable HTTP"
              />

              <Row
                label="Runtime"
                value="ECS Express"
              />

              <Row
                label="State"
                value="DynamoDB"
              />

              <Row
                label="Reasoning"
                value="Amazon Bedrock"
              />

              <Row
                label="Resume"
                value="EventBridge + Lambda"
              />
            </div>
          </div>

          {task && (
            <div className="card">
              <div className="card-heading">
                <p className="label">
                  DECISION RECEIPT
                </p>

                <button
                  className="refresh"
                  onClick={() =>
                    loadAudit()
                  }
                >
                  Refresh
                </button>
              </div>

              <div className="task-id">
                <span>Task ID</span>

                <code>
                  {task.task_id}
                </code>
              </div>

              {audit.length === 0 ? (
                <p className="empty">
                  Complete the workflow or press Refresh
                  to load the audit trail.
                </p>
              ) : (
                <div className="audit">
                  {audit.map((event, index) => (
                    <div
                      className="audit-event"
                      key={
                        event.event_id ||
                        index
                      }
                    >
                      <span className="dot" />

                      <div>
                        <strong>
                          {event.event_type}
                        </strong>

                        <small>
                          {formatTime(
                            event.timestamp,
                          )}
                        </small>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}

function Row({
  label,
  value,
  highlight = false,
}) {
  return (
    <div className="row">
      <span>{label}</span>

      <strong
        className={
          highlight ? "highlight" : ""
        }
      >
        {value}
      </strong>
    </div>
  );
}

function Timeline({ status }) {
  const stages = [
    "Delegated",
    "Working",
    "Options",
    "Approval",
    "Completed",
  ];

  const map = {
    READY: -1,
    DELEGATED: 0,
    SEARCHING: 1,
    OPTIONS_READY: 2,
    SELECTING: 2,
    NEEDS_APPROVAL: 3,
    APPROVING: 3,
    REJECTED: 3,
    COMPLETED: 4,
    ERROR: 1,
  };

  const active = map[status] ?? -1;

  return (
    <div className="timeline">
      {stages.map((stage, index) => (
        <div
          className={`timeline-row ${
            index < active
              ? "done"
              : index === active
                ? "active"
                : ""
          }`}
          key={stage}
        >
          <div className="timeline-icon">
            {index < active
              ? "✓"
              : index === active
                ? "●"
                : ""}
          </div>

          <span>{stage}</span>
        </div>
      ))}
    </div>
  );
}

function formatDate(value) {
  if (!value) {
    return "Unknown";
  }

  return new Intl.DateTimeFormat(
    "en-IN",
    {
      weekday: "long",
      day: "numeric",
      month: "short",
    },
  ).format(
    new Date(
      `${value}T12:00:00`,
    ),
  );
}

function formatTime(value) {
  if (!value) {
    return "";
  }

  return new Intl.DateTimeFormat(
    "en-IN",
    {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    },
  ).format(
    new Date(value),
  );
}

export default App;