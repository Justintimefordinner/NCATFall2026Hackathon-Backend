// ========================================
// IMPORTS
// ========================================

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  RefreshCw,
  Send,
  ShieldCheck,
  Terminal,
} from "lucide-react";

import { useMES } from "../context/MESContext";
import { useResponsive } from "../hooks/useResponsive";

// ========================================
// SUPERVISOR PAGE COMPONENT
// ========================================

function SupervisorPage() {
  // ========================================
  // RESPONSIVE SCREEN DETECTION
  // ========================================

  const { isMobile, isCompact, isSmallHeight } = useResponsive();
  const isKiosk = isCompact && isSmallHeight;

  // ========================================
  // STATE
  // ========================================

  const navigate = useNavigate();

  const { mesState, connected, error, elapsedSeconds, sendCommand } = useMES();

  const [pin, setPin] = useState("");
  const [alertMessage, setAlertMessage] = useState("");
  const [debugCommand, setDebugCommand] = useState("");
  const [actionFeedback, setActionFeedback] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // ========================================
  // BACKEND DATA
  // ========================================

  const operation = mesState?.operation ?? {};
  const labor = mesState?.labor ?? {};
  const progress = mesState?.progress ?? { signed: 0, total: 0 };
  const pendingInspector = mesState?.pending_inspector ?? [];
  const qualityAlert = mesState?.quality_alert ?? null;
  const commandLog = mesState?.log ?? [];

  // ========================================
  // CURRENT PAGE SUPERVISOR CHECKPOINTS
  // ========================================

  // Flask currently includes step metadata for the active page only.
  // Keep the overall operation progress accurate, and display precise
  // supervisor checkpoint positions on a separate current-page track.
  const currentPage = mesState?.page ?? {};
  const pageSteps = currentPage.steps ?? [];
  const checkpointSteps = pageSteps.filter((step) => step.inspector_required);
  const pageSignedCount = pageSteps.filter((step) => step.signed).length;
  const pageProgressPercent = pageSteps.length
    ? (pageSignedCount / pageSteps.length) * 100
    : 0;

  const progressPercent =
    progress.total > 0
      ? Math.round((progress.signed / progress.total) * 100)
      : 0;

  const formatTime = (seconds) => {
    const total = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const remainingSeconds = total % 60;

    return [hours, minutes, remainingSeconds]
      .map((value) => String(value).padStart(2, "0"))
      .join(":");
  };

  // ========================================
  // STYLING
  // ========================================

  const styles = {
    page: {
      minHeight: "100dvh",
      backgroundColor: "#08111F",
      color: "#FFFFFF",
      fontFamily: "Arial, sans-serif",
      padding: isCompact ? "12px" : "24px",
      boxSizing: "border-box",
    },

    header: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: "12px",
      flexWrap: "wrap",
      marginBottom: "18px",
    },

    heading: {
      margin: 0,
      fontSize: isCompact ? "20px" : "28px",
    },

    subtitle: {
      color: "#94A3B8",
      fontSize: "13px",
      marginTop: "5px",
    },

    backButton: {
      display: "flex",
      alignItems: "center",
      gap: "6px",
      backgroundColor: "#1E293B",
      border: "1px solid #334155",
      color: "#FFFFFF",
      padding: "10px 14px",
      borderRadius: "8px",
      cursor: "pointer",
    },

    connection: {
      color: connected ? "#22C55E" : "#EF4444",
      fontWeight: "bold",
      fontSize: "13px",
    },

    grid: {
      display: "grid",
      gridTemplateColumns: isMobile ? "1fr" : "repeat(2, minmax(0, 1fr))",
      gap: "16px",
      alignItems: "start",
    },

    card: {
      backgroundColor: "#111D30",
      border: "1px solid #26364B",
      borderRadius: "12px",
      padding: "16px",
      minWidth: 0,
    },

    cardTitle: {
      display: "flex",
      alignItems: "center",
      gap: "8px",
      margin: "0 0 14px",
      fontSize: "16px",
    },

    stats: {
      display: "grid",
      gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
      gap: "12px",
    },

    statLabel: {
      color: "#94A3B8",
      fontSize: "12px",
      marginBottom: "5px",
    },

    statValue: {
      fontSize: isCompact ? "16px" : "20px",
      fontWeight: "bold",
    },

    progressTrack: {
      height: "10px",
      backgroundColor: "#334155",
      borderRadius: "10px",
      overflow: "hidden",
      marginTop: "12px",
    },

    progressFill: {
      height: "100%",
      width: `${progressPercent}%`,
      backgroundColor: "#22C55E",
      transition: "width 0.3s ease",
    },

    // ========================================
    // CURRENT PAGE CHECKPOINT BAR
    // ========================================

    checkpointTrack: {
      position: "relative",
      height: "12px",
      backgroundColor: "#334155",
      borderRadius: "999px",
      marginTop: "12px",
      overflow: "visible",
    },

    checkpointFill: {
      height: "100%",
      width: `${pageProgressPercent}%`,
      backgroundColor: "#2563EB",
      borderRadius: "999px",
      transition: "width 0.3s ease",
    },

    checkpointLegend: {
      display: "flex",
      gap: "12px",
      flexWrap: "wrap",
      marginTop: "13px",
      fontSize: "11px",
      color: "#CBD5E1",
    },

    input: {
      width: "100%",
      boxSizing: "border-box",
      backgroundColor: "#08111F",
      color: "#FFFFFF",
      border: "1px solid #475569",
      borderRadius: "7px",
      padding: "10px",
      fontSize: "14px",
      marginBottom: "10px",
    },

    button: {
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      gap: "7px",
      border: "none",
      borderRadius: "7px",
      backgroundColor: "#2563EB",
      color: "#FFFFFF",
      padding: "10px 14px",
      cursor: "pointer",
      fontWeight: "bold",
      fontSize: "13px",
    },

    dangerButton: {
      backgroundColor: "#B91C1C",
    },

    successButton: {
      backgroundColor: "#15803D",
    },

    logContainer: {
      maxHeight: "280px",
      overflowY: "auto",
      display: "flex",
      flexDirection: "column",
      gap: "8px",
    },

    logEntry: {
      padding: "9px",
      backgroundColor: "#08111F",
      borderRadius: "6px",
      border: "1px solid #26364B",
      fontSize: "12px",
    },

    feedback: {
      margin: "12px 0",
      padding: "10px",
      backgroundColor: "#1E293B",
      borderRadius: "7px",
      fontSize: "13px",
    },
  };

  // ========================================
  // API HELPER
  // ========================================

  async function postAction(endpoint, body = {}) {
    if (isSubmitting) return;

    setIsSubmitting(true);
    setActionFeedback("");

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.message || `HTTP ${response.status}`);
      }

      setActionFeedback(result.message || "Action completed.");

      // Business-rule rejections may return HTTP 200.
      // Always inspect the backend's ok field.
      return result;
    } catch (err) {
      setActionFeedback(err.message || "Backend request failed.");
      return { ok: false };
    } finally {
      setIsSubmitting(false);
    }
  }

  // ========================================
  // SUPERVISOR ACTIONS
  // ========================================

  async function handleInspectorSignoff(page, step) {
    if (!pin.trim()) {
      setActionFeedback("Enter supervisor PIN first.");
      return;
    }

    const result = await postAction("/api/inspector/signoff", {
      pin,
      page,
      step,
    });

    if (result?.ok) setPin("");
  }

  async function handleTriggerAlert(event) {
    event.preventDefault();

    if (!alertMessage.trim()) {
      setActionFeedback("Enter an alert message.");
      return;
    }

    const result = await postAction("/api/quality/trigger", {
      message: alertMessage.trim(),
    });

    if (result?.ok) setAlertMessage("");
  }

  async function handleClearAlert() {
    if (!pin.trim()) {
      setActionFeedback("Enter supervisor PIN first.");
      return;
    }

    const result = await postAction("/api/quality/acknowledge", {
      pin,
    });

    if (result?.ok) setPin("");
  }

  async function handleDebugCommand(event) {
    event.preventDefault();

    if (!debugCommand.trim()) return;

    const result = await sendCommand(debugCommand.trim());
    setActionFeedback(result?.message || "Command submitted.");

    if (result?.ok) setDebugCommand("");
  }

  async function handleReset() {
    if (!window.confirm("Reset the entire MES demonstration?")) return;

    await postAction("/api/reset");
  }

  // ========================================
  // LOADING
  // ========================================

  if (!mesState) {
    return (
      <div style={styles.page}>
        <h2>Connecting to MES Supervisor Dashboard...</h2>
        <p>{error || "Waiting for Flask backend..."}</p>
      </div>
    );
  }

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <div style={styles.page}>
      {/* =====================================
          HEADER
      ===================================== */}
      <header style={styles.header}>
        <div>
          <h1 style={styles.heading}>MES Supervisor Dashboard</h1>
          <div style={styles.subtitle}>
            {operation.work_order} • {operation.operation}
          </div>
        </div>

        <span style={styles.connection}>
          {connected ? "● Live" : "● Disconnected"}
        </span>

        <button
          type="button"
          style={styles.backButton}
          onClick={() => navigate("/tech")}
        >
          <ArrowLeft size={16} />
          Technician View
        </button>
      </header>

      {/* =====================================
          ACTION FEEDBACK
      ===================================== */}
      {actionFeedback && (
        <div style={styles.feedback} role="status">
          {actionFeedback}
        </div>
      )}

      {/* =====================================
          MAIN SUPERVISOR GRID
      ===================================== */}
      <div style={styles.grid}>
        {/* OPERATION STATUS */}
        <section style={styles.card}>
          <h2 style={styles.cardTitle}>
            <Activity size={18} />
            Operation Status
          </h2>

          <div style={styles.stats}>
            <div>
              <div style={styles.statLabel}>Current Mode</div>
              <div style={styles.statValue}>{mesState.mode?.toUpperCase()}</div>
            </div>

            <div>
              <div style={styles.statLabel}>Current Page</div>
              <div style={styles.statValue}>
                {mesState.page?.number} / {operation.page_count}
              </div>
            </div>

            <div>
              <div style={styles.statLabel}>Labor Timer</div>
              <div style={styles.statValue}>{formatTime(elapsedSeconds)}</div>
            </div>

            <div>
              <div style={styles.statLabel}>Labor Status</div>
              <div
                style={{
                  ...styles.statValue,
                  color: labor.running ? "#22C55E" : "#FBBF24",
                }}
              >
                {labor.running ? "RUNNING" : "STOPPED"}
              </div>
            </div>
          </div>

          <div style={{ marginTop: "16px" }}>
            <div style={styles.statLabel}>
              Operation Progress: {progress.signed}/{progress.total} steps (
              {progressPercent}%)
            </div>
            <div style={styles.progressTrack}>
              <div style={styles.progressFill} />
            </div>

            {/* =====================================
                CURRENT PAGE APPROVAL CHECKPOINTS
                ===================================== */}
            <div style={{ marginTop: "19px" }}>
              <div style={styles.statLabel}>
                Page {currentPage.number ?? "—"} checkpoints: {pageSignedCount}/
                {pageSteps.length} steps
              </div>

              <div
                style={styles.checkpointTrack}
                role="img"
                aria-label={`Page ${currentPage.number ?? "current"} progress, ${pageSignedCount} of ${pageSteps.length} steps signed. ${checkpointSteps.length} supervisor checkpoints.`}
              >
                <div style={styles.checkpointFill} />

                {checkpointSteps.map((step) => {
                  const index = pageSteps.findIndex(
                    (item) => item.number === step.number,
                  );
                  const position = ((index + 1) / pageSteps.length) * 100;
                  const pending =
                    step.pending_inspector ||
                    pendingInspector.some(
                      (item) =>
                        item.page === currentPage.number &&
                        item.step === step.number,
                    );
                  const approved =
                    step.signed && step.signed_by === "supervisor";
                  const color = approved
                    ? "#22C55E"
                    : pending
                      ? "#EF4444"
                      : "#FBBF24";
                  const status = approved
                    ? "approved"
                    : pending
                      ? "approval pending"
                      : "approval upcoming";

                  return (
                    <div
                      key={`checkpoint-${currentPage.number}-${step.number}`}
                      title={`Step ${step.number}: ${status}`}
                      style={{
                        position: "absolute",
                        left: `${position}%`,
                        top: "50%",
                        transform: "translate(-50%, -50%)",
                        width: isKiosk ? "15px" : "18px",
                        height: isKiosk ? "15px" : "18px",
                        borderRadius: "50%",
                        backgroundColor: color,
                        border: "3px solid #111D30",
                        boxShadow: `0 0 0 1px ${color}`,
                        boxSizing: "border-box",
                        zIndex: 1,
                      }}
                    />
                  );
                })}
              </div>

              <div style={styles.checkpointLegend}>
                <span>🟡 Upcoming</span>
                <span>🔴 Pending</span>
                <span>🟢 Approved</span>
              </div>

              {checkpointSteps.length === 0 && (
                <div style={{ ...styles.statLabel, marginTop: "9px" }}>
                  No supervisor checkpoints on this page.
                </div>
              )}

              {checkpointSteps.length > 0 && (
                <div style={{ ...styles.statLabel, marginTop: "9px" }}>
                  Supervisor required:{" "}
                  {checkpointSteps
                    .map((step) => `Step ${step.number}`)
                    .join(", ")}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* INSPECTOR SIGN-OFF */}
        <section style={styles.card}>
          <h2 style={styles.cardTitle}>
            <ShieldCheck size={18} />
            Inspector Sign-Off
          </h2>

          <input
            type="password"
            style={styles.input}
            placeholder="Supervisor PIN"
            aria-label="Supervisor PIN"
            value={pin}
            onChange={(event) => setPin(event.target.value)}
          />

          {pendingInspector.length === 0 ? (
            <p style={{ color: "#94A3B8", fontSize: "13px" }}>
              No pending inspector approvals.
            </p>
          ) : (
            pendingInspector.map((item) => (
              <div
                key={`${item.page}-${item.step}`}
                style={{
                  ...styles.logEntry,
                  marginBottom: "10px",
                }}
              >
                <p>
                  Page {item.page}, Step {item.step}
                </p>

                <button
                  type="button"
                  style={{
                    ...styles.button,
                    ...styles.successButton,
                  }}
                  disabled={isSubmitting}
                  onClick={() => handleInspectorSignoff(item.page, item.step)}
                >
                  <CheckCircle2 size={15} />
                  Approve Step
                </button>
              </div>
            ))
          )}
        </section>

        {/* QUALITY ALERT */}
        <section style={styles.card}>
          <h2 style={styles.cardTitle}>
            <AlertTriangle size={18} />
            Quality Alert Management
          </h2>

          {qualityAlert ? (
            <div
              style={{
                ...styles.logEntry,
                borderColor: "#EF4444",
                marginBottom: "12px",
              }}
            >
              <strong style={{ color: "#FCA5A5" }}>ACTIVE ALERT</strong>
              <p>{qualityAlert}</p>

              <button
                type="button"
                style={{
                  ...styles.button,
                  ...styles.successButton,
                }}
                disabled={isSubmitting}
                onClick={handleClearAlert}
              >
                <ShieldCheck size={15} />
                Clear Alert (PIN Required)
              </button>
            </div>
          ) : (
            <p style={{ color: "#94A3B8", fontSize: "13px" }}>
              No active quality alerts.
            </p>
          )}

          <form onSubmit={handleTriggerAlert}>
            <input
              style={styles.input}
              placeholder="Describe a quality issue..."
              aria-label="Quality alert message"
              value={alertMessage}
              onChange={(event) => setAlertMessage(event.target.value)}
            />

            <button
              type="submit"
              style={{
                ...styles.button,
                ...styles.dangerButton,
              }}
              disabled={isSubmitting}
            >
              <AlertTriangle size={15} />
              Trigger Quality Alert
            </button>
          </form>
        </section>

        {/* COMMAND LOG */}
        <section style={styles.card}>
          <h2 style={styles.cardTitle}>
            <Clock3 size={18} />
            Command History
          </h2>

          <div style={styles.logContainer}>
            {commandLog.length === 0 ? (
              <p style={{ color: "#94A3B8", fontSize: "13px" }}>
                No commands recorded yet.
              </p>
            ) : (
              [...commandLog].reverse().map((entry, index) => (
                <div key={`${entry.ts}-${index}`} style={styles.logEntry}>
                  <div
                    style={{
                      color: entry.ok ? "#22C55E" : "#EF4444",
                      fontWeight: "bold",
                      marginBottom: "4px",
                    }}
                  >
                    {entry.ok ? "SUCCESS" : "REJECTED"} • {entry.source}
                  </div>

                  <div>{entry.input}</div>

                  <div style={{ color: "#94A3B8", marginTop: "4px" }}>
                    {entry.message}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* DEBUG COMMANDS */}
        <section style={styles.card}>
          <h2 style={styles.cardTitle}>
            <Terminal size={18} />
            Debug Voice Commands
          </h2>

          <form onSubmit={handleDebugCommand}>
            <input
              style={styles.input}
              placeholder='Try "start labor" or "next page"'
              aria-label="Debug command"
              value={debugCommand}
              onChange={(event) => setDebugCommand(event.target.value)}
            />

            <button type="submit" style={styles.button} disabled={isSubmitting}>
              <Send size={15} />
              Send Command
            </button>
          </form>
        </section>

        {/* DEMO RESET */}
        <section style={styles.card}>
          <h2 style={styles.cardTitle}>
            <RefreshCw size={18} />
            Demo Controls
          </h2>

          <p style={{ color: "#94A3B8", fontSize: "13px" }}>
            Reset the operation, labor timer, sign-offs, and quality alert for a
            fresh demonstration.
          </p>

          <button
            type="button"
            style={{
              ...styles.button,
              ...styles.dangerButton,
            }}
            disabled={isSubmitting}
            onClick={handleReset}
          >
            <RefreshCw size={15} />
            Reset Demonstration
          </button>
        </section>
      </div>
    </div>
  );
}

// ========================================
// EXPORT
// ========================================

export default SupervisorPage;
