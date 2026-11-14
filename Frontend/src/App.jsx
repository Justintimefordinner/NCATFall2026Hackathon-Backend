import React from "react";
import { useNavigate } from "react-router-dom";

// ========================================
// DASHBOARD COMPONENT IMPORTS
// ========================================

import Header from "./components/Header";
import OperationInfo from "./components/OperationInfo";
import StepsSidebar from "./components/StepsSidebar";
import InstructionViewer from "./components/InstructionViewer";
import NavigationBar from "./components/NavigationBar";
import LaborTimer from "./components/LaborTimer";
import VoiceControl from "./components/VoiceControl";

// ========================================
// POWER SCREEN COMPONENT
// ========================================

import PowerScreen from "./components/PowerScreen";

// ========================================
// RESPONSIVE HOOK
// ========================================

import { useResponsive } from "./hooks/useResponsive";

// ========================================
// SHARED MES STATE
// ========================================

import { useMES } from "./context/MESContext";

// ========================================
// MAIN DASHBOARD COMPONENT
// ========================================

function App() {
  // ========================================
  // ROUTER NAVIGATION
  // ========================================

  // Navigate between technician and
  // supervisor dashboards.
  const navigate = useNavigate();

  // ========================================
  // RESPONSIVE SCREEN DETECTION
  // ========================================

  const { isMobile, isCompact, isSmallHeight } = useResponsive();

  // Enable Raspberry Pi kiosk layout.
  const isKiosk = isCompact && isSmallHeight;

  // ========================================
  // SHARED BACKEND STATE & LOGIC
  // ========================================

  const {
    // Backend connection state
    mesState,
    connected,
    error,

    // Manufacturing operation data
    operation,
    currentPage,
    selectedStep,
    completedSteps,
    totalPages,
    activePage,

    // Labor and voice state
    isLaborRunning,
    elapsedSeconds,
    isListening,
    feedback,

    // Power activation
    handlePowerOn,

    // Labor commands
    handleStartLabor,
    handleStopLabor,

    // Page navigation
    handlePreviousPage,
    handleNextPage,

    // Step selection and sign-off
    handleSelectStep,
    handleSignOffStep,
    handleSignOffPage,

    // Voice controls
    handleToggleListening,
    handleVoiceCommand,
  } = useMES();

  // ========================================
  // SUPERVISOR APPROVAL STATUS
  // ========================================

  const pendingInspector = mesState?.pending_inspector ?? [];

  // Show the prompt only for the selected pending step.
  const selectedPendingApproval =
    pendingInspector.find(
      (item) =>
        Number(item.page) === Number(currentPage) &&
        Number(item.step) === Number(selectedStep),
    ) ?? null;

  const supervisorApprovalRequired = Boolean(selectedPendingApproval);

  // ========================================
  // STYLING
  // ========================================

  const styles = {
    // Main application container
    app: {
      width: "100%",
      height: "100dvh",
      minHeight: 0,
      backgroundColor: "#F9FAFB",
      color: "#18181B",
      fontFamily: "ui-sans-serif, system-ui, sans-serif",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      boxSizing: "border-box",
    },

    // Backend connection warning
    connectionWarning: {
      backgroundColor: "#FEF2F2",
      color: "#B91C1C",
      padding: isKiosk ? "4px 8px" : "10px 16px",
      fontSize: isKiosk ? "10px" : "13px",
      textAlign: "center",
      flexShrink: 0,
    },

    // Initial backend loading screen
    loading: {
      width: "100%",
      height: "100dvh",
      backgroundColor: "#F9FAFB",
      color: "#18181B",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: "12px",
      padding: "20px",
      fontFamily: "ui-sans-serif, system-ui, sans-serif",
      textAlign: "center",
      boxSizing: "border-box",
    },

    // Main work instructions area
    mainContent: {
      display: "flex",
      flexDirection: "row",
      flex: 1,
      minHeight: 0,
      minWidth: 0,
      padding: "clamp(4px, 0.9vh, 12px) clamp(6px, 1vw, 20px)",
      gap: "clamp(4px, 0.8vh, 12px)",
      overflow: "hidden",
    },

    // Voice control and labor timer row
    controlsRow: {
      display: "flex",
      flexDirection: "row",
      alignItems: "stretch",
      flexShrink: 0,
      gap: "clamp(4px, 0.8vh, 12px)",
      padding: "0 clamp(6px, 1vw, 20px) clamp(3px, 0.7vh, 10px)",
    },

    // Supervisor dashboard button row
    supervisorRow: {
      display: "flex",
      alignItems: "center",
      justifyContent: "flex-start",
      flexShrink: 0,
      padding: "0 clamp(6px, 1vw, 20px) 4px",
    },

    // Supervisor dashboard button
    supervisorButton: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      minHeight: isKiosk ? "32px" : "44px",
      padding: isKiosk ? "5px 12px" : "12px 18px",
      backgroundColor: "#FEF2F2",
      border: "1px solid #FECACA",
      borderRadius: isKiosk ? "6px" : "8px",
      color: "#FFFFFF",
      fontSize: isKiosk ? "11px" : "14px",
      fontWeight: "bold",
      cursor: "pointer",
      whiteSpace: "nowrap",
      touchAction: "manipulation",
    },
  };

  // ========================================
  // INITIAL BACKEND LOADING STATE
  // ========================================

  // Wait for Flask to provide the first
  // manufacturing operation snapshot.
  //
  // This prevents incomplete operation
  // information from appearing at startup.

  if (!mesState) {
    return (
      <div style={styles.loading}>
        <h2 style={{ margin: 0 }}>Connecting to MES...</h2>

        <p
          style={{
            color: "#71717A",
            fontSize: "14px",
            margin: 0,
          }}
        >
          Waiting for manufacturing operation data.
        </p>

        {error && (
          <p
            role="alert"
            style={{
              color: "#DC2626",
              fontSize: "13px",
              margin: 0,
            }}
          >
            Connection error: {error}
          </p>
        )}
      </div>
    );
  }

  // ========================================
  // SYSTEM STANDBY / POWER SCREEN
  // ========================================

  // Flask controls the actual MES mode.
  //
  // When the backend reports IDLE,
  // the technician dashboard is hidden.
  //
  // Pressing Power calls the backend,
  // which transitions IDLE -> ARRIVED.
  //
  // Once the updated state is received,
  // React automatically renders the
  // normal technician dashboard.

  if (mesState.mode === "idle") {
    return <PowerScreen onPowerOn={handlePowerOn} connected={connected} />;
  }

  // ========================================
  // MAIN TECHNICIAN DASHBOARD
  // ========================================

  return (
    <div style={styles.app}>
      {/* =====================================
          BACKEND CONNECTION WARNING
      ===================================== */}
      {!connected && (
        <div style={styles.connectionWarning} role="alert">
          MES live connection unavailable. Waiting for backend
          synchronization...
        </div>
      )}

      {/* =====================================
          APPLICATION HEADER
      ===================================== */}
      <Header station={operation.station} technician={operation.technician} />

      {/* =====================================
          OPERATION INFORMATION
      ===================================== */}
      <OperationInfo operation={operation} currentPage={currentPage} />

      {/* =====================================
          MAIN WORK INSTRUCTIONS AREA
      ===================================== */}
      <main style={styles.mainContent}>
        {/* LEFT SIDEBAR */}
        <StepsSidebar
          page={activePage}
          currentPage={currentPage}
          totalPages={totalPages}
          selectedStep={selectedStep}
          completedSteps={completedSteps}
          onSelectStep={handleSelectStep}
        />

        {/* MAIN INSTRUCTION VIEWER */}
        <InstructionViewer page={activePage} selectedStep={selectedStep} />
      </main>

      {/* =====================================
          VOICE CONTROL AND LABOR TIMER
      ===================================== */}
      <div style={styles.controlsRow}>
        {/* VOICE ASSISTANT */}
        <VoiceControl
          isListening={isListening}
          onToggleListening={handleToggleListening}
          onVoiceCommand={handleVoiceCommand}
          feedback={feedback}
        />

        {/* LABOR TIMER */}
        <LaborTimer
          isLaborRunning={isLaborRunning}
          elapsedSeconds={elapsedSeconds}
          onStartLabor={handleStartLabor}
          onStopLabor={handleStopLabor}
        />
      </div>

      {/* =====================================
        CONDITIONAL SUPERVISOR APPROVAL
      ===================================== */}

      {supervisorApprovalRequired && (
        <div
          style={{
            flexShrink: 0,
            padding: "clamp(3px, 0.7vh, 8px) clamp(6px, 1vw, 20px)",
            backgroundColor: "#FEF2F2",
            borderTop: "1px solid #FECACA",
            borderBottom: "1px solid #FECACA",
            display: "flex",
            flexDirection: "column",
            gap: "clamp(2px, 0.5vh, 8px)",
          }}
        >
          {/* SUPERVISOR NOTIFICATION */}
          <div
            role="alert"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              color: "#DC2626",
              fontSize: isKiosk ? "11px" : "14px",
              fontWeight: "bold",
              textAlign: "center",
            }}
          >
            🔒 Supervisor Approval Required — Page{" "}
            {selectedPendingApproval.page}, Step {selectedPendingApproval.step}
          </div>

          {/* SUPERVISOR BUTTON */}
          <button
            type="button"
            onClick={() => navigate("/supervisor")}
            style={{
              width: "100%",
              minHeight: "clamp(26px, 5vh, 40px)",
              borderRadius: "7px",
              border: "1px solid #FECACA",
              backgroundColor: "#DC2626",
              color: "#FFFFFF",
              fontSize: isKiosk ? "11px" : "14px",
              fontWeight: "bold",
              cursor: "pointer",
              touchAction: "manipulation",
            }}
          >
            Supervisor Approval — Enter PIN
          </button>
        </div>
      )}

      {/* =====================================
          BOTTOM NAVIGATION BAR
      ===================================== */}
      <NavigationBar
        currentPage={currentPage}
        totalPages={totalPages}
        selectedStep={selectedStep}
        onPreviousPage={handlePreviousPage}
        onNextPage={handleNextPage}
        onSignOffStep={handleSignOffStep}
        onSignOffPage={handleSignOffPage}
      />
    </div>
  );
}

// ========================================
// EXPORT
// ========================================

export default App;
