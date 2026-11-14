import React from "react";
import { CheckCircle2, Circle } from "lucide-react";

import { useResponsive } from "../hooks/useResponsive";

// ========================================
// COMPONENT
// ========================================

function StepsSidebar({
  page,
  currentPage,
  totalPages,
  selectedStep,
  completedSteps,
  onSelectStep,
}) {
  // ========================================
  // RESPONSIVE SCREEN DETECTION
  // ========================================

  const { isCompact, isSmallHeight } = useResponsive();

  // Enables the Raspberry Pi compact layout.
  const isKiosk = isCompact && isSmallHeight;

  // ========================================
  // STYLING
  // ========================================

  const styles = {
    // Main sidebar container
    sidebar: {
      width: isKiosk ? "210px" : "310px",
      flexShrink: 0,
      backgroundColor: "#101B2B",
      border: "1px solid #34465B",
      borderRadius: isKiosk ? "8px" : "12px",
      padding: isKiosk ? "8px" : "20px",
      display: "flex",
      flexDirection: "column",
      gap: isKiosk ? "8px" : "20px",
      minHeight: 0,
      overflow: "hidden",
    },

    // Sidebar title
    title: {
      fontSize: isKiosk ? "15px" : "24px",
      fontWeight: "bold",
      color: "#FFFFFF",
      margin: 0,
      lineHeight: 1.2,
    },

    // Current page indicator
    pageIndicator: {
      fontSize: isKiosk ? "10px" : "15px",
      color: "#9CAFC5",
      fontWeight: "normal",
    },

    // Container for instruction steps
    stepsContainer: {
      display: "flex",
      flexDirection: "column",
      gap: isKiosk ? "6px" : "12px",
      minHeight: 0,
      overflowY: isKiosk ? "auto" : "visible",
      scrollbarWidth: "thin",
    },

    // Individual step button
    step: {
      width: "100%",
      minHeight: isKiosk ? "40px" : "auto",
      flexShrink: 0,
      display: "flex",
      alignItems: "center",
      gap: isKiosk ? "7px" : "12px",
      padding: isKiosk ? "7px 8px" : "16px 14px",
      backgroundColor: "#172437",
      border: "1px solid #40536B",
      borderRadius: isKiosk ? "6px" : "10px",
      color: "#FFFFFF",
      textAlign: "left",
      cursor: "pointer",
      fontSize: isKiosk ? "11px" : "15px",
      transition: "background-color 0.2s ease, border-color 0.2s ease",
      boxSizing: "border-box",
    },

    // Selected step appearance
    selectedStep: {
      backgroundColor: "#0755A3",
      border: "2px solid #00BFFF",
    },

    // Completed step appearance
    completedStep: {
      backgroundColor: "#10352C",
      border: "1px solid #22C55E",
    },

    // Step text
    stepText: {
      flex: 1,
      minWidth: 0,
      lineHeight: isKiosk ? 1.2 : 1.4,
      overflowWrap: "break-word",
    },
  };

  // ========================================
  // LOGIC
  // ========================================

  // Determines the styling for each step.
  const getStepStyle = (step) => {
    // Check completion and selection state.
    const isCompleted = completedSteps.includes(step.id);
    const isSelected = selectedStep === step.id;

    // Combine base, completed, and selected styles.
    return {
      ...styles.step,
      ...(isCompleted ? styles.completedStep : {}),
      ...(isSelected ? styles.selectedStep : {}),
    };
  };

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <aside style={styles.sidebar}>
      {/* =====================================
          SIDEBAR HEADER
      ===================================== */}
      <div>
        <h2 style={styles.title}>
          Steps{" "}
          <span style={styles.pageIndicator}>
            {isKiosk
              ? `(${currentPage}/${totalPages})`
              : `(Page ${currentPage} of ${totalPages})`}
          </span>
        </h2>
      </div>

      {/* =====================================
          ASSEMBLY STEPS
      ===================================== */}
      <div style={styles.stepsContainer}>
        {page.steps.map((step) => {
          // Check whether the step is completed.
          const isCompleted = completedSteps.includes(step.id);

          return (
            <button
              key={step.id}
              type="button"
              style={getStepStyle(step)}
              onClick={() => onSelectStep(step.id)}
              aria-pressed={selectedStep === step.id}
            >
              {/* STEP STATUS ICON */}
              {isCompleted ? (
                <CheckCircle2
                  size={isKiosk ? 16 : 24}
                  color="#22C55E"
                  style={{ flexShrink: 0 }}
                />
              ) : (
                <Circle
                  size={isKiosk ? 16 : 24}
                  color="#CBD5E1"
                  style={{ flexShrink: 0 }}
                />
              )}

              {/* STEP NUMBER AND TITLE */}
              <span style={styles.stepText}>
                {step.id}. {step.title}
              </span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}

// ========================================
// EXPORT
// ========================================

export default StepsSidebar;
