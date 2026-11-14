import React, { useState } from "react";
import { Power, Factory, WifiOff } from "lucide-react";

import { useResponsive } from "../hooks/useResponsive";

// ========================================
// POWER SCREEN COMPONENT
// ========================================

function PowerScreen({ onPowerOn, connected }) {
  // ========================================
  // RESPONSIVE SCREEN DETECTION
  // ========================================

  const { isCompact, isSmallHeight } = useResponsive();
  const isKiosk = isCompact && isSmallHeight;

  // ========================================
  // LOCAL REQUEST STATE
  // ========================================

  const [isPoweringOn, setIsPoweringOn] = useState(false);
  const [error, setError] = useState("");

  // ========================================
  // POWER ACTIVATION HANDLER
  // ========================================

  const handlePowerOn = async () => {
    if (isPoweringOn || !onPowerOn) return;

    setIsPoweringOn(true);
    setError("");

    try {
      const result = await onPowerOn();

      if (result?.ok === false) {
        setError(result.message || "Activation failed.");
      }
    } catch (err) {
      setError(err.message || "Unable to activate MES.");
    } finally {
      setIsPoweringOn(false);
    }
  };

  // ========================================
  // STYLING
  // ========================================

  const styles = {
    container: {
      width: "100%",
      height: "100dvh",
      minHeight: 0,
      backgroundColor: "#08111F",
      color: "#FFFFFF",
      fontFamily: "Arial, sans-serif",
      display: "flex",
      flexDirection: "column",
      padding: isKiosk ? "12px 20px" : "24px 36px",
      boxSizing: "border-box",
      overflow: "hidden",
    },

    header: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: "12px",
    },

    brand: {
      display: "flex",
      alignItems: "center",
      gap: "12px",
      minWidth: 0,
    },

    brandIcon: {
      width: isKiosk ? "36px" : "46px",
      height: isKiosk ? "36px" : "46px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: "#0755A3",
      borderRadius: "9px",
      flexShrink: 0,
    },

    brandTitle: {
      fontSize: isKiosk ? "14px" : "19px",
      fontWeight: "bold",
    },

    brandSubtitle: {
      fontSize: isKiosk ? "9px" : "11px",
      color: "#94A3B8",
      marginTop: "4px",
    },

    standbyBadge: {
      color: "#FACC15",
      border: "1px solid #854D0E",
      borderRadius: "20px",
      padding: "6px 12px",
      fontSize: "11px",
      fontWeight: "bold",
      whiteSpace: "nowrap",
    },

    main: {
      display: "flex",
      flex: 1,
      minHeight: 0,
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: isKiosk ? "12px" : "20px",
    },

    powerButton: {
      width: isKiosk ? "104px" : "150px",
      height: isKiosk ? "104px" : "150px",
      borderRadius: "50%",
      border: "3px solid #38BDF8",
      backgroundColor: "#102D46",
      color: "#38BDF8",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      cursor: isPoweringOn ? "wait" : "pointer",
      boxShadow: "0 0 35px rgba(56,189,248,0.18)",
      opacity: isPoweringOn ? 0.65 : 1,
      touchAction: "manipulation",
    },

    heading: {
      fontSize: isKiosk ? "22px" : "32px",
      fontWeight: "bold",
      letterSpacing: "2px",
      textAlign: "center",
    },

    description: {
      fontSize: isKiosk ? "12px" : "15px",
      color: "#94A3B8",
      textAlign: "center",
    },

    error: {
      color: "#FCA5A5",
      fontSize: "12px",
      textAlign: "center",
    },

    footer: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: "12px",
      borderTop: "1px solid #34465B",
      paddingTop: "12px",
      color: "#94A3B8",
      fontSize: isKiosk ? "10px" : "12px",
    },
  };

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <div style={styles.container}>
      {/* HEADER */}
      <header style={styles.header}>
        <div style={styles.brand}>
          <div style={styles.brandIcon}>
            <Factory size={isKiosk ? 21 : 27} />
          </div>

          <div>
            <div style={styles.brandTitle}>
              Glorp Manufacturing Execution System
            </div>

            <div style={styles.brandSubtitle}>INDUSTRIAL CONTROL TERMINAL</div>
          </div>
        </div>

        <span style={styles.standbyBadge}>STANDBY</span>
      </header>

      {/* CENTER POWER CONTROL */}
      <main style={styles.main}>
        <button
          type="button"
          style={styles.powerButton}
          onClick={handlePowerOn}
          disabled={isPoweringOn}
          aria-label="Activate manufacturing execution system"
        >
          <Power size={isKiosk ? 55 : 78} strokeWidth={1.8} />
        </button>

        <div style={styles.heading}>SYSTEM STANDBY</div>

        <div style={styles.description}>
          {isPoweringOn
            ? "Activating manufacturing system..."
            : "Press the power button to activate the MES"}
        </div>

        {error && (
          <div style={styles.error} role="alert">
            {error}
          </div>
        )}
      </main>

      {/* FOOTER */}
      <footer style={styles.footer}>
        <span>NCAT FALL 2026 HACKATHON</span>

        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            color: connected ? "#4ADE80" : "#FACC15",
          }}
        >
          {!connected && <WifiOff size={14} />}
          {connected ? "BACKEND CONNECTED" : "LIVE CONNECTION OFFLINE"}
        </span>
      </footer>
    </div>
  );
}

// ========================================
// EXPORT
// ========================================

export default PowerScreen;
