import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import DecisionReceiptTimeline from "./DecisionReceiptTimeline";
import { createScamApi } from "../lib/scamApi";
import "../styles/scam-shield.css";

const OWNER_ID = "user_savita";

const FINAL_STATES = new Set([
  "APPROVED",
  "REJECTED",
  "EXPIRED_BLOCKED",
  "CLEARED",
  "BLOCKED",
]);

const SAMPLE_MESSAGE =
  "Your electricity connection will be disconnected today. Call +91 98765 43210 immediately and pay ₹25,000 to avoid suspension.";


function unwrap(value) {
  if (
    value &&
    typeof value === "object" &&
    "result" in value
  ) {
    return value.result;
  }

  return value;
}


function getRiskScore(result) {
  return (
    result?.risk_score ??
    result?.score ??
    result?.risk?.score ??
    0
  );
}


function getSignals(result) {
  const signals =
    result?.signals ??
    result?.risk?.signals ??
    [];

  return Array.isArray(signals)
    ? signals
    : [];
}


function getCaseId(result) {
  return (
    result?.task_id ??
    result?.case_id ??
    result?.case?.case_id ??
    result?.id ??
    null
  );
}


export default function ScamShieldFlow({
  callTool,
}) {
  const api =
    useMemo(
      () =>
        createScamApi(
          callTool,
        ),
      [callTool],
    );

  const copyTimerRef =
    useRef(null);

  const [message, setMessage] =
    useState(SAMPLE_MESSAGE);

  const [sender, setSender] =
    useState(
      "+91 98765 43210",
    );

  const [analysis, setAnalysis] =
    useState(null);

  const [
    numberResult,
    setNumberResult,
  ] = useState(null);

  const [amount, setAmount] =
    useState("25000");

  const [
    payeeLabel,
    setPayeeLabel,
  ] = useState(
    "New electricity payee",
  );

  const [
    payeeIsNew,
    setPayeeIsNew,
  ] = useState(true);

  const [
    assessment,
    setAssessment,
  ] = useState(null);

  const [caseId, setCaseId] =
    useState(null);

  const [
    caseData,
    setCaseData,
  ] = useState(null);

  const [receipt, setReceipt] =
    useState(null);

  const [
    activeContact,
    setActiveContact,
  ] = useState("c_rohan");

  const [
    familyInbox,
    setFamilyInbox,
  ] = useState(null);

  const [busy, setBusy] =
    useState(false);

  const [error, setError] =
    useState("");

  const [copied, setCopied] =
    useState(false);


  const currentState =
    caseData?.state ??
    caseData?.status ??
    "";


  useEffect(() => {
    return () => {
      if (
        copyTimerRef.current
      ) {
        window.clearTimeout(
          copyTimerRef.current,
        );

        copyTimerRef.current =
          null;
      }
    };
  }, []);


  useEffect(() => {
    if (!caseId) {
      return undefined;
    }

    let live = true;
    let interval = null;

    async function refreshCase() {
      try {
        const current =
          unwrap(
            await api.getCase(
              caseId,
              OWNER_ID,
            ),
          );

        if (!live) {
          return;
        }

        setCaseData(
          current,
        );

        const state =
          current?.state ??
          current?.status ??
          "";

        if (
          FINAL_STATES.has(
            state,
          )
        ) {
          if (interval) {
            window.clearInterval(
              interval,
            );

            interval = null;
          }

          const evidence =
            unwrap(
              await api.getReceipt(
                caseId,
                OWNER_ID,
              ),
            );

          if (live) {
            setReceipt(
              evidence,
            );
          }
        }
      } catch (refreshError) {
        if (live) {
          setError(
            refreshError instanceof
              Error
              ? refreshError.message
              : "Unable to refresh protection case.",
          );
        }
      }
    }

    refreshCase();

    interval =
      window.setInterval(
        refreshCase,
        3000,
      );

    return () => {
      live = false;

      if (interval) {
        window.clearInterval(
          interval,
        );
      }
    };
  }, [
    api,
    caseId,
  ]);


  useEffect(() => {
    if (
      !caseId ||
      FINAL_STATES.has(
        currentState,
      )
    ) {
      return undefined;
    }

    let live = true;

    async function refreshInbox() {
      try {
        const inbox =
          unwrap(
            await api.inbox(
              caseId,
              activeContact,
            ),
          );

        if (live) {
          setFamilyInbox(
            inbox,
          );
        }
      } catch {
        if (live) {
          setFamilyInbox(
            null,
          );
        }
      }
    }

    refreshInbox();

    const interval =
      window.setInterval(
        refreshInbox,
        3000,
      );

    return () => {
      live = false;

      window.clearInterval(
        interval,
      );
    };
  }, [
    api,
    caseId,
    activeContact,
    currentState,
  ]);


  async function handleAnalyze() {
    if (!message.trim()) {
      setError(
        "Enter a suspicious message first.",
      );

      return;
    }

    setBusy(true);
    setError("");
    setAnalysis(null);
    setNumberResult(null);
    setAssessment(null);
    setCaseId(null);
    setCaseData(null);
    setReceipt(null);
    setFamilyInbox(null);

    try {
      const result =
        unwrap(
          await api.analyze(
            message.trim(),
            sender.trim() ||
              null,
          ),
        );

      setAnalysis(result);

      if (sender.trim()) {
        try {
          const checked =
            unwrap(
              await api.checkNumber(
                sender.trim(),
              ),
            );

          setNumberResult(
            checked,
          );
        } catch {
          setNumberResult(
            null,
          );
        }
      }
    } catch (analyzeError) {
      setError(
        analyzeError instanceof
          Error
          ? analyzeError.message
          : "Unable to analyze message.",
      );
    } finally {
      setBusy(false);
    }
  }


  async function handlePayment() {
    if (!analysis) {
      setError(
        "Analyze the suspicious message first.",
      );

      return;
    }

    const numericAmount =
      Number(amount);

    if (
      !Number.isFinite(
        numericAmount,
      ) ||
      numericAmount <= 0
    ) {
      setError(
        "Enter a valid payment amount.",
      );

      return;
    }

    setBusy(true);
    setError("");
    setAssessment(null);
    setCaseId(null);
    setCaseData(null);
    setReceipt(null);
    setFamilyInbox(null);

    try {
      const riskScore =
        getRiskScore(
          analysis,
        );

      const assessed =
        unwrap(
          await api.assess(
            OWNER_ID,
            riskScore,
            numericAmount,
            payeeIsNew,
          ),
        );

      setAssessment(
        assessed,
      );

      const decision =
        assessed?.decision ??
        assessed?.risk
          ?.decision ??
        "";

      if (
        decision !== "HOLD"
      ) {
        return;
      }

      const opened =
        unwrap(
          await api.openCase({
            ownerId:
              OWNER_ID,
            riskScore,
            amount:
              numericAmount,
            payeeLabel:
              payeeLabel.trim() ||
              "New payee",
            payeeIsNew,
            signals: getSignals(analysis).map((signal) => {
              if (typeof signal === "string") {
                return signal;
              }

              const name = signal?.name ?? "signal";
              const evidence = signal?.evidence;

              return evidence
                ? `${name}: ${evidence}`
                : name;
            }),
            coolingOffMinutes:
              2,
          }),
        );

      const nextCaseId =
        getCaseId(
          opened,
        );

      if (!nextCaseId) {
        throw new Error(
          "Relay opened a protection case but did not return a case ID.",
        );
      }

      setCaseId(
        nextCaseId,
      );

      setCaseData(
        opened,
      );
    } catch (paymentError) {
      setError(
        paymentError instanceof
          Error
          ? paymentError.message
          : "Unable to protect this payment.",
      );
    } finally {
      setBusy(false);
    }
  }


  async function handleDecision(
    decision,
  ) {
    const code =
      familyInbox
        ?.approval_code;

    if (
      !caseId ||
      !code
    ) {
      setError(
        "No family approval code is available on this family device yet.",
      );

      return;
    }

    setBusy(true);
    setError("");

    try {
      const result =
        unwrap(
          await api.decide(
            caseId,
            activeContact,
            code,
            decision,
          ),
        );

      if (result) {
        setCaseData(
          result,
        );
      }

      const current =
        unwrap(
          await api.getCase(
            caseId,
            OWNER_ID,
          ),
        );

      setCaseData(
        current,
      );

      const evidence =
        unwrap(
          await api.getReceipt(
            caseId,
            OWNER_ID,
          ),
        );

      setReceipt(
        evidence,
      );
    } catch (decisionError) {
      setError(
        decisionError instanceof
          Error
          ? decisionError.message
          : "Unable to record family decision.",
      );
    } finally {
      setBusy(false);
    }
  }


  async function copyComplaint() {
    if (!receipt) {
      return;
    }

    try {
      const text =
        typeof receipt ===
        "string"
          ? receipt
          : JSON.stringify(
              receipt,
              null,
              2,
            );

      await navigator.clipboard
        .writeText(text);

      setCopied(true);

      if (
        copyTimerRef.current
      ) {
        window.clearTimeout(
          copyTimerRef.current,
        );
      }

      copyTimerRef.current =
        window.setTimeout(
          () => {
            setCopied(false);

            copyTimerRef.current =
              null;
          },
          1500,
        );
    } catch {
      setError(
        "Unable to copy the evidence summary.",
      );
    }
  }


  const events =
    receipt?.events ??
    receipt?.timeline ??
    caseData?.events ??
    [];


  return (
    <section className="shield-shell">
      <div className="shield-header">
        <div>
          <p className="relay-eyebrow">
            Relay Shield
          </p>

          <h2>
            Scam protection for
            families
          </h2>

          <p>
            Detect suspicious
            pressure, hold risky
            payments and require a
            trusted family decision
            before money can move.
          </p>
        </div>

        <span className="shield-status">
          {currentState ||
            "READY"}
        </span>
      </div>


      {error && (
        <div className="shield-error">
          {error}
        </div>
      )}


      <div className="shield-grid">
        <article className="shield-phone">
          <div className="shield-phone__title">
            Savita&apos;s phone
          </div>

          <p className="shield-phone__hint">
            Protected user
          </p>

          <label>
            Suspicious message
          </label>

          <textarea
            value={message}
            onChange={(
              event,
            ) =>
              setMessage(
                event.target
                  .value,
              )
            }
            rows={6}
          />

          <label>
            Sender / phone number
          </label>

          <input
            value={sender}
            onChange={(
              event,
            ) =>
              setSender(
                event.target
                  .value,
              )
            }
          />

          <button
            type="button"
            disabled={busy}
            onClick={
              handleAnalyze
            }
          >
            Analyze message
          </button>


          {analysis && (
            <div className="shield-result">
              <div className="shield-result__headline">
                <strong>
                  Risk score:{" "}
                  {getRiskScore(
                    analysis,
                  )}
                </strong>

                {(
                  analysis?.risk_level ??
                  analysis?.risk_tier ??
                  analysis?.tier
                ) && (
                  <span>
                    {analysis
                      ?.risk_level ??
                      analysis
                        ?.risk_tier ??
                      analysis
                        ?.tier}
                  </span>
                )}
              </div>

              {getSignals(
                analysis,
              ).length >
                0 && (
                <>
                  <small>
                    Detected signals
                  </small>

                  <ul>
                    {getSignals(
                      analysis,
                    ).map(
                      (
                        signal,
                        index,
                      ) => (
                        <li
                          key={`${String(
                            signal,
                          )}-${index}`}
                        >
                          {typeof signal ===
                          "string"
                            ? signal
                            : JSON.stringify(
                                signal,
                              )}
                        </li>
                      ),
                    )}
                  </ul>
                </>
              )}

              {analysis?.advice && (
                <p>
                  {analysis.advice}
                </p>
              )}
            </div>
          )}


          {numberResult && (
            <div className="shield-result">
              <small>
                Number reputation
              </small>

              <strong>
                {numberResult
                  ?.reputation ??
                  numberResult
                    ?.status ??
                  numberResult
                    ?.risk ??
                  "Checked"}
              </strong>

              {numberResult
                ?.reason && (
                <p>
                  {
                    numberResult.reason
                  }
                </p>
              )}
            </div>
          )}


          <div className="shield-divider" />


          <div className="shield-payment-heading">
            <div>
              <small>
                Protected payment
              </small>

              <strong>
                Payment review
              </strong>
            </div>

            <span>
              Human controlled
            </span>
          </div>


          <label>
            Payment amount
          </label>

          <input
            type="number"
            value={amount}
            min="1"
            onChange={(
              event,
            ) =>
              setAmount(
                event.target
                  .value,
              )
            }
          />

          <label>
            Payee
          </label>

          <input
            value={payeeLabel}
            onChange={(
              event,
            ) =>
              setPayeeLabel(
                event.target
                  .value,
              )
            }
          />

          <label className="shield-check">
            <input
              type="checkbox"
              checked={
                payeeIsNew
              }
              onChange={(
                event,
              ) =>
                setPayeeIsNew(
                  event.target
                    .checked,
                )
              }
            />

            <span>
              This is a new payee
            </span>
          </label>

          <button
            type="button"
            disabled={
              busy ||
              !analysis
            }
            onClick={
              handlePayment
            }
          >
            Assess ₹
            {Number(
              amount || 0,
            ).toLocaleString(
              "en-IN",
            )}{" "}
            payment
          </button>


          {assessment && (
            <div className="shield-result">
              <small>
                Relay policy
              </small>

              <strong>
                Decision:{" "}
                {assessment
                  ?.decision ??
                  "UNKNOWN"}
              </strong>

              {assessment
                ?.reasons &&
                Array.isArray(
                  assessment.reasons,
                ) && (
                  <ul>
                    {assessment.reasons.map(
                      (
                        reason,
                        index,
                      ) => (
                        <li
                          key={`${String(
                            reason,
                          )}-${index}`}
                        >
                          {String(
                            reason,
                          )}
                        </li>
                      ),
                    )}
                  </ul>
                )}
            </div>
          )}


          {caseId && (
            <div className="shield-hold">
              <span>
                PAYMENT PROTECTED
              </span>

              <strong>
                {currentState ||
                  "HELD"}
              </strong>

              <p>
                Relay opened a
                protection case and
                notified the trusted
                family contact. Silence
                never releases money.
              </p>

              <code>
                {caseId}
              </code>
            </div>
          )}
        </article>


        <article className="shield-phone shield-phone--family">
          <div className="shield-phone__title">
            Family phone
          </div>

          <p className="shield-phone__hint">
            Simulated private delivery
            channel
          </p>


          <div className="shield-tabs">
            <button
              type="button"
              className={
                activeContact ===
                "rohan"
                  ? "active"
                  : ""
              }
              onClick={() => {
                setFamilyInbox(
                  null,
                );

                setActiveContact(
                  "c_rohan",
                );
              }}
            >
              Rohan
            </button>

            <button
              type="button"
              className={
                activeContact ===
                "anita"
                  ? "active"
                  : ""
              }
              onClick={() => {
                setFamilyInbox(
                  null,
                );

                setActiveContact(
                  "c_anita",
                );
              }}
            >
              Anita
            </button>
          </div>


          {!caseId && (
            <div className="shield-empty">
              <strong>
                No family alert yet
              </strong>

              <p>
                Analyze Savita&apos;s
                message and assess the
                protected payment
                first.
              </p>
            </div>
          )}


          {caseId &&
            !familyInbox &&
            !FINAL_STATES.has(
              currentState,
            ) && (
              <div className="shield-empty">
                <strong>
                  Waiting for private
                  family alert…
                </strong>

                <p>
                  Relay is polling the
                  simulated family
                  device every three
                  seconds.
                </p>
              </div>
            )}


          {familyInbox && (
            <div className="shield-family-message">
              <div className="shield-family-alert">
                <span>
                  PRIVATE FAMILY ALERT
                </span>

                <strong>
                  Review requested
                </strong>
              </div>

              <p>
                {familyInbox
                  ?.message ??
                  familyInbox
                    ?.summary ??
                  "A protected family payment needs your review."}
              </p>


              {familyInbox
                ?.approval_code && (
                  <div className="shield-code">
                    <span>
                      Approval code
                    </span>

                    <strong>
                      {
                        familyInbox
                          .approval_code
                      }
                    </strong>

                    <small>
                      Visible only on
                      this simulated
                      family device.
                    </small>
                  </div>
                )}


              {!FINAL_STATES.has(
                currentState,
              ) && (
                <div className="shield-actions">
                  <button
                    type="button"
                    disabled={
                      busy ||
                      !familyInbox
                        ?.approval_code
                    }
                    onClick={() =>
                      handleDecision(
                        "APPROVE",
                      )
                    }
                  >
                    Approve
                  </button>

                  <button
                    type="button"
                    className="shield-reject"
                    disabled={
                      busy ||
                      !familyInbox
                        ?.approval_code
                    }
                    onClick={() =>
                      handleDecision(
                        "REJECT",
                      )
                    }
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          )}


          {FINAL_STATES.has(
            currentState,
          ) && (
            <div className="shield-final">
              <small>
                Final protection state
              </small>

              <strong>
                {currentState}
              </strong>

              <p>
                Family review is
                complete. The private
                family channel is no
                longer being polled.
              </p>
            </div>
          )}
        </article>


        <article className="shield-evidence">
          <div className="shield-evidence__heading">
            <div>
              <p className="relay-eyebrow">
                Decision Evidence
              </p>

              <h3>
                Auditable protection
                trail
              </h3>
            </div>

            {currentState && (
              <span className="shield-status">
                {currentState}
              </span>
            )}
          </div>

          {!caseId && (
            <div className="shield-empty">
              <p>
                Evidence appears here
                after Relay opens a
                protection case.
              </p>
            </div>
          )}

          {caseId && (
            <DecisionReceiptTimeline
              events={events}
            />
          )}

          {receipt && (
            <button
              type="button"
              className="shield-copy"
              onClick={
                copyComplaint
              }
            >
              {copied
                ? "Evidence copied"
                : "Copy complaint evidence"}
            </button>
          )}
        </article>
      </div>
    </section>
  );
}