// ========================================
// IMPORTS
// ========================================

import React, { useState } from "react";
import { ShieldCheck, Delete, LockKeyhole } from "lucide-react";

// Responsive screen detection
import { useResponsive } from "../hooks/useResponsive";

// ========================================
// SUPERVISOR PIN PAD COMPONENT
// ========================================

function SupervisorPinPad({ onAuthorized }) {
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
    // Main PIN pad container
    container: {
      position: "relative",
      width: "100%",
      maxWidth: isKiosk ? "320px" : "420px",
      padding: isKiosk ? "10px 14px" : "30px",
      boxSizing: "border-box",
      backgroundColor: "#101B2B",
      border: "2px solid #00BFFF",
      borderRadius: isKiosk ? "12px" : "22px",
      boxShadow: isKiosk
        ? "0 0 18px rgba(0, 191, 255, 0.25)"
        : "0 0 35px rgba(0, 191, 255, 0.35)",
      color: "#FFFFFF",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: isKiosk ? "6px" : "20px",
      maxHeight: isKiosk ? "100%" : "none",
      overflow: "hidden",
    },

    // Supervisor icon
    icon: {
      color: "#FFFFFF",
      flexShrink: 0,
    },

    // PIN pad title
    title: {
      margin: 0,
      fontSize: isKiosk ? "15px" : "25px",
      fontWeight: "bold",
      textAlign: "center",
      lineHeight: 1.2,
    },

    // Masked PIN display
    pinDisplay: {
      width: "100%",
      height: isKiosk ? "28px" : "58px",
      minHeight: isKiosk ? "28px" : "58px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: isKiosk ? "12px" : "20px",
      backgroundColor: "#1D2D42",
      border: "1px solid #64748B",
      borderRadius: isKiosk ? "6px" : "10px",
      boxSizing: "border-box",
    },

    // Individual PIN indicator
    pinDot: {
      width: isKiosk ? "9px" : "13px",
      height: isKiosk ? "9px" : "13px",
      borderRadius: "50%",
      backgroundColor: "#FFFFFF",
    },

    // Empty PIN indicator
    emptyDot: {
      width: isKiosk ? "9px" : "13px",
      height: isKiosk ? "9px" : "13px",
      borderRadius: "50%",
      border: "1px solid #64748B",
      boxSizing: "border-box",
    },

    // Numeric keypad grid
    keypad: {
      display: "grid",
      gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
      gap: isKiosk ? "5px" : "12px",
      width: "100%",
    },

    // Standard keypad button
    button: {
      height: isKiosk ? "44px" : "62px",
      minWidth: 0,
      borderRadius: isKiosk ? "6px" : "10px",
      backgroundColor: "#24364C",
      border: "1px solid #40536B",
      color: "#FFFFFF",
      fontSize: isKiosk ? "19px" : "26px",
      fontWeight: "bold",
      cursor: "pointer",
      padding: 0,
      touchAction: "manipulation",
    },

    // Enter button
    enterButton: {
      backgroundColor: "#087CE8",
      border: "1px solid #00BFFF",
      fontSize: isKiosk ? "14px" : "19px",
    },

    // Error message
    error: {
      color: "#F87171",
      fontSize: isKiosk ? "11px" : "14px",
      fontWeight: "600",
      textAlign: "center",
      minHeight: isKiosk ? "14px" : "20px",
      lineHeight: 1.2,
    },

    // Helper text
    helper: {
      display: isKiosk ? "none" : "block",
      color: "#94A3B8",
      fontSize: "13px",
      textAlign: "center",
    },
  };

  // ========================================
  // STATE & LOGIC
  // ========================================

  // Demo PIN used only for the hackathon prototype.
  const DEMO_PIN = "1234";

  // Stores the digits entered by the supervisor.
  const [pin, setPin] = useState("");

  // Stores validation error messages.
  const [error, setError] = useState("");

  // Adds a digit, up to four digits.
  const handleDigit = (digit) => {
    setPin((previous) => (previous.length < 4 ? previous + digit : previous));

    setError("");
  };

  // Removes the most recently entered digit.
  const handleDelete = () => {
    setPin((previous) => previous.slice(0, -1));
    setError("");
  };

  // Checks the entered PIN.
  const handleSubmit = () => {
    // Require exactly four digits.
    if (pin.length !== 4) {
      setError("Please enter a four-digit PIN.");
      return;
    }

    // Verify the demo PIN.
    if (pin === DEMO_PIN) {
      setError("");
      setPin("");
      onAuthorized();
      return;
    }

    // Incorrect PIN keeps the screen locked.
    setError("Incorrect supervisor PIN. Try again.");
    setPin("");
  };

  // Keypad layout, including delete and enter.
  const keypad = [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "delete",
    "0",
    "enter",
  ];

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <div style={styles.container}>
      {/* =====================================
          SUPERVISOR SECURITY ICON
      ===================================== */}
      <ShieldCheck size={isKiosk ? 24 : 55} style={styles.icon} />

      {/* =====================================
          PIN PAD TITLE
      ===================================== */}
      <h2 style={styles.title}>Enter Supervisor PIN</h2>

      {/* =====================================
          MASKED PIN DISPLAY
      ===================================== */}
      <div
        style={styles.pinDisplay}
        aria-label={`${pin.length} of 4 PIN digits entered`}
      >
        {Array.from({ length: 4 }, (_, index) => (
          <span
            key={index}
            style={index < pin.length ? styles.pinDot : styles.emptyDot}
          />
        ))}
      </div>

      {/* =====================================
          NUMERIC KEYPAD
      ===================================== */}
      <div style={styles.keypad}>
        {keypad.map((key) => {
          // Determine special keypad buttons.
          const isEnter = key === "enter";
          const isDelete = key === "delete";

          return (
            <button
              key={key}
              type="button"
              style={{
                ...styles.button,
                ...(isEnter ? styles.enterButton : {}),
              }}
              onClick={() => {
                if (isEnter) {
                  handleSubmit();
                } else if (isDelete) {
                  handleDelete();
                } else {
                  handleDigit(key);
                }
              }}
              aria-label={
                isEnter
                  ? "Submit PIN"
                  : isDelete
                    ? "Delete last digit"
                    : `Digit ${key}`
              }
            >
              {isDelete ? (
                <Delete size={isKiosk ? 20 : 25} />
              ) : isEnter ? (
                "Enter"
              ) : (
                key
              )}
            </button>
          );
        })}
      </div>

      {/* =====================================
          VALIDATION ERROR MESSAGE
      ===================================== */}
      <div style={styles.error} role="alert" aria-live="assertive">
        {error}
      </div>

      {/* =====================================
          SUPERVISOR AUTHORIZATION MESSAGE
      ===================================== */}
      <div style={styles.helper}>
        <LockKeyhole
          size={15}
          style={{
            verticalAlign: "middle",
            marginRight: "6px",
          }}
        />
        Supervisor authorization required to continue.
      </div>
    </div>
  );
}

// ========================================
// EXPORT
// ========================================

export default SupervisorPinPad;
