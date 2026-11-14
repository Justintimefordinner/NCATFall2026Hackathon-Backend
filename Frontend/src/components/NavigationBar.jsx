// ========================================
// IMPORTS
// ========================================

import React from "react";

import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
} from "lucide-react";

import { useResponsive } from "../hooks/useResponsive";
import { useMES } from "../context/MESContext";

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
  // LIVE BACKEND STATE
  // ========================================

  const { mesState } = useMES();

  const laborRunning = mesState?.labor?.running === true;
  const qualityAlert = mesState?.quality_alert ?? null;
  const hasQualityAlert = Boolean(qualityAlert);

  const steps = mesState?.page?.steps ?? [];

  const activeStep = steps.find((step) => step.number === selectedStep);

  // ========================================
  // BUTTON AVAILABILITY
  // ========================================

  const isFirstPage = currentPage <= 1;
  const isLastPage = currentPage >= totalPages;

  const disablePrevious = isFirstPage || hasQualityAlert;
  const disableNext = isLastPage || hasQualityAlert;

  const disableSignStep =
    !laborRunning ||
    hasQualityAlert ||
    selectedStep == null ||
    !activeStep ||
    activeStep.signed === true ||
    activeStep.pending_inspector === true;

  const disableSignPage =
    !laborRunning ||
    hasQualityAlert ||
    steps.length === 0 ||
    steps.every((step) => step.signed || step.pending_inspector);

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
      backgroundColor: "#FFFFFF",
      borderTop: "1px solid #E4E4E7",
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
      border: "1px solid #D4D4D8",
      borderRadius: isKiosk ? "6px" : "10px",
      backgroundColor: "#F4F4F5",
      color: "#18181B",
      fontSize: isKiosk ? "11px" : "15px",
      fontWeight: "600",
      cursor: "pointer",
      lineHeight: 1.1,
      whiteSpace: "nowrap",
      touchAction: "manipulation",
    },

    // Primary action button
    primaryButton: {
      backgroundColor: "#2563EB",
      border: "1px solid #1D4ED8",
      color: "#FFFFFF",
    },

    // Sign-off button
    signOffButton: {
      backgroundColor: "#16A34A",
      border: "1px solid #15803D",
      color: "#FFFFFF",
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
      color: "#18181B",
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
      backgroundColor: "#D4D4D8",
    },

    activeDot: {
      backgroundColor: "#2563EB",
    },
  };

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
          ...(disablePrevious ? styles.disabledButton : {}),
        }}
        onClick={onPreviousPage}
        disabled={disablePrevious}
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
          ...(disableSignStep ? styles.disabledButton : {}),
        }}
        onClick={() => onSignOffStep(selectedStep)}
        disabled={disableSignStep}
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
        style={{
          ...styles.button,
          ...(disableSignPage ? styles.disabledButton : {}),
        }}
        onClick={onSignOffPage}
        disabled={disableSignPage}
        aria-label="Sign off entire page"
      >
        <ClipboardCheck size={isKiosk ? 15 : 21} />
        {isKiosk ? "Sign Page" : "Sign Off Page"}
      </button>

      {/* =====================================
          CURRENT PAGE INDICATOR
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
          ...(disableNext ? styles.disabledButton : {}),
        }}
        onClick={onNextPage}
        disabled={disableNext}
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
