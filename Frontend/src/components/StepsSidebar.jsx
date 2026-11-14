import React from "react";

import { CheckCircle2, Circle, Clock3, ShieldAlert } from "lucide-react";

import { useResponsive } from "../hooks/useResponsive";

// ========================================
// COMPONENT
// ========================================

function StepsSidebar({
  page,
  currentPage,
  totalPages,
  selectedStep,
  completedSteps = [],
  onSelectStep,
}) {
  // ========================================
  // RESPONSIVE SCREEN DETECTION
  // ========================================

  const { isCompact, isSmallHeight } = useResponsive();

  // Enables the Raspberry Pi compact layout.
  const isKiosk = isCompact && isSmallHeight;

  // ========================================
  // BACKEND STEP DATA
  // ========================================

  // Flask provides page.steps with:
  // number, text, signed, signed_by,
  // inspector_required, pending_inspector.
  const steps = page?.steps ?? [];

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
      boxSizing: "border-box",
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

    // Waiting for inspector approval
    pendingStep: {
      backgroundColor: "#3B2B10",
      border: "1px solid #FACC15",
    },

    // Inspector-required step
    inspectorStep: {
      border: "1px solid #A78BFA",
    },

    // Step text
    stepText: {
      flex: 1,
      minWidth: 0,
      lineHeight: isKiosk ? 1.2 : 1.4,
      overflowWrap: "break-word",
    },

    // Small status label
    statusLabel: {
      display: "block",
      fontSize: isKiosk ? "9px" : "12px",
      marginTop: "4px",
      fontWeight: "bold",
    },
  };

  // ========================================
  // STEP STATUS HELPERS
  // ========================================

  // Determine whether a step is complete.
  const isStepCompleted = (step) =>
    step.signed === true || completedSteps.includes(step.id ?? step.number);

  // Determine the visual appearance of a step.
  const getStepStyle = (step) => {
    const isCompleted = isStepCompleted(step);

    const isPending = step.pending_inspector === true;

    const requiresInspector = step.inspector_required === true;

    const isSelected = selectedStep === (step.id ?? step.number);

    return {
      ...styles.step,
      ...(requiresInspector ? styles.inspectorStep : {}),
      ...(isCompleted ? styles.completedStep : {}),
      ...(isPending && !isCompleted ? styles.pendingStep : {}),
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
        {steps.length === 0 ? (
          <p style={{ color: "#94A3B8", fontSize: "12px" }}>
            No steps available.
          </p>
        ) : (
          steps.map((step) => {
            // ========================================
            // STEP STATUS
            // ========================================

            const stepId = step.id ?? step.number;

            const isCompleted = isStepCompleted(step);

            const isPending = step.pending_inspector === true;

            const requiresInspector = step.inspector_required === true;

            const isSelected = selectedStep === stepId;

            // ========================================
            // STEP STATUS ICON
            // ========================================

            let StatusIcon = Circle;
            let statusColor = "#CBD5E1";
            let statusText = null;

            if (isCompleted) {
              StatusIcon = CheckCircle2;
              statusColor = "#22C55E";
              statusText = "Signed Off";
            } else if (isPending) {
              StatusIcon = Clock3;
              statusColor = "#FACC15";
              statusText = "Pending Inspector";
            } else if (requiresInspector) {
              StatusIcon = ShieldAlert;
              statusColor = "#A78BFA";
              statusText = "Inspector Required";
            }

            // ========================================
            // STEP BUTTON
            // ========================================

            return (
              <button
                key={stepId}
                type="button"
                style={getStepStyle(step)}
                onClick={() => onSelectStep(stepId)}
                aria-pressed={isSelected}
              >
                {/* STATUS ICON */}
                <StatusIcon
                  size={isKiosk ? 16 : 24}
                  color={statusColor}
                  style={{ flexShrink: 0 }}
                />

                {/* STEP NUMBER AND TEXT */}
                <span style={styles.stepText}>
                  <span>
                    {step.number}. {step.text}
                  </span>

                  {statusText && (
                    <span
                      style={{
                        ...styles.statusLabel,
                        color: statusColor,
                      }}
                    >
                      {statusText}
                    </span>
                  )}
                </span>
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}

// ========================================
// EXPORT
// ========================================

export default StepsSidebar;
