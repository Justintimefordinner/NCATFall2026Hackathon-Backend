import React from "react";
import { ClipboardList, Info } from "lucide-react";

import { useResponsive } from "../hooks/useResponsive";

// Assembly instruction image
import LegoImage from "../assets/Lego.jpg";

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
  // STYLING
  // ========================================

  const styles = {
    // Main instruction viewer container
    container: {
      flex: 1,
      minWidth: 0,
      minHeight: 0,
      backgroundColor: "#101B2B",
      border: "1px solid #34465B",
      borderRadius: isKiosk ? "8px" : "12px",
      padding: isKiosk ? "10px" : "24px",
      display: "flex",
      flexDirection: "column",
      gap: isKiosk ? "8px" : "24px",
      overflow: "hidden",
    },

    // Instruction page title
    title: {
      fontSize: isKiosk ? "16px" : "25px",
      fontWeight: "bold",
      color: "#FFFFFF",
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
      backgroundColor: "#08111F",
      border: "1px solid #009DFF",
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
      color: "#00BFFF",
      fontSize: isKiosk ? "13px" : "21px",
      fontWeight: "bold",
      flexShrink: 0,
    },

    // Instruction list
    instructionsList: {
      display: "flex",
      flexDirection: "column",
      gap: isKiosk ? "5px" : "16px",
      paddingLeft: isKiosk ? "18px" : "24px",
      margin: 0,
      fontSize: isKiosk ? "11px" : "16px",
      lineHeight: isKiosk ? 1.3 : 1.6,
    },

    // Important information box
    note: {
      backgroundColor: "#192B3D",
      border: "1px solid #EAB308",
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
      color: "#FACC15",
      fontSize: isKiosk ? "11px" : "18px",
      fontWeight: "bold",
      marginBottom: isKiosk ? "4px" : "10px",
    },

    // Note description
    noteText: {
      color: "#E2E8F0",
      fontSize: isKiosk ? "10px" : "15px",
      lineHeight: isKiosk ? 1.3 : 1.5,
      margin: 0,
    },
  };

  // ========================================
  // LOGIC
  // ========================================

  // Find the currently selected step.
  const activeStep = page.steps.find((step) => step.id === selectedStep);

  // Display the selected step title when available.
  const displayTitle = activeStep ? activeStep.title : page.title;

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
          <img
            src={LegoImage}
            alt="Assembly instruction reference"
            style={styles.image}
          />
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

          {/* NUMBERED INSTRUCTIONS */}
          <ol style={styles.instructionsList}>
            {page.instructions.map((instruction, index) => (
              <li key={index}>{instruction}</li>
            ))}
          </ol>

          {/* =====================================
              IMPORTANT INFORMATION NOTE
          ===================================== */}
          <div style={styles.note}>
            <div style={styles.noteHeading}>
              <Info size={isKiosk ? 13 : 22} style={{ flexShrink: 0 }} />
              <span>Important Note</span>
            </div>

            <p style={styles.noteText}>
              Follow the provided assembly instructions and verify all
              components before proceeding.
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
