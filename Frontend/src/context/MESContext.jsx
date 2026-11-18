import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

// ========================================
// MES CONTEXT
// ========================================

const MESContext = createContext(null);

// ========================================
// MES PROVIDER
// ========================================

export function MESProvider({ children }) {
  // ========================================
  // BACKEND CONNECTION STATE
  // ========================================

  const [mesState, setMesState] = useState(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);

  // ========================================
  // LOCAL UI STATE
  // ========================================

  // Selected instruction step is local UI state.
  const [selectedStep, setSelectedStep] = useState(null);

  // Feedback from backend commands.
  const [feedback, setFeedback] = useState("Connecting to MES backend...");

  // Compatibility with existing supervisor controls.
  const [isSupervisorLocked, setIsSupervisorLocked] = useState(false);

  // Smooth timer display between backend updates.
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // ========================================
  // REFS
  // ========================================

  // Keeps track of the active WebSocket.
  const socketRef = useRef(null);

  // ========================================
  // INITIAL BACKEND STATE FETCH
  // ========================================

  useEffect(() => {
    let cancelled = false;

    const loadInitialState = async () => {
      try {
        const response = await fetch("/api/state");

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (!cancelled) {
          setMesState(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setFeedback(`Unable to connect to MES: ${err.message}`);
        }
      }
    };

    loadInitialState();

    return () => {
      cancelled = true;
    };
  }, []);

  // ========================================
  // WEBSOCKET CONNECTION
  // ========================================

  useEffect(() => {
    let active = true;
    let reconnectTimeout = null;

    const connectWebSocket = () => {
      if (!active) return;

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";

      const socket = new WebSocket(
        `${protocol}//${window.location.host}/ws/ui`,
      );

      socketRef.current = socket;

      // ------------------------------------
      // CONNECTION OPENED
      // ------------------------------------

      socket.onopen = () => {
        if (!active) return;

        setConnected(true);
        setError(null);
      };

      // ------------------------------------
      // INCOMING BACKEND MESSAGES
      // ------------------------------------

      socket.onmessage = (event) => {
        if (!active) return;

        try {
          const message = JSON.parse(event.data);

          if (message.type === "state") {
            setMesState(message);
            setError(null);
          }

          if (message.type === "announce") {
            setFeedback(message.message);
          }
        } catch (err) {
          console.error("Invalid MES WebSocket message:", err);
        }
      };

      // ------------------------------------
      // CONNECTION CLOSED
      // ------------------------------------

      socket.onclose = () => {
        if (!active) return;

        setConnected(false);

        reconnectTimeout = setTimeout(() => {
          connectWebSocket();
        }, 2000);
      };

      // ------------------------------------
      // CONNECTION ERROR
      // ------------------------------------

      socket.onerror = () => {
        if (!active) return;

        setConnected(false);
      };
    };

    connectWebSocket();

    return () => {
      active = false;

      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }

      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  // ========================================
  // BACKEND OPERATION DATA
  // ========================================

  const backendOperation = mesState?.operation ?? {};
  const backendPage = mesState?.page ?? null;

  const currentPage = backendPage?.number ?? 1;
  const totalPages = backendOperation.page_count ?? 0;

  // ========================================
  // ACTIVE PAGE NORMALIZATION
  // ========================================

  // The backend uses "number" and "signed".
  // Some existing frontend components use
  // "id" and "completed".
  //
  // Preserve both formats for compatibility.

  const activePage = backendPage
    ? {
        ...backendPage,

        steps: (backendPage.steps ?? []).map((step) => ({
          ...step,
          id: step.number,
          completed: step.signed,
        })),
      }
    : {
        number: 1,
        title: "",
        steps: [],
      };

  // ========================================
  // OPERATION NORMALIZATION
  // ========================================

  const operation = {
    ...backendOperation,
    station: backendOperation.station ?? "A-01",
    technician: backendOperation.operator ?? "Unknown",
    pages: [activePage],
  };

  // ========================================
  // COMPLETED STEPS
  // ========================================

  const completedSteps = activePage.steps
    .filter((step) => step.signed)
    .map((step) => step.id);

  // ========================================
  // LABOR AND VOICE STATE
  // ========================================

  const isLaborRunning = mesState?.labor?.running ?? false;

  const isListening = mesState?.listening ?? false;

  // ========================================
  // STEP SELECTION SYNCHRONIZATION
  // ========================================

  // Select the first instruction step when
  // Flask changes to a different page.

  useEffect(() => {
    setSelectedStep(backendPage?.steps?.[0]?.number ?? null);
  }, [currentPage, Boolean(backendPage)]);

  // ========================================
  // LABOR TIMER SYNCHRONIZATION
  // ========================================

  const backendSeconds = mesState?.labor?.seconds ?? 0;

  // Update the displayed timer whenever
  // Flask provides an authoritative value.
  useEffect(() => {
    setElapsedSeconds(backendSeconds);
  }, [backendSeconds]);

  // Increment locally for smooth display.
  useEffect(() => {
    if (!isLaborRunning) return;

    const interval = setInterval(() => {
      setElapsedSeconds((seconds) => seconds + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isLaborRunning]);

  // ========================================
  // SHARED HTTP POST HELPER
  // ========================================

  const postJSON = async (endpoint, body = {}) => {
    try {
      const response = await fetch(endpoint, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify(body),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.message ?? `HTTP ${response.status}`);
      }

      // Some endpoints return a complete
      // state snapshot; others return lights.
      if (result.state) {
        setMesState(result.state);
      }

      if (result.message) {
        setFeedback(result.message);
      }

      setError(null);

      return result;
    } catch (err) {
      setError(err.message);
      setFeedback(`Connection error: ${err.message}`);

      return {
        ok: false,
        message: err.message,
      };
    }
  };

  // ========================================
  // COMMAND API
  // ========================================

  // Sends a text command through Flask's
  // existing parser and state machine.

  // Keep pending supervisor approval authoritative in Flask.
  // Reviewing a signed step is allowed, but continuing is not.
  const blockForPendingApproval = () => {
    const pending = mesState?.pending_inspector?.[0];
    if (!pending) return null;

    if (Number(pending.page) === Number(currentPage)) {
      setSelectedStep(pending.step);
    }

    const message = `Supervisor approval required — Page ${pending.page}, Step ${pending.step}.`;
    setFeedback(message);
    return { ok: false, message };
  };

  // Supervisor sign-off from a screen.
  // Typed / simulated commands carry no voice, so Flask can't tell who
  // said them and answers "Supervisor PIN required". Route them to the
  // PIN prompt instead. Real spoken "supervisor confirm" comes from the
  // voice process and opens the spoken challenge (supervisor_challenge).
  const isSupervisorConfirm = (normalized) =>
    /^(supervisor (confirm|sign off|signoff)|inspector (sign off|signoff))\b/.test(
      normalized,
    );

  const handleSupervisorSignoff = (pin, page, step) => {
    return postJSON("/api/inspector/signoff", { pin, page, step });
  };

  const sendCommand = (text) => {
    const normalized = String(text).trim().toLowerCase();

    if (isSupervisorConfirm(normalized)) {
      const pending = mesState?.pending_inspector?.[0];
      if (pending) {
        const message = `Supervisor: enter PIN to approve Page ${pending.page}, Step ${pending.step}.`;
        setFeedback(message);
        return Promise.resolve({ ok: false, message, needsPin: true });
      }
    }

    const isContinuation =
      /^(next page|previous page|page done|sign off page|sign off step)$/.test(
        normalized,
      ) || /^step\s+\d+\s+done$/.test(normalized);

    if (isContinuation) {
      const blocked = blockForPendingApproval();
      if (blocked) return Promise.resolve(blocked);
    }

    return postJSON("/api/command", {
      text,
      source: "debug",
    });
  };

  // ========================================
  // POWER ACTIVATION
  // ========================================

  // Simulates the physical Power button.
  //
  // The backend changes:
  // IDLE -> ARRIVED
  //
  // React does not change the mode locally.

  const handlePowerOn = async () => {
    const result = await postJSON("/api/panel/button", {
      id: "power",
    });

    // Panel endpoints return LED states,
    // not a full MES snapshot.
    //
    // Fetch the authoritative state so
    // the dashboard can appear immediately.

    if (result.ok) {
      try {
        const response = await fetch("/api/state");

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const state = await response.json();

        setMesState(state);
        setError(null);
      } catch (err) {
        console.error("Failed to refresh power state:", err);
      }
    }

    return result;
  };

  // ========================================
  // LABOR COMMANDS
  // ========================================

  const handleStartLabor = () => {
    return sendCommand("start labor");
  };

  const handleStopLabor = () => {
    return sendCommand("stop labor");
  };

  // ========================================
  // PAGE NAVIGATION
  // ========================================

  const handlePreviousPage = async () => {
    if (mesState?.mode === "arrived") {
      const result = await sendCommand("open instructions");
      if (!result?.ok) return result;
    }

    return sendCommand("previous page");
  };

  const handleNextPage = async () => {
    if (mesState?.mode === "arrived") {
      const result = await sendCommand("open instructions");
      if (!result?.ok) return result;
    }

    return sendCommand("next page");
  };

  // Only adjacent navigation is supported
  // by the current backend commands.
  const navigateToPage = async (pageNumber) => {
    if (pageNumber === currentPage) {
      return {
        ok: true,
        message: "Already on requested page",
      };
    }

    if (pageNumber === currentPage + 1) {
      return handleNextPage();
    }

    if (pageNumber === currentPage - 1) {
      return handlePreviousPage();
    }

    return {
      ok: false,
      message: "Only adjacent page navigation is supported.",
    };
  };

  // ========================================
  // STEP SELECTION
  // ========================================

  // Selecting a step only changes the
  // instruction currently being displayed.

  const handleSelectStep = (stepId) => {
    setSelectedStep(stepId);
  };

  // ========================================
  // STEP SIGN-OFF
  // ========================================

  const handleSignOffStep = (stepId = selectedStep) => {
    const step = activePage.steps.find((item) => item.number === stepId);

    if (!step) {
      return Promise.resolve({
        ok: false,
        message: "No step selected",
      });
    }

    return sendCommand(`step ${step.number} done`);
  };

  // ========================================
  // PAGE SIGN-OFF
  // ========================================

  const handleSignOffPage = () => {
    return sendCommand("page done");
  };

  // ========================================
  // VOICE LISTENING TOGGLE
  // ========================================

  // Uses the same backend endpoint as
  // the ESP32 listening button.

  const handleToggleListening = () => {
    return postJSON("/api/panel/button", {
      id: "listen_toggle",
    });
  };

  // ========================================
  // SIMULATED VOICE COMMANDS
  // ========================================

  // Desktop testing uses the debug source.
  // Real microphone recognition will use
  // the backend's voice-command pipeline.

  const handleVoiceCommand = (command) => {
    const normalized = String(command).trim().toLowerCase();

    if (normalized === "sign off step") {
      return handleSignOffStep();
    }

    if (normalized === "sign off page") {
      return handleSignOffPage();
    }

    return sendCommand(normalized);
  };

  // ========================================
  // SUPERVISOR UI COMPATIBILITY
  // ========================================

  const requestSupervisor = () => {
    setIsSupervisorLocked(true);
  };

  const authorizeSupervisor = () => {
    setIsSupervisorLocked(false);
  };

  // ========================================
  // CONTEXT VALUE
  // ========================================

  const contextValue = {
    // Backend state
    mesState,
    connected,
    error,

    // Operation data
    operation,
    currentPage,
    selectedStep,
    completedSteps,
    totalPages,
    activePage,

    // Labor and voice
    isLaborRunning,
    elapsedSeconds,
    isListening,
    feedback,

    // Supervisor UI
    isSupervisorLocked,

    // Generic backend command
    sendCommand,

    // Power activation
    handlePowerOn,

    // Labor
    handleStartLabor,
    handleStopLabor,

    // Navigation
    navigateToPage,
    handlePreviousPage,
    handleNextPage,

    // Sign-offs
    handleSelectStep,
    handleSignOffStep,
    handleSignOffPage,

    // Voice
    handleToggleListening,
    handleVoiceCommand,

    // Supervisor compatibility
    requestSupervisor,
    authorizeSupervisor,

    // Supervisor sign-off (PIN) and spoken challenge
    handleSupervisorSignoff,
    supervisorChallenge: mesState?.supervisor_challenge ?? null,
  };

  // ========================================
  // PROVIDER RETURN
  // ========================================

  return (
    <MESContext.Provider value={contextValue}>{children}</MESContext.Provider>
  );
}

// ========================================
// CUSTOM HOOK
// ========================================

export function useMES() {
  const context = useContext(MESContext);

  if (!context) {
    throw new Error("useMES must be used inside MESProvider.");
  }

  return context;
}
