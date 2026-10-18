import {
  useEffect,
  useRef,
  useState,
} from "react";

import "./App.css";
import HomeOpsFlow from "./components/HomeOpsFlow";
import ScamShieldFlow from "./components/ScamShieldFlow";
import DecisionReceiptTimeline from "./components/DecisionReceiptTimeline";

const API = "/api";

const DEFAULT_REQUEST =
  "Alexa, get my AC serviced this week under ₹2,000, but not Thursday.";


function App() {
  const [connected, setConnected] =
    useState(false);

  const [request, setRequest] =
    useState(DEFAULT_REQUEST);

  const [messages, setMessages] =
    useState([
      {
        role: "assistant",
        text:
          "Hi, I'm Relay. Delegate a real-world task and I'll carry it across services, failures and time while keeping meaningful commitments under your control.",
      },
    ]);

  const [task, setTask] =
    useState(null);

  const [providers, setProviders] =
    useState([]);

  const [
    selectedProvider,
    setSelectedProvider,
  ] = useState(null);

  const [audit, setAudit] =
    useState([]);

  const [homeOpsContract, setHomeOpsContract] =
    useState(null);

  const [
    showShield,
    setShowShield,
  ] = useState(false);

  const [status, setStatus] =
    useState("READY");

  const [busy, setBusy] =
    useState(false);

  const [
    approvalPending,
    setApprovalPending,
  ] = useState(false);

  const [error, setError] =
    useState("");

  const [
    failedProvider,
    setFailedProvider,
  ] = useState(null);

  const [
    recoveryOccurred,
    setRecoveryOccurred,
  ] = useState(false);

  const [waitState, setWaitState] =
    useState("IDLE");

  const [waitInfo, setWaitInfo] =
    useState(null);

  const [
    resumedTask,
    setResumedTask,
  ] = useState(null);

  const resumeAnnounced =
    useRef(false);


  useEffect(() => {
    checkConnection();
  }, []);


  useEffect(() => {
    if (
      waitState !== "SCHEDULED" ||
      !task?.task_id
    ) {
      return undefined;
    }

    const interval =
      window.setInterval(
        async () => {
          try {
            const current =
              await callTool(
                "get_errand",
                {
                  task_id:
                    task.task_id,
                },
              );

            if (
              current?.wait_status ===
              "RESUMED"
            ) {
              setTask(current);
              setResumedTask(current);

              setWaitState(
                "RESUMED",
              );

              await loadAudit(
                current.task_id,
              );

              if (
                !resumeAnnounced.current
              ) {
                resumeAnnounced.current =
                  true;

                addMessage(
                  "assistant",
                  "I'm back. EventBridge Scheduler woke the task, Lambda restored the persisted state from DynamoDB, and Relay resumed without losing the original goal, constraints or approval context.",
                );
              }
            }
          } catch (err) {
            console.error(
              "Resume polling failed:",
              err,
            );
          }
        },
        8000,
      );

    return () => {
      window.clearInterval(
        interval,
      );
    };
  }, [
    waitState,
    task?.task_id,
  ]);


  async function checkConnection() {
    try {
      const response =
        await fetch(
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
    const response =
      await fetch(
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
      typeof data.result ===
        "object" &&
      !Array.isArray(
        data.result,
      ) &&
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

    for (
      const providerId
      of ids
    ) {
      try {
        await callTool(
          "restore_provider",
          {
            provider_id:
              providerId,
          },
        );
      } catch {
        // continue
      }
    }
  }


  async function startTask(contractOverride = null) {
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
    setWaitState("IDLE");
    setWaitInfo(null);
    setResumedTask(null);

    resumeAnnounced.current =
      false;

    const preparedContract =
      contractOverride?.service_contract ??
      contractOverride ??
      null;

    const delegation =
      preparedContract
        ? {
            goal:
              preparedContract.goal ??
              "Get my AC serviced",
            budget:
              preparedContract.budget ??
              2000,
            deadline:
              preparedContract.deadline ??
              "2026-10-10",
            excluded_days:
              preparedContract.excluded_days ??
              ["Thursday"],
          }
        : {
            goal:
              "Get my AC serviced",
            budget: 2000,
            deadline:
              "2026-10-10",
            excluded_days: [
              "Thursday",
            ],
          };

    addMessage(
      "user",
      preparedContract
        ? `Continue with this prepared HomeOps service contract: ${delegation.goal}`
        : request,
    );

    try {
      await restoreDemoProviders();

      setStatus(
        "DELEGATED",
      );

      const created =
        await callTool(
          "create_errand",
          delegation,
        );

      setTask(created);

      addMessage(
        "assistant",
        preparedContract
          ? "HomeOps context is ready. I converted the asset and warranty context into a durable Relay contract. I'll now search only providers that satisfy the original budget, deadline and excluded-day constraints."
          : "Got it. I'll search for AC servicing under ₹2,000 before October 10 and exclude Thursday.",
      );

      setStatus(
        "SEARCHING",
      );

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
          a.price -
          b.price,
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

      await loadAudit(
        created.task_id,
      );
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Something went wrong.";

      setError(message);
      setStatus("ERROR");
    } finally {
      setBusy(false);
    }
  }


  async function chooseProvider(
    provider,
  ) {
    if (
      !task ||
      busy
    ) {
      return;
    }

    setBusy(true);
    setError("");

    try {
      setStatus(
        "SELECTING",
      );

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

      setApprovalPending(
        true,
      );

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
      setStatus(
        "APPROVING",
      );

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

      setStatus(
        "COMPLETED",
      );

      addMessage(
        "user",
        `Approve ₹${selectedProvider.price}.`,
      );

      if (
        recoveryOccurred
      ) {
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
    if (
      !task ||
      busy
    ) {
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
          approve:
            false,
        },
      );

      setApprovalPending(
        false,
      );

      setStatus(
        "REJECTED",
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

    setStatus(
      "RECOVERING",
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
        recovery
          .remaining_providers ||
        [];

      setProviders(
        remaining,
      );

      if (
        remaining.length ===
        0
      ) {
        setStatus(
          "NO_PROVIDERS",
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
          a.price -
          b.price,
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
    } finally {
      setBusy(false);
    }
  }


  async function scheduleDurableResume() {
    if (
      !task ||
      busy ||
      waitState ===
        "SCHEDULED"
    ) {
      return;
    }

    setBusy(true);
    setError("");

    resumeAnnounced.current =
      false;

    try {
      const result =
        await callTool(
          "schedule_task_resume",
          {
            task_id:
              task.task_id,
            minutes:
              2,
          },
        );

      setWaitInfo(
        result,
      );

      setWaitState(
        "SCHEDULED",
      );

      addMessage(
        "user",
        "Continue this task later.",
      );

      addMessage(
        "assistant",
        "Done. I persisted the task in DynamoDB and scheduled EventBridge to wake Relay in about two minutes.",
      );

      await loadAudit(
        task.task_id,
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to schedule resume.",
      );

      setWaitState(
        "ERROR",
      );
    } finally {
      setBusy(false);
    }
  }


  async function checkResumeNow() {
    if (!task?.task_id) {
      return;
    }

    setBusy(true);
    setError("");

    try {
      const current =
        await callTool(
          "get_errand",
          {
            task_id:
              task.task_id,
          },
        );

      setTask(current);
      setResumedTask(current);

      if (
        current?.wait_status ===
        "RESUMED"
      ) {
        setWaitState(
          "RESUMED",
        );

        await loadAudit(
          current.task_id,
        );

        if (
          !resumeAnnounced.current
        ) {
          resumeAnnounced.current =
            true;

          addMessage(
            "assistant",
            "The scheduled wake-up completed successfully. EventBridge triggered Lambda, Relay restored the persisted task from DynamoDB, and the original delegation context was preserved.",
          );
        }

        return;
      }

      await loadAudit(
        current.task_id,
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to check resume state.",
      );
    } finally {
      setBusy(false);
    }
  }


  async function loadAudit(
    taskId =
      task?.task_id,
  ) {
    if (!taskId) {
      return;
    }

    try {
      const result =
        await callTool(
          "get_audit_log",
          {
            task_id:
              taskId,
          },
        );

      if (
        Array.isArray(result)
      ) {
        setAudit(
          result,
        );
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
      // continue
    }

    setMessages([
      {
        role:
          "assistant",
        text:
          "Hi, I'm Relay. Delegate a real-world task and I'll carry it across services, failures and time while keeping meaningful commitments under your control.",
      },
    ]);

    setTask(null);
    setProviders([]);
    setSelectedProvider(null);
    setApprovalPending(false);
    setAudit([]);
    setHomeOpsContract(null);
    setShowShield(false);
    setError("");
    setStatus("READY");
    setRequest(
      DEFAULT_REQUEST,
    );
    setFailedProvider(
      null,
    );
    setRecoveryOccurred(
      false,
    );
    setWaitState("IDLE");
    setWaitInfo(null);
    setResumedTask(null);

    resumeAnnounced.current =
      false;

    setBusy(false);
  }


  const cheapestId =
    providers.length > 0
      ? [...providers].sort(
          (a, b) =>
            a.price -
            b.price,
        )[0]
          .provider_id
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
        )[0]
          .provider_id
      : null;


  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <div className="logo">
            R
          </div>

          <div>
            <h2>
              Relay
            </h2>

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
            onClick={
              resetDemo
            }
            disabled={
              busy
            }
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
                A durable agent that
                works across time,
                services and failures
                while keeping humans
                in control of meaningful
                commitments.
              </p>
            </div>

            <div className="protocol">
              MCP

              <strong>
                2025-11-25
              </strong>
            </div>
          </div>


          {!task && (
            <div style={{ marginBottom: "24px" }}>
              <div className="shield-mode-toggle">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() =>
                    setShowShield(false)
                  }
                  disabled={!showShield}
                >
                  HomeOps
                </button>

                <button
                  type="button"
                  className="secondary-button"
                  onClick={() =>
                    setShowShield(true)
                  }
                  disabled={showShield}
                >
                  Relay Shield
                </button>
              </div>

              {showShield ? (
                <ScamShieldFlow
                  callTool={callTool}
                />
              ) : (
                <HomeOpsFlow
                  callTool={callTool}
                  onContractPrepared={(prepared) => {
                    setHomeOpsContract(prepared);
                    addMessage(
                      "assistant",
                      "HomeOps found the household asset, checked warranty context, ran conservative troubleshooting, and prepared a durable service contract. I can now hand that contract into Relay's existing delegation lifecycle.",
                    );
                    startTask(prepared);
                  }}
                />
              )}
            </div>
          )}


          <div className="chat">
            {messages.map(
              (
                message,
                index,
              ) => (
                <div
                  className={`message ${message.role}`}
                  key={
                    index
                  }
                >
                  <div className="avatar">
                    {message.role ===
                    "assistant"
                      ? "R"
                      : "You"}
                  </div>

                  <div className="bubble">
                    {
                      message.text
                    }
                  </div>
                </div>
              ),
            )}
          </div>


          {providers.length >
            0 &&
            status !==
              "COMPLETED" && (
              <div className="providers">
                <p className="section-title">
                  {recoveryOccurred
                    ? "RECOVERY OPTIONS"
                    : "VALID PROVIDERS"}
                </p>

                <div className="provider-grid">
                  {providers.map(
                    (
                      provider,
                    ) => (
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
                              AC service provider
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
                    HUMAN APPROVAL REQUIRED
                  </p>

                  <h3>
                    Approve ₹
                    {
                      selectedProvider.price
                    }{" "}
                    commitment?
                  </h3>

                  <div className="approval-buttons">
                    <button
                      className="approve"
                      onClick={
                        approve
                      }
                      disabled={
                        busy
                      }
                    >
                      Approve ₹
                      {
                        selectedProvider.price
                      }
                    </button>

                    <button
                      className="reject"
                      onClick={
                        reject
                      }
                      disabled={
                        busy
                      }
                    >
                      Don't approve
                    </button>
                  </div>
                </div>
              </div>
            )}


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
                  control to you.
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
                      Constraints reapplied
                    </strong>
                  </div>
                </div>
              </div>
            </div>
          )}


          {status ===
            "COMPLETED" &&
            selectedProvider &&
            !recoveryOccurred && (
              <div className="approval">
                <div className="warning">
                  ↻
                </div>

                <div className="approval-content">
                  <p className="label orange">
                    FAILURE RECOVERY DEMO
                  </p>

                  <h3>
                    What if the provider cancels later?
                  </h3>

                  <button
                    className="reject"
                    disabled={
                      busy
                    }
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
            )}


          {status ===
            "COMPLETED" &&
            waitState ===
              "IDLE" && (
              <div className="durable-card">
                <div className="durable-heading">
                  <div className="durable-icon">
                    â—·
                  </div>

                  <div>
                    <p className="label">
                      DURABLE WAIT DEMO
                    </p>

                    <h3>
                      Can Relay continue after this session?
                    </h3>
                  </div>
                </div>

                <p className="durable-copy">
                  Persist the task,
                  schedule EventBridge,
                  and let Lambda restore
                  it later.
                </p>

                <button
                  className="resume-button"
                  disabled={
                    busy
                  }
                  onClick={
                    scheduleDurableResume
                  }
                >
                  Schedule real 2-minute AWS wake-up
                </button>
              </div>
            )}


          {waitState ===
            "SCHEDULED" && (
              <div className="durable-card">
                <div className="durable-heading">
                  <div className="durable-icon">
                    â—·
                  </div>

                  <div>
                    <p className="label">
                      DURABLE WAIT ACTIVE
                    </p>

                    <h3>
                      Relay is waiting outside this session
                    </h3>
                  </div>
                </div>

                <div className="durable-grid">
                  <DurableStep
                    title="DynamoDB"
                    value="Persisted"
                    done
                  />

                  <DurableStep
                    title="EventBridge"
                    value="Scheduled"
                    done
                  />

                  <DurableStep
                    title="Lambda"
                    value="Waiting"
                    waiting
                  />
                </div>

                {waitInfo?.run_at_utc && (
                  <div className="resume-time">
                    Scheduled wake-up:{" "}
                    <strong>
                      {formatFullTime(
                        waitInfo.run_at_utc,
                      )}
                    </strong>
                  </div>
                )}

                <button
                  className="reject"
                  onClick={
                    checkResumeNow
                  }
                  disabled={
                    busy
                  }
                >
                  Check resume now
                </button>
              </div>
            )}


          {waitState ===
            "RESUMED" && (
              <div className="durable-card resumed-card">
                <div className="durable-heading">
                  <div className="durable-icon">
                    ✓
                  </div>

                  <div>
                    <p className="label success-label">
                      TASK RESUMED
                    </p>

                    <h3>
                      Relay woke up without losing context
                    </h3>
                  </div>
                </div>

                <div className="durable-grid">
                  <DurableStep
                    title="EventBridge"
                    value="Triggered"
                    done
                  />

                  <DurableStep
                    title="State"
                    value="Restored"
                    done
                  />

                  <DurableStep
                    title="Resume count"
                    value={
                      resumedTask
                        ?.resume_count ??
                      1
                    }
                    done
                  />
                </div>
              </div>
            )}


          {!task &&
            !showShield && (
              <div className="composer">
                <textarea
                  rows="3"
                  value={
                    request
                  }
                  onChange={(
                    event,
                  ) =>
                    setRequest(
                      event.target.value,
                    )
                  }
                />

                <div className="composer-bottom">
                  <span>
→ Voice-style Alexa+ simulation
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


          {task && audit.length > 0 && (
            <div style={{ marginTop: "24px" }}>
              <DecisionReceiptTimeline events={audit} />
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
            <p className="label">
              DELEGATION CONTRACT
            </p>

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
                label="Resume"
                value="EventBridge + Lambda"
              />
            </div>
          </div>

          <div className="card">
            <p className="label">
              DEMO BOUNDARY
            </p>

            <div className="rows">
              <Row
                label="Alexa+ client"
                value="Simulated"
              />

              <Row
                label="Provider catalog"
                value="Simulated"
              />

              <Row
                label="MCP backend"
                value="Real"
                highlight
              />

              <Row
                label="Durable resume"
                value="Real AWS"
                highlight
              />
            </div>
          </div>


          {task && (
            <div className="card">
              <div className="card-heading">
                <p className="label">
                  TASK EVIDENCE
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
                  {
                    task.task_id
                  }
                </code>
              </div>

              <div className="rows">
                <Row
                  label="Audit events"
                  value={audit.length}
                />

                <Row
                  label="Recovery"
                  value={
                    recoveryOccurred
                      ? "Revalidated"
                      : "Ready"
                  }
                />

                <Row
                  label="Resume"
                  value={
                    waitState === "RESUMED"
                      ? "Restored"
                      : waitState === "SCHEDULED"
                        ? "Scheduled"
                        : "Available"
                  }
                />
              </div>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}


function DurableStep({
  title,
  value,
  done = false,
  waiting = false,
}) {
  return (
    <div
      className={`durable-step ${
        done
          ? "done"
          : waiting
            ? "waiting"
            : ""
      }`}
    >
      <span>
        {done
          ? "✓"
          : waiting
            ? "●"
            : "â—‹"}
      </span>

      <div>
        <small>
          {title}
        </small>

        <strong>
          {value}
        </strong>
      </div>
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
      <span>
        {label}
      </span>

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


function formatDate(
  value,
) {
  if (!value) {
    return "Unknown";
  }

  return new Intl.DateTimeFormat(
    "en-IN",
    {
      weekday:
        "long",
      day:
        "numeric",
      month:
        "short",
    },
  ).format(
    new Date(
      `${value}T12:00:00`,
    ),
  );
}


function formatTime(
  value,
) {
  if (!value) {
    return "";
  }

  return new Intl.DateTimeFormat(
    "en-IN",
    {
      hour:
        "2-digit",
      minute:
        "2-digit",
      second:
        "2-digit",
    },
  ).format(
    new Date(value),
  );
}


function formatFullTime(
  value,
) {
  if (!value) {
    return "";
  }

  return new Intl.DateTimeFormat(
    "en-IN",
    {
      hour:
        "2-digit",
      minute:
        "2-digit",
      second:
        "2-digit",
      day:
        "numeric",
      month:
        "short",
    },
  ).format(
    new Date(value),
  );
}


export default App;
