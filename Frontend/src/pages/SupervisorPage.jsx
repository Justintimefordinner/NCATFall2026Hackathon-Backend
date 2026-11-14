// ========================================
// IMPORTS
// ========================================

import React from "react";
import { useNavigate } from "react-router-dom";

// Existing dashboard component
import App from "../App";

// Supervisor authorization components
import SupervisorAlert from "../components/SupervisorAlert";
import SupervisorPinPad from "../components/SupervisorPinPad";

// Responsive screen detection
import { useResponsive } from "../hooks/useResponsive";

// Shared MES context
import { useMES } from "../context/MESContext";

// ========================================
// SUPERVISOR PAGE COMPONENT
// ========================================

function SupervisorPage() {
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
    // Main supervisor page container
    container: {
      position: "relative",
      width: "100%",
      height: isKiosk ? "100dvh" : "auto",
      minHeight: isKiosk ? 0 : "100dvh",
      backgroundColor: "#08111F",
      overflow: "hidden",
      boxSizing: "border-box",
      isolation: "isolate",
    },

    // Existing dashboard displayed behind the lock
    dashboard: {
      width: "100%",
      height: isKiosk ? "100%" : "auto",
      pointerEvents: "none",
      userSelect: "none",
      overflow: "hidden",
    },

    // Dark overlay that covers the dashboard
    overlay: {
      position: "fixed",
      inset: 0,
      backgroundColor: isKiosk ? "rgba(0, 0, 0, 0.72)" : "rgba(0, 0, 0, 0.65)",
      zIndex: 1000,
      pointerEvents: "auto",
    },

    // Container that centers the PIN keypad
    pinPadWrapper: {
      position: "fixed",
      top: isKiosk ? "44px" : 0,
      right: 0,
      bottom: 0,
      left: 0,
      zIndex: 1002,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: isKiosk ? "6px 12px" : "24px",
      pointerEvents: "none",
      boxSizing: "border-box",
      overflow: "hidden",
    },

    // Allows interaction with the PIN keypad
    pinPad: {
      pointerEvents: "auto",
      width: isKiosk ? "100%" : "auto",
      maxWidth: isKiosk ? "360px" : "none",
      maxHeight: "100%",
      minHeight: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    },
  };

  // ========================================
  // STATE & LOGIC
  // ========================================

  // React Router navigation function.
  const navigate = useNavigate();

  // Retrieves the supervisor authorization action
  // from our shared MES context.
  const { authorizeSupervisor } = useMES();

  // ========================================
  // SUPERVISOR AUTHORIZATION HANDLER
  // ========================================

  // Called only when the correct PIN is entered.
  const handleAuthorized = () => {
    // Removes the supervisor lock.
    authorizeSupervisor();

    // Returns to the normal dashboard route.
    // replace prevents adding the supervisor
    // screen to the browser's navigation history.
    navigate("/", { replace: true });
  };

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <div style={styles.container}>
      {/* =====================================
          EXISTING DASHBOARD BACKGROUND

          Uses the same App.jsx and shared
          MESContext state as the normal screen.

          Preserves:
          - Current instruction page
          - Selected instruction step
          - Current instruction image
          - Completed steps
          - Labor timer state
      ===================================== */}
      <div style={styles.dashboard} inert={true} aria-hidden="true">
        <App />
      </div>

      {/* =====================================
          DARK SUPERVISOR OVERLAY

          Visually locks the workstation.
          The dashboard cannot be interacted
          with while this overlay is active.
      ===================================== */}
      <div style={styles.overlay} aria-hidden="true" />

      {/* =====================================
          PERMANENT SUPERVISOR ALERT

          Displays the red warning banner.
          No close or dismiss button.
      ===================================== */}
      <SupervisorAlert />

      {/* =====================================
          SUPERVISOR PIN PAD

          Correct PIN:
          - Unlocks the dashboard
          - Navigates back to "/"

          Incorrect PIN:
          - Keeps the dashboard locked
      ===================================== */}
      <div style={styles.pinPadWrapper}>
        <div style={styles.pinPad}>
          <SupervisorPinPad onAuthorized={handleAuthorized} />
        </div>
      </div>
    </div>
  );
}

// ========================================
// EXPORT
// ========================================

export default SupervisorPage;
