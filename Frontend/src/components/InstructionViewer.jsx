import React from "react";
import { CheckCircle2, ClipboardList, Info, ShieldAlert } from "lucide-react";

import { useResponsive } from "../hooks/useResponsive";

// ========================================
// COMPONENT
// ========================================

function InstructionViewer({ page, selectedStep }) {
  // ========================================
  // RESPONSIVE SCREEN DETECTION
  // ========================================

  const { isCompact, isSmallHeight } = useResponsive();

  // Enables the compact kiosk layout.
  const isKiosk = isCompact && isSmallHeight;

  // ========================================
  // BACKEND INSTRUCTION DATA
  // ========================================

  // The backend provides steps instead of
  // the old mock page.instructions array.
  const steps = page?.steps ?? [];

  // Find the currently selected instruction.
  const activeStep =
    steps.find((step) => step.id === selectedStep) ?? steps[0] ?? null;

  // Display the selected step number and page title.
  const displayTitle = activeStep
    ? `${page?.title ?? "Assembly"} — Step ${activeStep.number}`
    : (page?.title ?? "Assembly Instructions");

  // Flask provides image URLs such as:
  // /static/img/p1s1.jpg
  const imageSource = activeStep?.image ?? null;

  // Step completion information.
  const isSigned = activeStep?.signed ?? false;

  const inspectorRequired = activeStep?.inspector_required ?? false;

  const pendingInspector = activeStep?.pending_inspector ?? false;

  // ========================================
  // STYLING
  // ========================================

  const styles = {
    // Main instruction viewer container
    container: {
      flex: 1,
      minWidth: 0,
      minHeight: 0,
      backgroundColor: "#FFFFFF",
      border: "1px solid #E4E4E7",
      borderRadius: isKiosk ? "8px" : "12px",
      padding: isKiosk ? "10px" : "24px",
      display: "flex",
      flexDirection: "column",
      gap: isKiosk ? "8px" : "24px",
      overflow: "hidden",
      boxSizing: "border-box",
    },

    // Instruction page title
    title: {
      fontSize: isKiosk ? "16px" : "25px",
      fontWeight: "bold",
      color: "#18181B",
      margin: 0,
      lineHeight: 1.2,
      flexShrink: 0,
    },

    // Main content layout
    content: {
      display: "flex",
      flexDirection: "row",
      gap: isKiosk ? "10px" : "24px",
      flex: 1,
      minHeight: 0,
      minWidth: 0,
    },

    // Image display container
    imageContainer: {
      flex: isKiosk ? 1.2 : 1.4,
      minWidth: 0,
      minHeight: 0,
      backgroundColor: "#F9FAFB",
      border: "1px solid #E4E4E7",
      borderRadius: isKiosk ? "6px" : "10px",
      overflow: "hidden",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    },

    // Assembly image
    image: {
      width: "100%",
      height: "100%",
      maxHeight: isKiosk ? "100%" : "480px",
      objectFit: "contain",
      display: "block",
    },

    // Missing image placeholder
    imagePlaceholder: {
      color: "#71717A",
      fontSize: isKiosk ? "11px" : "15px",
      textAlign: "center",
      padding: "12px",
    },

    // Right instruction panel
    instructionsPanel: {
      flex: 1,
      minWidth: 0,
      minHeight: 0,
      display: "flex",
      flexDirection: "column",
      gap: isKiosk ? "6px" : "20px",
      overflowY: isKiosk ? "auto" : "visible",
      scrollbarWidth: "thin",
    },

    // Instruction heading
    heading: {
      display: "flex",
      alignItems: "center",
      gap: isKiosk ? "5px" : "10px",
      color: "#2563EB",
      fontSize: isKiosk ? "13px" : "21px",
      fontWeight: "bold",
      flexShrink: 0,
    },

    // Instruction text
    instructionText: {
      color: "#18181B",
      fontSize: isKiosk ? "12px" : "18px",
      lineHeight: isKiosk ? 1.4 : 1.6,
      margin: 0,
    },

    // Step status
    status: {
      display: "flex",
      alignItems: "center",
      gap: "6px",
      fontSize: isKiosk ? "10px" : "14px",
      fontWeight: "bold",
      color: isSigned ? "#16A34A" : pendingInspector ? "#EA580C" : "#71717A",
    },

    // Important information box
    note: {
      backgroundColor: "#FFF7ED",
      border: "1px solid #FDBA74",
      borderRadius: isKiosk ? "6px" : "10px",
      padding: isKiosk ? "7px" : "18px",
      marginTop: isKiosk ? "4px" : "auto",
      flexShrink: 0,
    },

    // Note heading
    noteHeading: {
      display: "flex",
      alignItems: "center",
      gap: isKiosk ? "5px" : "10px",
      color: "#C2410C",
      fontSize: isKiosk ? "11px" : "18px",
      fontWeight: "bold",
      marginBottom: isKiosk ? "4px" : "10px",
    },

    // Note description
    noteText: {
      color: "#57534E",
      fontSize: isKiosk ? "10px" : "15px",
      lineHeight: isKiosk ? 1.3 : 1.5,
      margin: 0,
    },
  };

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <section style={styles.container}>
      {/* =====================================
          INSTRUCTION TITLE
      ===================================== */}
      <h2 style={styles.title}>{displayTitle}</h2>

      {/* =====================================
          MAIN INSTRUCTION CONTENT
      ===================================== */}
      <div style={styles.content}>
        {/* =====================================
            ASSEMBLY IMAGE
        ===================================== */}
        <div style={styles.imageContainer}>
          {imageSource ? (
            <img
              src={imageSource}
              alt={`Assembly reference for step ${activeStep.number}`}
              style={styles.image}
            />
          ) : (
            <div style={styles.imagePlaceholder}>
              No instruction image available.
            </div>
          )}
        </div>

        {/* =====================================
            INSTRUCTIONS PANEL
        ===================================== */}
        <div style={styles.instructionsPanel}>
          {/* INSTRUCTION HEADING */}
          <div style={styles.heading}>
            <ClipboardList size={isKiosk ? 15 : 25} style={{ flexShrink: 0 }} />
            <span>Instructions</span>
          </div>

          {/* SELECTED STEP INSTRUCTION */}
          <p style={styles.instructionText}>
            {activeStep?.text ?? "No instruction selected."}
          </p>

          {/* STEP COMPLETION STATUS */}
          {activeStep && (
            <div style={styles.status}>
              {isSigned ? (
                <>
                  <CheckCircle2 size={isKiosk ? 13 : 18} />
                  <span>
                    Signed Off
                    {activeStep.signed_by ? ` by ${activeStep.signed_by}` : ""}
                  </span>
                </>
              ) : pendingInspector ? (
                <>
                  <ShieldAlert size={isKiosk ? 13 : 18} />
                  <span>Pending Inspector Approval</span>
                </>
              ) : (
                <span>Not Yet Signed Off</span>
              )}
            </div>
          )}

          {/* =====================================
              IMPORTANT INFORMATION NOTE
          ===================================== */}
          <div style={styles.note}>
            <div style={styles.noteHeading}>
              <Info size={isKiosk ? 13 : 22} style={{ flexShrink: 0 }} />
              <span>
                {inspectorRequired
                  ? "Inspector Sign-Off Required"
                  : "Important Note"}
              </span>
            </div>

            <p style={styles.noteText}>
              {inspectorRequired
                ? "This step requires supervisor approval before it can be considered complete."
                : "Follow the provided assembly instructions and verify all components before proceeding."}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

// ========================================
// EXPORT
// ========================================

export default InstructionViewer;
