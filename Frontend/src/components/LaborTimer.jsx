import React, { useState } from "react";

import { Play, Square, Clock3 } from "lucide-react";

import { useResponsive } from "../hooks/useResponsive";

// ========================================
// COMPONENT
// ========================================

function LaborTimer({
  isLaborRunning = false,
  elapsedSeconds = 0,
  onStartLabor,
  onStopLabor,
}) {
  // ========================================
  // RESPONSIVE SCREEN DETECTION
  // ========================================

  const { isCompact, isSmallHeight } = useResponsive();

  // Enables the compact Raspberry Pi layout.
  const isKiosk = isCompact && isSmallHeight;

  // ========================================
  // LOCAL UI STATE
  // ========================================

  // Tracks whether a labor command is pending.
  // This does not replace backend labor state.
  const [isProcessing, setIsProcessing] = useState(false);

  // ========================================
  // TIME FORMATTING
  // ========================================

  // Converts elapsed seconds into HH:MM:SS.
  const formatTime = (seconds) => {
    // Prevent invalid or negative time values.
    const safeSeconds = Math.max(0, Math.floor(Number(seconds) || 0));

    const hours = Math.floor(safeSeconds / 3600);

    const minutes = Math.floor((safeSeconds % 3600) / 60);

    const remainingSeconds = safeSeconds % 60;

    return [hours, minutes, remainingSeconds]
      .map((value) => String(value).padStart(2, "0"))
      .join(":");
  };

  // ========================================
  // LABOR COMMAND HANDLER
  // ========================================

  const handleLaborToggle = async () => {
    // Prevent duplicate commands.
    if (isProcessing) return;

    // Determine which backend command to send.
    const action = isLaborRunning ? onStopLabor : onStartLabor;

    if (typeof action !== "function") return;

    setIsProcessing(true);

    try {
      // Wait for Flask to process the command.
      await action();
    } catch (error) {
      console.error("Labor command failed:", error);
    } finally {
      // The parent updates isLaborRunning
      // using authoritative backend state.
      setIsProcessing(false);
    }
  };

  // ========================================
  // STYLING
  // ========================================

  const styles = {
    // Main labor timer container
    container: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: isKiosk ? "8px" : "18px",
      padding: isKiosk ? "5px 8px" : "16px 22px",
      backgroundColor: "#FFFFFF",
      border: "1px solid #E4E4E7",
      borderRadius: isKiosk ? "8px" : "12px",
      minWidth: isKiosk ? 0 : "300px",
      minHeight: isKiosk ? "52px" : "auto",
      height: isKiosk ? "52px" : "auto",
      flex: isKiosk ? 1 : "initial",
      boxSizing: "border-box",
    },

    // Timer information
    timerInfo: {
      display: "flex",
      alignItems: "center",
      gap: isKiosk ? "7px" : "14px",
      minWidth: 0,
    },

    // Timer status text
    status: {
      fontSize: isKiosk ? "11px" : "14px",
      fontWeight: "600",
      color: isLaborRunning ? "#16A34A" : "#EA580C",
      whiteSpace: "nowrap",
    },

    // Timer digits
    time: {
      fontSize: isKiosk ? "18px" : "27px",
      fontWeight: "bold",
      color: "#18181B",
      fontVariantNumeric: "tabular-nums",
      lineHeight: 1.1,
      whiteSpace: "nowrap",
    },

    // Start and stop button
    button: {
      width: isKiosk ? "40px" : "54px",
      height: isKiosk ? "40px" : "54px",
      minWidth: isKiosk ? "40px" : "54px",
      minHeight: isKiosk ? "40px" : "54px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: isLaborRunning ? "#DC2626" : "#16A34A",
      border: isLaborRunning ? "1px solid #B91C1C" : "1px solid #15803D",
      borderRadius: "50%",
      color: "#FFFFFF",
      cursor: isProcessing ? "wait" : "pointer",
      flexShrink: 0,
      padding: 0,
      touchAction: "manipulation",
      opacity: isProcessing ? 0.5 : 1,
    },
  };

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <section style={styles.container}>
      {/* =====================================
          LABOR STATUS AND TIME
      ===================================== */}
      <div style={styles.timerInfo}>
        {/* TIMER ICON */}
        <Clock3
          size={isKiosk ? 19 : 26}
          color={isLaborRunning ? "#16A34A" : "#EA580C"}
          style={{ flexShrink: 0 }}
        />

        {/* TIMER STATUS AND DIGITS */}
        <div>
          <div style={styles.status}>
            {isLaborRunning ? "Labor Running" : "Labor Stopped"}
          </div>

          <div style={styles.time}>{formatTime(elapsedSeconds)}</div>
        </div>
      </div>

      {/* =====================================
          START / STOP LABOR BUTTON
      ===================================== */}
      <button
        type="button"
        style={styles.button}
        onClick={handleLaborToggle}
        disabled={isProcessing}
        aria-label={isLaborRunning ? "Stop labor" : "Start labor"}
        title={isLaborRunning ? "Stop labor" : "Start labor"}
      >
        {isLaborRunning ? (
          <Square size={isKiosk ? 17 : 22} fill="currentColor" />
        ) : (
          <Play size={isKiosk ? 19 : 25} fill="currentColor" />
        )}
      </button>
    </section>
  );
}

// ========================================
// EXPORT
// ========================================

export default LaborTimer;
