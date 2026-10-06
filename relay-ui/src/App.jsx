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
  const [selectedProvider, setSelectedProvider] =
    useState(null);

  const [audit, setAudit] = useState([]);

  const [status, setStatus] = useState("READY");
  const [busy, setBusy] = useState(false);

  const [approvalPending, setApprovalPending] =
    useState(false);

  const [error, setError] = useState("");

  const [failedProvider, setFailedProvider] =
    useState(null);

  const [recoveryOccurred, setRecoveryOccurred] =
    useState(false);

  useEffect(() => {
    checkConnection();
  }, []);

  async function checkConnection() {
    try {
      const response = await fetch(
        `${API}/health`,
      );

      if (!response.ok) {
        throw new Error(
          "Bridge unavailable",
        );
      }

      await response.json();

      setConnected(true);
    } catch {
      setConnected(false);
    }
  }

  async function callTool(
    name,
    args,
  ) {
    const response = await fetch(
      `${API}/tool`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        body: JSON.stringify({
          name,
          arguments: args,
        }),
      },
    );

    const data =
      await response.json();

    if (
      !response.ok ||
      !data.success
    ) {
      throw new Error(
        data.error ||
          `${name} failed`,
      );
    }

    if (
      data.result &&
      typeof data.result === "object" &&
      !Array.isArray(data.result) &&
      data.result.error
    ) {
      throw new Error(
        data.result.error,
      );
    }

    return data.result;
  }

  function addMessage(
    role,
    text,
  ) {
    setMessages(
      (current) => [
        ...current,
        {
          role,
          text,
        },
      ],
    );
  }

  async function restoreDemoProviders() {
    const ids = [
      "provider_1",
      "provider_2",
      "provider_3",
    ];

    for (const providerId of ids) {
      try {
        await callTool(
          "restore_provider",
          {
            provider_id:
              providerId,
          },
        );
      } catch {
        // Demo reset should continue even
        // if one provider is already available.
      }
    }
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
    setFailedProvider(null);
    setRecoveryOccurred(false);

    addMessage(
      "user",
      request,
    );

    try {
      await restoreDemoProviders();

      setStatus("DELEGATED");

      const created =
        await callTool(
          "create_errand",
          {
            goal:
              "Get my AC serviced",
            budget: 2000,
            deadline:
              "2026-10-10",
            excluded_days: [
              "Thursday",
            ],
          },
        );

      setTask(created);

      addMessage(
        "assistant",
        "Got it. I’ll search for AC servicing under ₹2,000 before October 10 and exclude Thursday.",
      );

      setStatus("SEARCHING");

      const found =
        await callTool(
          "find_providers",
          {
            task_id:
              created.task_id,
          },
        );

      const foundProviders =
        found.providers || [];

      setProviders(
        foundProviders,
      );

      if (
        foundProviders.length ===
        0
      ) {
        setStatus(
          "NO_PROVIDERS",
        );

        addMessage(
          "assistant",
          "I couldn't find any providers that satisfy all of your constraints.",
        );

        return;
      }

      await callTool(
        "propose_options",
        {
          task_id:
            created.task_id,
        },
      );

      setStatus(
        "OPTIONS_READY",
      );

      const cheapest = [
        ...foundProviders,
      ].sort(
        (a, b) =>
          a.price - b.price,
      )[0];

      const earliest = [
        ...foundProviders,
      ].sort(
        (a, b) =>
          new Date(
            a.available_date,
          ) -
          new Date(
            b.available_date,
          ),
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

  async function chooseProvider(
    provider,
  ) {
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
          task_id:
            task.task_id,

          provider_id:
            provider.provider_id,
        },
      );

      setSelectedProvider(
        provider,
      );

      setApprovalPending(true);

      setStatus(
        "NEEDS_APPROVAL",
      );

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

      await loadAudit(
        task.task_id,
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
    if (
      !task ||
      !selectedProvider ||
      busy
    ) {
      return;
    }

    setBusy(true);
    setError("");

    try {
      setStatus("APPROVING");

      await callTool(
        "approve_booking",
        {
          task_id:
            task.task_id,

          approve: true,
        },
      );

      setApprovalPending(
        false,
      );

      setStatus("COMPLETED");

      addMessage(
        "user",
        `Approve ₹${selectedProvider.price}.`,
      );

      if (recoveryOccurred) {
        addMessage(
          "assistant",
          `${selectedProvider.name} has been approved as the replacement provider for ${formatDate(
            selectedProvider.available_date,
          )}. Relay recovered the task without silently changing your financial commitment.`,
        );
      } else {
        addMessage(
          "assistant",
          `${selectedProvider.name} has been approved for ${formatDate(
            selectedProvider.available_date,
          )}. The complete decision trail has been preserved.`,
        );
      }

      await loadAudit(
        task.task_id,
      );
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
    setError("");

    try {
      await callTool(
        "approve_booking",
        {
          task_id:
            task.task_id,

          approve: false,
        },
      );

      setApprovalPending(
        false,
      );

      setStatus("REJECTED");

      addMessage(
        "user",
        "Don't approve it.",
      );

      addMessage(
        "assistant",
        "Understood. I stopped before making the commitment.",
      );

      await loadAudit(
        task.task_id,
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to reject booking.",
      );

      setStatus("ERROR");
    } finally {
      setBusy(false);
    }
  }

  async function simulateFailure() {
    if (
      !task ||
      !selectedProvider ||
      busy ||
      recoveryOccurred
    ) {
      return;
    }

    const cancelled =
      selectedProvider;

    setBusy(true);
    setError("");
    setStatus("RECOVERING");

    addMessage(
      "assistant",
      `Update: ${cancelled.name} has reported that it can no longer fulfil the booking. I’m reopening the task and reapplying your original constraints.`,
    );

    try {
      const recovery =
        await callTool(
          "simulate_provider_failure_tool",
          {
            task_id:
              task.task_id,
          },
        );

      setFailedProvider(
        recovery.failed_provider ||
          cancelled,
      );

      setRecoveryOccurred(
        true,
      );

      setSelectedProvider(
        null,
      );

      setApprovalPending(
        false,
      );

      const remaining =
        recovery.remaining_providers ||
        [];

      setProviders(remaining);

      if (
        remaining.length === 0
      ) {
        setStatus(
          "NO_PROVIDERS",
        );

        addMessage(
          "assistant",
          "The previous provider failed and no remaining provider satisfies your original constraints. I stopped rather than weakening them.",
        );

        await loadAudit(
          task.task_id,
        );

        return;
      }

      await callTool(
        "propose_options",
        {
          task_id:
            task.task_id,
        },
      );

      setStatus(
        "OPTIONS_READY",
      );

      const cheapest = [
        ...remaining,
      ].sort(
        (a, b) =>
          a.price - b.price,
      )[0];

      addMessage(
        "assistant",
        `${cancelled.name} has been removed. ${cheapest.name} still satisfies your budget, deadline and excluded-day constraint at ₹${cheapest.price}. I will not switch providers without a new decision from you.`,
      );

      await loadAudit(
        task.task_id,
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Recovery failed.",
      );

      setStatus("ERROR");

      addMessage(
        "assistant",
        "I couldn't safely recover the task, so I stopped instead of making an uncontrolled commitment.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function loadAudit(
    taskId = task?.task_id,
  ) {
    if (!taskId) {
      return;
    }

    try {
      const result =
        await callTool(
          "get_audit_log",
          {
            task_id: taskId,
          },
        );

      if (
        Array.isArray(result)
      ) {
        setAudit(result);
      } else if (
        Array.isArray(
          result?.events,
        )
      ) {
        setAudit(
          result.events,
        );
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function resetDemo() {
    if (busy) {
      return;
    }

    setBusy(true);

    try {
      await restoreDemoProviders();
    } catch {
      // UI reset should still proceed.
    }

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
    setFailedProvider(null);
    setRecoveryOccurred(false);

    setBusy(false);
  }

  const cheapestId =
    providers.length > 0
      ? [...providers].sort(
          (a, b) =>
            a.price - b.price,
        )[0].provider_id
      : null;

  const earliestId =
    providers.length > 0
      ? [...providers].sort(
          (a, b) =>
            new Date(
              a.available_date,
            ) -
            new Date(
              b.available_date,
            ),
        )[0].provider_id
      : null;

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <div className="logo">
            R
          </div>

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
              connected
                ? "online"
                : "offline"
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
            disabled={busy}
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
                SIMULATED ALEXA+
                EXPERIENCE
              </p>

              <h1>
                Delegate the outcome.
                <br />
                Relay handles the work.
              </h1>

              <p className="description">
                A durable agent that works
                across time, services and
                decisions while keeping
                humans in control of
                meaningful commitments.
              </p>
            </div>

            <div className="protocol">
              MCP
              <strong>
                2025-11-25
              </strong>
            </div>
          </div>

          <div className="chat">
            {messages.map(
              (
                message,
                index,
              ) => (
                <div
                  className={`message ${message.role}`}
                  key={index}
                >
                  <div className="avatar">
                    {message.role ===
                    "assistant"
                      ? "R"
                      : "You"}
                  </div>

                  <div className="bubble">
                    {message.text}
                  </div>
                </div>
              ),
            )}

            {busy && (
              <div className="message assistant">
                <div className="avatar">
                  R
                </div>

                <div className="bubble working">
                  <span />
                  <span />
                  <span />

                  Relay is working
                </div>
              </div>
            )}
          </div>

          {failedProvider && (
            <div className="approval">
              <div className="warning">
                !
              </div>

              <div className="approval-content">
                <p className="label orange">
                  DURABLE RECOVERY
                </p>

                <h3>
                  {
                    failedProvider.name
                  }{" "}
                  became unavailable
                </h3>

                <p>
                  Relay preserved the
                  original task, removed
                  the failed provider,
                  reapplied your
                  constraints and returned
                  control to you before
                  making another
                  commitment.
                </p>

                <div className="approval-details">
                  <div>
                    <span>
                      Failed provider
                    </span>

                    <strong>
                      {
                        failedProvider.name
                      }
                    </strong>
                  </div>

                  <div>
                    <span>
                      Old approval
                    </span>

                    <strong>
                      Invalidated
                    </strong>
                  </div>

                  <div>
                    <span>
                      Recovery
                    </span>

                    <strong>
                      Constraints
                      reapplied
                    </strong>
                  </div>
                </div>
              </div>
            </div>
          )}

          {providers.length > 0 &&
            status !== "COMPLETED" && (
              <div className="providers">
                <p className="section-title">
                  {recoveryOccurred
                    ? "RECOVERY OPTIONS"
                    : "VALID PROVIDERS"}
                </p>

                <div className="provider-grid">
                  {providers.map(
                    (provider) => (
                      <article
                        className="provider-card"
                        key={
                          provider.provider_id
                        }
                      >
                        <div className="provider-header">
                          <div>
                            <h3>
                              {
                                provider.name
                              }
                            </h3>

                            <span>
                              AC service
                              provider
                            </span>
                          </div>

                          <strong>
                            ₹
                            {
                              provider.price
                            }
                          </strong>
                        </div>

                        <div className="badges">
                          {provider.provider_id ===
                            cheapestId && (
                            <span>
                              Cheapest
                            </span>
                          )}

                          {provider.provider_id ===
                            earliestId && (
                            <span>
                              Earliest
                            </span>
                          )}

                          {recoveryOccurred && (
                            <span>
                              Revalidated
                            </span>
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
                            approvalPending
                          }
                          onClick={() =>
                            chooseProvider(
                              provider,
                            )
                          }
                        >
                          Choose{" "}
                          {
                            provider.name
                          }
                        </button>
                      </article>
                    ),
                  )}
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
                    HUMAN APPROVAL
                    REQUIRED
                  </p>

                  <h3>
                    Approve ₹
                    {
                      selectedProvider.price
                    }{" "}
                    commitment?
                  </h3>

                  <p>
                    Relay will not cross
                    this financial boundary
                    without explicit
                    permission.
                  </p>

                  <div className="approval-details">
                    <div>
                      <span>
                        Provider
                      </span>

                      <strong>
                        {
                          selectedProvider.name
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Date
                      </span>

                      <strong>
                        {formatDate(
                          selectedProvider.available_date,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Amount
                      </span>

                      <strong>
                        ₹
                        {
                          selectedProvider.price
                        }
                      </strong>
                    </div>
                  </div>

                  <div className="approval-buttons">
                    <button
                      className="approve"
                      onClick={approve}
                      disabled={busy}
                    >
                      Approve ₹
                      {
                        selectedProvider.price
                      }
                    </button>

                    <button
                      className="reject"
                      onClick={reject}
                      disabled={busy}
                    >
                      Don't approve
                    </button>
                  </div>
                </div>
              </div>
            )}

          {status === "COMPLETED" &&
            selectedProvider &&
            !recoveryOccurred && (
              <div className="approval">
                <div className="warning">
                  ↻
                </div>

                <div className="approval-content">
                  <p className="label orange">
                    DURABILITY DEMO
                  </p>

                  <h3>
                    What if the provider
                    cancels later?
                  </h3>

                  <p>
                    Simulate an external
                    provider failure after
                    approval to show how
                    Relay resumes the same
                    durable task instead of
                    losing context or
                    silently switching
                    providers.
                  </p>

                  <div className="approval-buttons">
                    <button
                      className="reject"
                      disabled={busy}
                      onClick={
                        simulateFailure
                      }
                    >
                      Demo: Simulate{" "}
                      {
                        selectedProvider.name
                      }{" "}
                      cancellation
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
                  ◉ Voice-style Alexa+
                  simulation
                </span>

                <button
                  disabled={
                    busy ||
                    !connected
                  }
                  onClick={
                    startTask
                  }
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

            <Timeline
              status={status}
              recovered={
                recoveryOccurred
              }
            />
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
                label="AI layer"
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
                <span>
                  Task ID
                </span>

                <code>
                  {task.task_id}
                </code>
              </div>

              {audit.length === 0 ? (
                <p className="empty">
                  Complete an action or
                  press Refresh to load
                  the audit trail.
                </p>
              ) : (
                <div className="audit">
                  {audit.map(
                    (
                      event,
                      index,
                    ) => (
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
                            {
                              event.event_type
                            }
                          </strong>

                          <small>
                            {formatTime(
                              event.timestamp,
                            )}
                          </small>
                        </div>
                      </div>
                    ),
                  )}
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
          highlight
            ? "highlight"
            : ""
        }
      >
        {value}
      </strong>
    </div>
  );
}

function Timeline({
  status,
  recovered,
}) {
  const stages = recovered
    ? [
        "Delegated",
        "Working",
        "Approved",
        "Provider failed",
        "Recovered",
        "New approval",
      ]
    : [
        "Delegated",
        "Working",
        "Options",
        "Approval",
        "Completed",
      ];

  let active = -1;

  if (!recovered) {
    const normalMap = {
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
      NO_PROVIDERS: 2,
    };

    active =
      normalMap[status] ?? -1;
  } else {
    const recoveryMap = {
      RECOVERING: 3,
      OPTIONS_READY: 4,
      SELECTING: 4,
      NEEDS_APPROVAL: 5,
      APPROVING: 5,
      COMPLETED: 5,
      ERROR: 3,
      NO_PROVIDERS: 4,
    };

    active =
      recoveryMap[status] ?? 4;
  }

  return (
    <div className="timeline">
      {stages.map(
        (stage, index) => (
          <div
            className={`timeline-row ${
              index < active
                ? "done"
                : index ===
                    active
                  ? "active"
                  : ""
            }`}
            key={stage}
          >
            <div className="timeline-icon">
              {index < active
                ? "✓"
                : index ===
                    active
                  ? "●"
                  : ""}
            </div>

            <span>
              {stage}
            </span>
          </div>
        ),
      )}
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