import React from "react";
import { Play, Square, Clock3 } from "lucide-react";

import { useResponsive } from "../hooks/useResponsive";

// ========================================
// COMPONENT
// ========================================

function LaborTimer({
  isLaborRunning,
  elapsedSeconds,
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
      backgroundColor: "#101B2B",
      border: "1px solid #34465B",
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
      color: isLaborRunning ? "#22C55E" : "#FACC15",
      whiteSpace: "nowrap",
    },

    // Timer digits
    time: {
      fontSize: isKiosk ? "18px" : "27px",
      fontWeight: "bold",
      color: "#FFFFFF",
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
      backgroundColor: isLaborRunning ? "#7F1D1D" : "#14532D",
      border: isLaborRunning ? "1px solid #EF4444" : "1px solid #22C55E",
      borderRadius: "50%",
      color: "#FFFFFF",
      cursor: "pointer",
      flexShrink: 0,
      padding: 0,
      touchAction: "manipulation",
    },
  };

  // ========================================
  // LOGIC
  // ========================================

  // Converts seconds into HH:MM:SS.
  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;

    return [hours, minutes, remainingSeconds]
      .map((value) => String(value).padStart(2, "0"))
      .join(":");
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
          color={isLaborRunning ? "#22C55E" : "#FACC15"}
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
        onClick={isLaborRunning ? onStopLabor : onStartLabor}
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
