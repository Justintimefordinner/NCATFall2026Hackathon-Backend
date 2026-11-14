import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

// ========================================
// CONTEXT CREATION
// ========================================

const MESContext = createContext(null);

// ========================================
// CONTEXT PROVIDER
// ========================================

export function MESProvider({ children }) {
  // ========================================
  // STATE
  // ========================================

  // Flask is the authoritative source of MES data.
  const [mesState, setMesState] = useState(null);

  // Tracks the WebSocket connection.
  const [connected, setConnected] = useState(false);

  // Stores connection errors.
  const [error, setError] = useState(null);

  // Selected step is local UI-only state.
  const [selectedStep, setSelectedStep] = useState(null);

  // Latest command or backend response.
  const [feedback, setFeedback] = useState("Connecting to MES backend...");

  // Preserved for compatibility with older components.
  // This does not authorize supervisor actions.
  const [isSupervisorLocked, setIsSupervisorLocked] = useState(false);

  // Display-only timer value.
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // ========================================
  // INITIAL BACKEND STATE
  // ========================================

  useEffect(() => {
    let cancelled = false;

    async function loadInitialState() {
      try {
        const response = await fetch("/api/state");

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (cancelled) return;

        setMesState(data);
        setError(null);
      } catch (err) {
        if (cancelled) return;

        console.error("MES initial state error:", err);
        setError(err.message);
      }
    }

    loadInitialState();

    return () => {
      cancelled = true;
    };
  }, []);

  // ========================================
  // WEBSOCKET CONNECTION
  // ========================================

  useEffect(() => {
    let socket = null;
    let reconnectTimeout = null;
    let stopped = false;

    function connect() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";

      const url = `${protocol}//${window.location.host}/ws/ui`;

      socket = new WebSocket(url);

      socket.onopen = () => {
        if (stopped) return;

        setConnected(true);
        setError(null);
      };

      socket.onmessage = (event) => {
        if (stopped) return;

        try {
          const message = JSON.parse(event.data);

          if (message.type === "state") {
            setMesState(message);
          }

          if (message.type === "announce") {
            setFeedback(message.message);
          }
        } catch (err) {
          console.error("MES WebSocket message error:", err);
        }
      };

      socket.onerror = () => {
        if (stopped) return;

        setError("MES WebSocket connection failed.");
      };

      socket.onclose = () => {
        if (stopped) return;

        setConnected(false);

        reconnectTimeout = setTimeout(connect, 2000);
      };
    }

    connect();

    return () => {
      stopped = true;

      clearTimeout(reconnectTimeout);

      if (socket) {
        socket.close();
      }
    };
  }, []);

  // ========================================
  // DERIVED BACKEND DATA
  // ========================================

  const backendOperation = mesState?.operation ?? {};

  const backendPage = mesState?.page ?? null;

  const currentPage = backendPage?.number ?? 1;

  const totalPages = backendOperation.page_count ?? 0;

  // Adapt backend step fields for existing components.
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

  // Adapt backend operation fields for existing components.
  const operation = {
    ...backendOperation,
    station: backendOperation.station ?? "A-01",
    technician: backendOperation.operator ?? "Unknown",
    pages: [activePage],
  };

  const completedSteps = activePage.steps
    .filter((step) => step.signed)
    .map((step) => step.id);

  const isLaborRunning = mesState?.labor?.running ?? false;

  const isListening = mesState?.listening ?? false;

  // ========================================
  // STEP SELECTION
  // ========================================

  // Select the first step when the backend changes pages.
  useEffect(() => {
    const firstStep = backendPage?.steps?.[0]?.number ?? null;

    setSelectedStep(firstStep);
  }, [currentPage, Boolean(backendPage)]);

  // ========================================
  // LABOR TIMER SYNCHRONIZATION
  // ========================================

  // Synchronize whenever Flask publishes new state.
  const backendSeconds = mesState?.labor?.seconds ?? 0;

  useEffect(() => {
    setElapsedSeconds(backendSeconds);
  }, [backendSeconds]);

  // Advance the displayed timer while labor is running.
  useEffect(() => {
    if (!isLaborRunning) return;

    const interval = setInterval(() => {
      setElapsedSeconds((seconds) => seconds + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isLaborRunning]);

  // ========================================
  // BACKEND COMMAND HELPER
  // ========================================

  async function postJSON(endpoint, body) {
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

      if (result.state) {
        setMesState(result.state);
      }

      if (result.message) {
        setFeedback(result.message);
      }

      // Flask can return HTTP 200 with ok: false.
      return result;
    } catch (err) {
      console.error("MES command error:", err);

      setError(err.message);
      setFeedback(`Connection error: ${err.message}`);

      return {
        ok: false,
        message: err.message,
      };
    }
  }

  // ========================================
  // TECHNICIAN COMMANDS
  // ========================================

  function sendCommand(text) {
    return postJSON("/api/command", {
      text,
      source: "debug",
    });
  }

  function handleStartLabor() {
    return sendCommand("start labor");
  }

  function handleStopLabor() {
    return sendCommand("stop labor");
  }

  function handlePreviousPage() {
    return sendCommand("previous page");
  }

  function handleNextPage() {
    return sendCommand("next page");
  }

  // Only adjacent navigation is supported.
  function navigateToPage(pageNumber) {
    if (pageNumber === currentPage + 1) {
      return handleNextPage();
    }

    if (pageNumber === currentPage - 1) {
      return handlePreviousPage();
    }

    setFeedback("Direct page navigation is not supported by the backend.");

    return Promise.resolve({
      ok: false,
      message: "Direct page navigation is not supported.",
    });
  }

  // ========================================
  // STEP MANAGEMENT
  // ========================================

  function handleSelectStep(stepId) {
    setSelectedStep(stepId);
  }

  function handleSignOffStep(stepId = selectedStep) {
    const step = activePage.steps.find((item) => item.id === stepId);

    if (!step) {
      setFeedback("Select a valid step first.");

      return Promise.resolve({
        ok: false,
        message: "Step not found.",
      });
    }

    return sendCommand(`step ${step.number} done`);
  }

  function handleSignOffPage() {
    // Backend decides which steps are eligible.
    // Page sign-off does NOT auto-advance.
    return sendCommand("page done");
  }

  // ========================================
  // LISTENING CONTROL
  // ========================================

  function handleToggleListening() {
    // Development-only simulation of ESP32 button.
    return postJSON("/api/panel/button", {
      id: "listen_toggle",
    });
  }

  // ========================================
  // SIMULATED VOICE COMMANDS
  // ========================================

  function handleVoiceCommand(command) {
    const normalized = command.toLowerCase().trim();

    if (normalized === "sign off step") {
      return handleSignOffStep();
    }

    if (normalized === "sign off page") {
      return handleSignOffPage();
    }

    return sendCommand(normalized);
  }

  // ========================================
  // LEGACY SUPERVISOR OVERLAY STATE
  // ========================================

  // These functions do not grant backend permissions.
  function requestSupervisor() {
    setIsSupervisorLocked(true);
  }

  function authorizeSupervisor() {
    setIsSupervisorLocked(false);
  }

  // ========================================
  // CONTEXT VALUES
  // ========================================

  const contextValue = {
    // Live backend information
    mesState,
    connected,
    error,

    // Adapted dashboard information
    operation,
    currentPage,
    selectedStep,
    completedSteps,
    totalPages,
    activePage,
    isLaborRunning,
    elapsedSeconds,
    isListening,
    feedback,
    isSupervisorLocked,

    // Technician actions
    sendCommand,
    handleStartLabor,
    handleStopLabor,
    navigateToPage,
    handlePreviousPage,
    handleNextPage,
    handleSelectStep,
    handleSignOffStep,
    handleSignOffPage,
    handleToggleListening,
    handleVoiceCommand,

    // Legacy compatibility
    requestSupervisor,
    authorizeSupervisor,
  };

  // ========================================
  // RETURN / JSX
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
