import React from "react";
import { useResponsive } from "../hooks/useResponsive";

// ========================================
// COMPONENT
// ========================================

function OperationInfo({ operation, currentPage }) {
  // ========================================
  // RESPONSIVE SCREEN DETECTION
  // ========================================

  const { isCompact, isSmallHeight } = useResponsive();

  // Enables the compact layout on small landscape screens.
  const isKiosk = isCompact && isSmallHeight;

  // ========================================
  // STYLING
  // ========================================

  const styles = {
    // Main operation information container
    container: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      backgroundColor: "#142235",
      padding: isKiosk ? "5px 10px" : "20px 28px",
      color: "#FFFFFF",
      gap: isKiosk ? "10px" : "24px",
      borderBottom: "1px solid #34465B",
      height: isKiosk ? "48px" : "auto",
      minHeight: isKiosk ? "48px" : "auto",
      flexShrink: 0,
      overflow: "hidden",
    },

    // Individual information section
    section: {
      flex: isKiosk ? "0 1 auto" : 1,
      minWidth: 0,
      borderRight: isKiosk ? "none" : "1px solid #3B536C",
      paddingRight: isKiosk ? "0" : "20px",
    },

    // Information labels
    label: {
      color: "#9CAFC5",
      fontSize: isKiosk ? "10px" : "13px",
      marginBottom: isKiosk ? "2px" : "6px",
      whiteSpace: "nowrap",
    },

    // Information values
    value: {
      fontSize: isKiosk ? "12px" : "19px",
      fontWeight: "600",
      lineHeight: 1.2,
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis",
    },

    // Progress bar background
    progressTrack: {
      width: isKiosk ? "55px" : "180px",
      height: isKiosk ? "5px" : "10px",
      backgroundColor: "#34465B",
      borderRadius: "10px",
      overflow: "hidden",
    },

    // Progress bar fill
    progressFill: {
      height: "100%",
      backgroundColor: "#00AFFF",
      borderRadius: "10px",
      transition: "width 0.3s ease",
    },

    // Progress bar and page number container
    progressContainer: {
      display: "flex",
      alignItems: "center",
      gap: isKiosk ? "5px" : "15px",
      whiteSpace: "nowrap",
    },

    // Page progress text
    progressText: {
      fontSize: isKiosk ? "11px" : "16px",
      whiteSpace: "nowrap",
    },
  };

  // ========================================
  // LOGIC
  // ========================================

  // Calculates total number of instruction pages.
  const totalPages = operation.pages.length;

  // Calculates page navigation progress.
  const progress = (currentPage / totalPages) * 100;

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <div style={styles.container}>
      {/* =====================================
          OPERATION NAME
      ===================================== */}
      <div style={styles.section}>
        <div style={styles.label}>Operation</div>

        <div style={styles.value} title={`${operation.id}: ${operation.name}`}>
          {isKiosk ? operation.id : `${operation.id}: ${operation.name}`}
        </div>
      </div>

      {/* =====================================
          ASSEMBLY NAME
      ===================================== */}
      <div style={styles.section}>
        <div style={styles.label}>Assembly</div>

        <div style={styles.value} title={operation.assembly}>
          {operation.assembly}
        </div>
      </div>

      {/* =====================================
          SERIAL NUMBER
      ===================================== */}
      <div style={styles.section}>
        <div style={styles.label}>{isKiosk ? "Serial" : "Serial Number"}</div>

        <div style={styles.value} title={operation.serialNumber}>
          {operation.serialNumber}
        </div>
      </div>

      {/* =====================================
          PAGE PROGRESS
      ===================================== */}
      <div>
        <div style={styles.label}>{isKiosk ? "Page" : "Page Progress"}</div>

        <div style={styles.progressContainer}>
          {/* PROGRESS BAR */}
          <div style={styles.progressTrack}>
            <div
              style={{
                ...styles.progressFill,
                width: `${progress}%`,
              }}
            />
          </div>

          {/* PAGE NUMBER */}
          <span style={styles.progressText}>
            {isKiosk
              ? `${currentPage}/${totalPages}`
              : `${currentPage} of ${totalPages}`}
          </span>
        </div>
      </div>
    </div>
  );
}

// ========================================
// EXPORT
// ========================================

export default OperationInfo;
