import React from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
} from "lucide-react";

import { useResponsive } from "../hooks/useResponsive";

// ========================================
// COMPONENT
// ========================================

function NavigationBar({
  currentPage,
  totalPages,
  selectedStep,
  onPreviousPage,
  onNextPage,
  onSignOffStep,
  onSignOffPage,
}) {
  // ========================================
  // RESPONSIVE SCREEN DETECTION
  // ========================================

  const { isCompact, isSmallHeight } = useResponsive();

  // Enables the compact Raspberry Pi layout.
  const isKiosk = isCompact && isSmallHeight;

  // ========================================
  // STYLING
  // ========================================

  const styles = {
    // Main navigation container
    container: {
      display: "flex",
      alignItems: "center",
      justifyContent: isKiosk ? "stretch" : "space-between",
      gap: isKiosk ? "6px" : "14px",
      padding: isKiosk ? "5px 8px" : "16px 20px",
      backgroundColor: "#101B2B",
      borderTop: "1px solid #34465B",
      height: isKiosk ? "52px" : "auto",
      minHeight: isKiosk ? "52px" : "auto",
      flexShrink: 0,
      boxSizing: "border-box",
      overflow: "hidden",
    },

    // Standard navigation button
    button: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: isKiosk ? "4px" : "10px",
      flex: isKiosk ? 1 : "initial",
      minWidth: 0,
      minHeight: isKiosk ? "40px" : "58px",
      height: isKiosk ? "40px" : "auto",
      padding: isKiosk ? "4px 6px" : "12px 20px",
      border: "1px solid #40536B",
      borderRadius: isKiosk ? "6px" : "10px",
      backgroundColor: "#1D2D42",
      color: "#FFFFFF",
      fontSize: isKiosk ? "11px" : "15px",
      fontWeight: "600",
      cursor: "pointer",
      lineHeight: 1.1,
      whiteSpace: "nowrap",
      touchAction: "manipulation",
    },

    // Primary action button
    primaryButton: {
      backgroundColor: "#087CE8",
      border: "1px solid #00BFFF",
    },

    // Sign-off button
    signOffButton: {
      backgroundColor: "#123D35",
      border: "1px solid #22C55E",
    },

    // Disabled button appearance
    disabledButton: {
      opacity: 0.4,
      cursor: "not-allowed",
    },

    // Page indicator container
    pageIndicator: {
      display: isKiosk ? "none" : "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: "8px",
      color: "#FFFFFF",
      fontSize: "14px",
    },

    // Page indicator dots
    dots: {
      display: "flex",
      gap: "8px",
    },

    dot: {
      width: "9px",
      height: "9px",
      borderRadius: "50%",
      backgroundColor: "#52637A",
    },

    activeDot: {
      backgroundColor: "#00BFFF",
    },
  };

  // ========================================
  // LOGIC
  // ========================================

  // Determines whether navigation is available.
  const isFirstPage = currentPage === 1;
  const isLastPage = currentPage === totalPages;

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <nav style={styles.container} aria-label="Work instruction navigation">
      {/* =====================================
          PREVIOUS PAGE BUTTON
      ===================================== */}
      <button
        type="button"
        style={{
          ...styles.button,
          ...(isFirstPage ? styles.disabledButton : {}),
        }}
        onClick={onPreviousPage}
        disabled={isFirstPage}
        aria-label="Previous page"
      >
        <ArrowLeft size={isKiosk ? 15 : 21} />
        {isKiosk ? "Previous" : "Previous Page"}
      </button>

      {/* =====================================
          SIGN OFF SELECTED STEP
      ===================================== */}
      <button
        type="button"
        style={{
          ...styles.button,
          ...styles.signOffButton,
          ...(selectedStep == null ? styles.disabledButton : {}),
        }}
        onClick={() => onSignOffStep(selectedStep)}
        disabled={selectedStep == null}
        aria-label={
          selectedStep == null
            ? "No step selected"
            : `Sign off step ${selectedStep}`
        }
      >
        <CheckCircle2 size={isKiosk ? 15 : 22} />

        {isKiosk ? "Sign Step" : `Sign Off Step ${selectedStep ?? ""}`}
      </button>

      {/* =====================================
          SIGN OFF ENTIRE PAGE
      ===================================== */}
      <button
        type="button"
        style={styles.button}
        onClick={onSignOffPage}
        aria-label="Sign off entire page"
      >
        <ClipboardCheck size={isKiosk ? 15 : 21} />
        {isKiosk ? "Sign Page" : "Sign Off Page"}
      </button>

      {/* =====================================
          CURRENT PAGE INDICATOR
          Hidden in kiosk mode because the
          operation bar already shows it.
      ===================================== */}
      {!isKiosk && (
        <div style={styles.pageIndicator}>
          <span>
            Page {currentPage} of {totalPages}
          </span>

          <div style={styles.dots}>
            {Array.from({ length: totalPages }, (_, index) => (
              <span
                key={index}
                style={{
                  ...styles.dot,
                  ...(index + 1 === currentPage ? styles.activeDot : {}),
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* =====================================
          NEXT PAGE BUTTON
      ===================================== */}
      <button
        type="button"
        style={{
          ...styles.button,
          ...styles.primaryButton,
          ...(isLastPage ? styles.disabledButton : {}),
        }}
        onClick={onNextPage}
        disabled={isLastPage}
        aria-label="Next page"
      >
        {isKiosk ? "Next" : "Next Page"}
        <ArrowRight size={isKiosk ? 15 : 21} />
      </button>
    </nav>
  );
}

// ========================================
// EXPORT
// ========================================

export default NavigationBar;
