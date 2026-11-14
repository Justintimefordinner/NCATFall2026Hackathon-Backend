import React from "react";
import { Mic, MicOff, AudioLines } from "lucide-react";

import { useResponsive } from "../hooks/useResponsive";

// ========================================
// COMPONENT
// ========================================

function VoiceControl({
  isListening,
  onToggleListening,
  onVoiceCommand,
  feedback,
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
    // Main voice control panel
    container: {
      display: "flex",
      alignItems: "center",
      justifyContent: isKiosk ? "space-between" : "flex-start",
      gap: isKiosk ? "8px" : "20px",
      flex: 1,
      minWidth: 0,
      minHeight: 0,
      height: isKiosk ? "52px" : "auto",
      padding: isKiosk ? "5px 8px" : "16px 20px",
      backgroundColor: "#101B2B",
      border: "1px solid #34465B",
      borderRadius: isKiosk ? "8px" : "12px",
      overflow: "hidden",
    },

    // Voice assistant status container
    status: {
      display: isKiosk ? "flex" : "none",
      flexDirection: "column",
      justifyContent: "center",
      minWidth: 0,
      gap: "2px",
    },

    // Voice assistant label
    statusTitle: {
      fontSize: "12px",
      fontWeight: "bold",
      color: "#FFFFFF",
      whiteSpace: "nowrap",
    },

    // Listening status
    statusText: {
      fontSize: "10px",
      color: isListening ? "#4ADE80" : "#94A3B8",
    },

    // Microphone toggle button
    microphoneButton: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: isKiosk ? "6px" : "12px",
      minHeight: isKiosk ? "40px" : "auto",
      padding: isKiosk ? "7px 10px" : "14px 20px",
      borderRadius: isKiosk ? "7px" : "10px",
      border: isListening ? "1px solid #00BFFF" : "1px solid #40536B",
      backgroundColor: isListening ? "#0755A3" : "#1D2D42",
      color: "#FFFFFF",
      fontWeight: "bold",
      fontSize: isKiosk ? "11px" : "16px",
      cursor: "pointer",
      whiteSpace: "nowrap",
      flexShrink: 0,
    },

    // Voice command controls
    commands: {
      display: isKiosk ? "none" : "flex",
      alignItems: "center",
      gap: "10px",
      flexWrap: "wrap",
    },

    // Individual simulated voice command
    commandButton: {
      padding: "10px 14px",
      backgroundColor: "#1D2D42",
      border: "1px solid #40536B",
      borderRadius: "24px",
      color: "#FFFFFF",
      fontSize: "13px",
      cursor: isListening ? "pointer" : "not-allowed",
      opacity: isListening ? 1 : 0.4,
    },

    // Feedback message
    feedback: {
      display: isKiosk ? "none" : "block",
      color: "#9CAFC5",
      fontSize: "13px",
      minWidth: "130px",
    },
  };

  // ========================================
  // LOGIC
  // ========================================

  // Example commands used to test our MES.
  const commands = [
    { label: "Next page", value: "next page" },
    { label: "Previous page", value: "previous page" },
    { label: "Start labor", value: "start labor" },
    { label: "Stop labor", value: "stop labor" },
    { label: "Sign off step", value: "sign off step" },
    { label: "Sign off page", value: "sign off page" },
  ];

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <section style={styles.container}>
      {/* =====================================
          COMPACT VOICE STATUS
          Visible only on small screens.
      ===================================== */}
      {isKiosk && (
        <div style={styles.status}>
          <span style={styles.statusTitle}>Voice Assistant</span>

          <span style={styles.statusText}>
            {isListening ? "Listening" : "Not Listening"}
          </span>
        </div>
      )}

      {/* =====================================
          MICROPHONE LISTENING TOGGLE
      ===================================== */}
      <button
        type="button"
        style={styles.microphoneButton}
        onClick={onToggleListening}
        aria-pressed={isListening}
      >
        {isListening ? (
          <Mic size={isKiosk ? 17 : 24} />
        ) : (
          <MicOff size={isKiosk ? 17 : 24} />
        )}

        <span>
          {isKiosk
            ? isListening
              ? "Stop"
              : "Start"
            : isListening
              ? "Listening"
              : "Start Listening"}
        </span>

        {isListening && !isKiosk && <AudioLines size={24} color="#38BDF8" />}
      </button>

      {/* =====================================
          SIMULATED VOICE COMMANDS
          Desktop only.
      ===================================== */}
      <div style={styles.commands}>
        {commands.map((command) => (
          <button
            key={command.value}
            type="button"
            style={styles.commandButton}
            onClick={() => onVoiceCommand(command.value)}
            disabled={!isListening}
          >
            {command.label}
          </button>
        ))}
      </div>

      {/* =====================================
          COMMAND FEEDBACK
          Desktop only.
      ===================================== */}
      <div style={styles.feedback} role="status" aria-live="polite">
        {feedback}
      </div>
    </section>
  );
}

// ========================================
// EXPORT
// ========================================

export default VoiceControl;
