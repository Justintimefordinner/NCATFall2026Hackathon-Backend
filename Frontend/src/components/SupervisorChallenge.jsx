import { useEffect, useState } from "react";

// ========================================
// SPOKEN SUPERVISOR CHALLENGE
// ========================================

// Shows the phrase the supervisor must say after "supervisor confirm"
// (or "clear alert"), with a countdown. Flask sends seconds_left with
// each snapshot; we count down locally from there and hide the prompt
// when it reaches zero (Flask doesn't push a new state on expiry).

// Keyed on expires_at so each new challenge remounts with a fresh countdown.
function SupervisorChallenge({ challenge, compact = false }) {
  if (!challenge) return null;
  return (
    <Countdown key={challenge.expires_at} challenge={challenge} compact={compact} />
  );
}

function Countdown({ challenge, compact }) {
  const [secondsLeft, setSecondsLeft] = useState(challenge.seconds_left ?? 0);

  useEffect(() => {
    if (secondsLeft <= 0) return undefined;
    const timeout = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(timeout);
  }, [secondsLeft]);

  if (secondsLeft <= 0) return null;

  const label =
    challenge.action === "clear_alert" ? "to clear the alert" : "to approve";

  return (
    <div
      role="status"
      aria-live="assertive"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "10px",
        padding: compact ? "3px 6px" : "8px 12px",
        borderRadius: "7px",
        backgroundColor: "#1E3A8A",
        color: "#FFFFFF",
        fontSize: compact ? "12px" : "15px",
        fontWeight: "bold",
        textAlign: "center",
      }}
    >
      <span>
        🎙 Supervisor, say{" "}
        <span style={{ fontSize: compact ? "14px" : "20px", letterSpacing: "1px" }}>
          “{challenge.phrase}”
        </span>{" "}
        {label}
      </span>
      <span
        style={{
          minWidth: "34px",
          padding: "2px 6px",
          borderRadius: "999px",
          backgroundColor: secondsLeft <= 5 ? "#DC2626" : "#3B82F6",
        }}
        aria-label={`${secondsLeft} seconds left`}
      >
        {secondsLeft}s
      </span>
    </div>
  );
}

export default SupervisorChallenge;
