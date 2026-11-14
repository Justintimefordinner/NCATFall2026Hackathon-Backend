// ========================================
// IMPORTS
// ========================================

import React from "react";
import { AlertTriangle } from "lucide-react";

// Responsive screen detection
import { useResponsive } from "../hooks/useResponsive";

// ========================================
// SUPERVISOR ALERT COMPONENT
// ========================================

function SupervisorAlert() {
  // ========================================
  // RESPONSIVE SCREEN DETECTION
  // ========================================

  const { isCompact, isSmallHeight } = useResponsive();

  // Enables the Raspberry Pi kiosk layout.
  const isKiosk = isCompact && isSmallHeight;

  // ========================================
  // STYLING
  // ========================================

  const styles = {
    // Main warning banner
    container: {
      position: "absolute",
      top: isKiosk ? 0 : "90px",
      left: isKiosk ? 0 : "20px",
      right: isKiosk ? 0 : "20px",
      zIndex: 1001,

      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: isKiosk ? "10px" : "20px",

      height: isKiosk ? "44px" : "auto",
      padding: isKiosk ? "0 12px" : "18px 24px",
      boxSizing: "border-box",

      backgroundColor: "#7F1D1D",
      border: isKiosk ? "none" : "2px solid #EF4444",
      borderBottom: isKiosk ? "2px solid #EF4444" : "2px solid #EF4444",

      borderRadius: isKiosk ? 0 : "12px",

      boxShadow: isKiosk
        ? "0 2px 12px rgba(239, 68, 68, 0.3)"
        : "0 0 25px rgba(239, 68, 68, 0.35)",

      color: "#FFFFFF",
      overflow: "hidden",
    },

    // Warning message
    title: {
      margin: 0,
      fontSize: isKiosk ? "16px" : "clamp(20px, 2.5vw, 32px)",
      fontWeight: "bold",
      textAlign: "center",
      lineHeight: 1.2,
      whiteSpace: isKiosk ? "nowrap" : "normal",
    },
  };

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <div style={styles.container} role="alert">
      {/* =====================================
          WARNING ICON
      ===================================== */}
      <AlertTriangle
        size={isKiosk ? 21 : 36}
        color="#FFFFFF"
        style={{ flexShrink: 0 }}
      />

      {/* =====================================
          PERMANENT SUPERVISOR WARNING
      ===================================== */}
      <h1 style={styles.title}>Supervisor Attention Required</h1>
    </div>
  );
}

// ========================================
// EXPORT
// ========================================

export default SupervisorAlert;
