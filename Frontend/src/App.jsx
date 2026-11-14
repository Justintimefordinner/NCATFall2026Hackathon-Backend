import React from "react";

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
  // RESPONSIVE SCREEN DETECTION
  // ========================================

  const { isMobile, isCompact, isSmallHeight } = useResponsive();

  // Enable compact kiosk layout.
  const isKiosk = isCompact && isSmallHeight;

  // ========================================
  // STYLING
  // ========================================

  const styles = {
    // Main application container
    app: {
      width: "100%",
      height: isKiosk ? "100dvh" : "auto",
      minHeight: isKiosk ? 0 : "100dvh",
      backgroundColor: "#08111F",
      color: "#FFFFFF",
      fontFamily: "Arial, sans-serif",
      display: "flex",
      flexDirection: "column",
      overflow: isKiosk ? "hidden" : "visible",
      boxSizing: "border-box",
    },

    // Main work instructions area
    mainContent: {
      display: "flex",
      flexDirection: isMobile ? "column" : "row",
      flex: 1,
      minHeight: 0,
      minWidth: 0,
      padding: isKiosk ? "6px 8px" : isCompact ? "8px" : "16px 20px",
      gap: isKiosk ? "8px" : "16px",
      overflow: isKiosk ? "hidden" : "visible",
    },

    // Voice control and labor timer row
    controlsRow: {
      display: "flex",
      flexDirection: isMobile ? "column" : "row",
      alignItems: "stretch",
      flexShrink: 0,
      gap: isKiosk ? "8px" : "16px",
      padding: isKiosk ? "0 8px 6px" : isCompact ? "0 8px 8px" : "0 20px 16px",
    },

    // Supervisor button row
    supervisorRow: {
      display: "flex",
      alignItems: "center",
      justifyContent: "flex-start",
      flexShrink: 0,
      padding: isKiosk ? "0 8px 5px" : "0 20px 16px",
    },

    // Supervisor authorization button
    supervisorButton: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      minHeight: isKiosk ? "32px" : "44px",
      padding: isKiosk ? "5px 12px" : "12px 18px",
      backgroundColor: "#7F1D1D",
      border: "1px solid #EF4444",
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
  // SHARED STATE & LOGIC
  // ========================================

  // Retrieve dashboard data and actions.
  const {
    operation,
    currentPage,
    selectedStep,
    completedSteps,
    totalPages,
    activePage,
    isLaborRunning,
    elapsedSeconds,
    isListening,
    feedback,

    handleStartLabor,
    handleStopLabor,
    handlePreviousPage,
    handleNextPage,
    handleSelectStep,
    handleSignOffStep,
    handleSignOffPage,
    handleToggleListening,
    handleVoiceCommand,
    requestSupervisor,
  } = useMES();

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <div style={styles.app}>
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

        {/* LABOR CLOCK */}
        <LaborTimer
          isLaborRunning={isLaborRunning}
          elapsedSeconds={elapsedSeconds}
          onStartLabor={handleStartLabor}
          onStopLabor={handleStopLabor}
        />
      </div>

      {/* =====================================
          SUPERVISOR AUTHORIZATION
      ===================================== */}
      <div style={styles.supervisorRow}>
        <button
          type="button"
          style={styles.supervisorButton}
          onClick={requestSupervisor}
        >
          {isKiosk
            ? "Supervisor Authorization"
            : "Request Supervisor Authorization"}
        </button>
      </div>

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
