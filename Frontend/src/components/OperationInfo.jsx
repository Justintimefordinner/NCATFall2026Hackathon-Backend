// ========================================
// IMPORTS
// ========================================

import React from "react";

import { useResponsive } from "../hooks/useResponsive";
import { useMES } from "../context/MESContext";

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
  // LIVE BACKEND DATA
  // ========================================

  // Access the authoritative Flask MES state.
  const { mesState } = useMES();

  // Protect against missing data while loading.
  const backendOperation = operation ?? {};

  // Manufacturing operation information.
  const operationName = backendOperation.operation ?? "Loading operation...";

  const workOrder = backendOperation.work_order ?? "—";

  const serialNumber = backendOperation.serial ?? "—";

  const partRevision = backendOperation.part_rev ?? "—";

  // Backend page count.
  const totalPages = backendOperation.page_count ?? 0;

  // Actual signed-step progress from Flask.
  const signedSteps = mesState?.progress?.signed ?? 0;

  const totalSteps = mesState?.progress?.total ?? 0;

  const progress =
    totalSteps > 0 ? Math.min(100, (signedSteps / totalSteps) * 100) : 0;

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
      boxSizing: "border-box",
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

    // Progress bar and step count container
    progressContainer: {
      display: "flex",
      alignItems: "center",
      gap: isKiosk ? "5px" : "15px",
      whiteSpace: "nowrap",
    },

    // Progress text
    progressText: {
      fontSize: isKiosk ? "11px" : "16px",
      whiteSpace: "nowrap",
    },
  };

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

        <div style={styles.value} title={operationName}>
          {operationName}
        </div>
      </div>

      {/* =====================================
          WORK ORDER
      ===================================== */}
      <div style={styles.section}>
        <div style={styles.label}>{isKiosk ? "WO" : "Work Order"}</div>

        <div style={styles.value} title={workOrder}>
          {workOrder}
        </div>
      </div>

      {/* =====================================
          SERIAL NUMBER
      ===================================== */}
      <div style={styles.section}>
        <div style={styles.label}>{isKiosk ? "Serial" : "Serial Number"}</div>

        <div style={styles.value} title={serialNumber}>
          {serialNumber}
        </div>
      </div>

      {/* =====================================
          PART REVISION
      ===================================== */}
      <div style={styles.section}>
        <div style={styles.label}>{isKiosk ? "Rev" : "Part Revision"}</div>

        <div style={styles.value} title={partRevision}>
          {partRevision}
        </div>
      </div>

      {/* =====================================
          STEP PROGRESS
      ===================================== */}
      <div>
        <div style={styles.label}>{isKiosk ? "Progress" : "Step Progress"}</div>

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

          {/* SIGNED STEP COUNT */}
          <span style={styles.progressText}>
            {signedSteps}/{totalSteps}
          </span>
        </div>

        {/* PAGE NUMBER ON LARGER SCREENS */}
        {!isKiosk && (
          <div
            style={{
              ...styles.label,
              marginTop: "6px",
            }}
          >
            Page {currentPage} of {totalPages}
          </div>
        )}
      </div>
    </div>
  );
}

// ========================================
// EXPORT
// ========================================

export default OperationInfo;
