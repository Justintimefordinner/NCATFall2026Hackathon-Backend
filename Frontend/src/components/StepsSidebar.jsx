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
      width: "clamp(150px, 26vw, 310px)",
      flexShrink: 0,
      backgroundColor: "#FFFFFF",
      border: "1px solid #E4E4E7",
      borderRadius: isKiosk ? "8px" : "12px",
      padding: "clamp(5px, 1vh, 14px)",
      display: "flex",
      flexDirection: "column",
      gap: "clamp(4px, 0.8vh, 12px)",
      minHeight: 0,
      overflow: "hidden",
      boxSizing: "border-box",
    },

    // Sidebar title
    title: {
      fontSize: "clamp(13px, 2.5vh, 22px)",
      fontWeight: "bold",
      color: "#18181B",
      margin: 0,
      lineHeight: 1.2,
    },

    // Current page indicator
    pageIndicator: {
      fontSize: isKiosk ? "10px" : "15px",
      color: "#71717A",
      fontWeight: "normal",
    },

    // Container for instruction steps
    stepsContainer: {
      display: "flex",
      flexDirection: "column",
      gap: "clamp(3px, 0.6vh, 8px)",
      minHeight: 0,
      overflowY: "auto",
      scrollbarWidth: "thin",
    },

    // Individual step button
    step: {
      width: "100%",
      minHeight: "clamp(32px, 7vh, 50px)",
      flexShrink: 0,
      display: "flex",
      alignItems: "center",
      gap: isKiosk ? "7px" : "12px",
      padding: "clamp(4px, 0.8vh, 9px) 7px",
      backgroundColor: "#F9FAFB",
      border: "1px solid #E4E4E7",
      borderRadius: isKiosk ? "6px" : "10px",
      color: "#18181B",
      textAlign: "left",
      cursor: "pointer",
      fontSize: "clamp(10px, 1.6vh, 14px)",
      transition: "background-color 0.2s ease, border-color 0.2s ease",
      boxSizing: "border-box",
    },

    // Selected step appearance
    selectedStep: {
      backgroundColor: "#EFF6FF",
      border: "2px solid #2563EB",
    },

    // Completed step appearance
    completedStep: {
      backgroundColor: "#F0FDF4",
      border: "1px solid #16A34A",
    },

    // Waiting for inspector approval
    pendingStep: {
      backgroundColor: "#FFF7ED",
      border: "1px solid #EA580C",
    },

    // Inspector-required step
    inspectorStep: {
      border: "1px solid #8B5CF6",
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
      fontSize: "clamp(9px, 1.35vh, 11px)",
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
          <p
            style={{
              color: "#71717A",
              fontSize: "12px",
            }}
          >
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
            let statusColor = "#A1A1AA";
            let statusText = null;

            if (isCompleted) {
              StatusIcon = CheckCircle2;
              statusColor = "#16A34A";
              statusText = "Signed Off";
            } else if (isPending) {
              StatusIcon = Clock3;
              statusColor = "#EA580C";
              statusText = "Pending Inspector";
            } else if (requiresInspector) {
              StatusIcon = ShieldAlert;
              statusColor = "#8B5CF6";
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
