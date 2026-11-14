// ========================================
// IMPORTS
// ========================================

import React, { createContext, useContext, useEffect, useState } from "react";

import { operation } from "../data/mockInstructions";

// ========================================
// CONTEXT CREATION
// ========================================

// Creates the shared MES context.
const MESContext = createContext(null);

// ========================================
// CONTEXT PROVIDER COMPONENT
// ========================================

export function MESProvider({ children }) {
  // ========================================
  // STYLING
  // ========================================

  // No styling is required here because
  // this component manages application data.

  // ========================================
  // STATE
  // ========================================

  // Tracks the current instruction page.
  const [currentPage, setCurrentPage] = useState(1);

  // Tracks the currently selected instruction step.
  const [selectedStep, setSelectedStep] = useState(
    operation.pages[0].steps[0]?.id ?? null,
  );

  // Stores completed assembly step IDs.
  const [completedSteps, setCompletedSteps] = useState(() =>
    operation.pages.flatMap((page) =>
      page.steps.filter((step) => step.completed).map((step) => step.id),
    ),
  );

  // Tracks whether labor is running.
  const [isLaborRunning, setIsLaborRunning] = useState(false);

  // Tracks elapsed labor time in seconds.
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Tracks whether simulated voice listening is enabled.
  const [isListening, setIsListening] = useState(false);

  // Stores the latest system feedback message.
  const [feedback, setFeedback] = useState("Voice control is off.");

  // Tracks whether supervisor authorization is required.
  const [isSupervisorLocked, setIsSupervisorLocked] = useState(false);

  // ========================================
  // DERIVED DATA
  // ========================================

  // Total number of instruction pages.
  const totalPages = operation.pages.length;

  // Retrieves the currently displayed instruction page.
  const activePage = operation.pages[currentPage - 1];

  // ========================================
  // LABOR TIMER
  // ========================================

  // Updates the labor timer while labor is running.
  useEffect(() => {
    if (!isLaborRunning) return;

    const interval = setInterval(() => {
      setElapsedSeconds((seconds) => seconds + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isLaborRunning]);

  // Starts the labor clock.
  const handleStartLabor = () => {
    if (isLaborRunning) {
      setFeedback("Labor is already running.");
      return;
    }

    setIsLaborRunning(true);
    setFeedback("Labor started.");
  };

  // Stops the labor clock.
  const handleStopLabor = () => {
    if (!isLaborRunning) {
      setFeedback("Labor is already stopped.");
      return;
    }

    setIsLaborRunning(false);
    setFeedback("Labor stopped.");
  };

  // ========================================
  // PAGE NAVIGATION
  // ========================================

  // Navigates to a specified instruction page.
  const navigateToPage = (pageNumber) => {
    // Prevents navigation outside the available pages.
    if (pageNumber < 1 || pageNumber > totalPages) {
      setFeedback("No page available in that direction.");
      return;
    }

    // Updates the current page.
    setCurrentPage(pageNumber);

    // Selects the first step on the new page.
    setSelectedStep(operation.pages[pageNumber - 1].steps[0]?.id ?? null);

    setFeedback(`Opened page ${pageNumber}.`);
  };

  // Navigates backward.
  const handlePreviousPage = () => {
    navigateToPage(currentPage - 1);
  };

  // Navigates forward.
  const handleNextPage = () => {
    navigateToPage(currentPage + 1);
  };

  // ========================================
  // STEP MANAGEMENT
  // ========================================

  // Selects an instruction step.
  const handleSelectStep = (stepId) => {
    setSelectedStep(stepId);
  };

  // Signs off a single step.
  const handleSignOffStep = (stepId) => {
    // Verify that the step exists on the current page.
    const stepExists = activePage.steps.some((step) => step.id === stepId);

    if (!stepExists) {
      setFeedback("Step not found on the current page.");
      return;
    }

    // Prevent duplicate sign-offs.
    if (completedSteps.includes(stepId)) {
      setFeedback(`Step ${stepId} is already completed.`);
      return;
    }

    // Demo-only sign-off.
    setCompletedSteps((previous) => [...previous, stepId]);

    setFeedback(`Step ${stepId} signed off (demo).`);
  };

  // Signs off every step on the current page.
  const handleSignOffPage = () => {
    // Collect all step IDs from the current page.
    const pageStepIds = activePage.steps.map((step) => step.id);

    // Mark every step as completed.
    setCompletedSteps((previous) => [
      ...new Set([...previous, ...pageStepIds]),
    ]);

    // Advance automatically if another page exists.
    if (currentPage < totalPages) {
      navigateToPage(currentPage + 1);

      setFeedback(`Page ${currentPage} signed off (demo).`);
    } else {
      setFeedback("Final page signed off (demo).");
    }
  };

  // ========================================
  // VOICE CONTROL
  // ========================================

  // Toggles simulated voice listening.
  const handleToggleListening = () => {
    setIsListening((previous) => !previous);

    setFeedback(
      isListening ? "Voice control stopped." : "Voice control started.",
    );
  };

  // Processes simulated voice commands.
  const handleVoiceCommand = (command) => {
    if (!isListening) {
      setFeedback("Voice control is not listening.");
      return;
    }

    switch (command.toLowerCase().trim()) {
      case "next page":
        handleNextPage();
        break;

      case "previous page":
        handlePreviousPage();
        break;

      case "start labor":
        handleStartLabor();
        break;

      case "stop labor":
        handleStopLabor();
        break;

      case "sign off step":
        handleSignOffStep(selectedStep);
        break;

      case "sign off page":
        handleSignOffPage();
        break;

      default:
        setFeedback("Command not recognized.");
        break;
    }
  };

  // ========================================
  // SUPERVISOR AUTHORIZATION
  // ========================================

  // Activates the supervisor lock.
  const requestSupervisor = () => {
    setIsSupervisorLocked(true);
    setFeedback("Supervisor authorization required.");
  };

  // Clears the supervisor lock after authorization.
  // This must only be called after successful PIN validation.
  const authorizeSupervisor = () => {
    setIsSupervisorLocked(false);
    setFeedback("Supervisor authorization successful.");
  };

  // ========================================
  // CONTEXT VALUES
  // ========================================

  // Makes all shared state and actions available
  // to the dashboard and supervisor page.
  const contextValue = {
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
    isSupervisorLocked,

    handleStartLabor,
    handleStopLabor,
    navigateToPage,
    handlePreviousPage,
    handleNextPage,
    handleSelectStep,
    handleSignOffStep,
    handleSignOffPage,
    handleToggleListening,
    handleVoiceCommand,
    requestSupervisor,
    authorizeSupervisor,
  };

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <MESContext.Provider value={contextValue}>{children}</MESContext.Provider>
  );
}

// ========================================
// CUSTOM HOOK
// ========================================

// Allows components to access shared MES state.
export function useMES() {
  const context = useContext(MESContext);

  if (!context) {
    throw new Error("useMES must be used inside MESProvider.");
  }

  return context;
}
