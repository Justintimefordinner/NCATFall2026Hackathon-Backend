// ========================================
// IMPORTS
// ========================================

import React from "react";

import { Routes, Route, Navigate, useLocation } from "react-router-dom";

import App from "./App";
import SupervisorPage from "./pages/SupervisorPage";
import { useMES } from "./context/MESContext";

// ========================================
// ROUTER COMPONENT
// ========================================

function AppRouter() {
  // ========================================
  // STYLING
  // ========================================

  // No styling is required.
  // The router only controls navigation.

  // ========================================
  // STATE & LOGIC
  // ========================================

  // Access supervisor lock state.
  const { isSupervisorLocked } = useMES();

  // Retrieve the current URL location.
  const location = useLocation();

  // Prevent access to the dashboard while locked.
  const dashboardElement = isSupervisorLocked ? (
    <Navigate to="/supervisor" replace />
  ) : (
    <App />
  );

  // Prevent opening the supervisor screen without
  // an active authorization request.
  const supervisorElement = isSupervisorLocked ? (
    <SupervisorPage />
  ) : (
    <Navigate to="/" replace />
  );

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <Routes location={location}>
      {/* =====================================
          NORMAL DASHBOARD ROUTE
      ===================================== */}
      <Route path="/" element={dashboardElement} />

      {/* =====================================
          SUPERVISOR AUTHORIZATION ROUTE
      ===================================== */}
      <Route path="/supervisor" element={supervisorElement} />

      {/* =====================================
          UNKNOWN ROUTES
      ===================================== */}
      <Route
        path="*"
        element={
          <Navigate to={isSupervisorLocked ? "/supervisor" : "/"} replace />
        }
      />
    </Routes>
  );
}

// ========================================
// EXPORT
// ========================================

export default AppRouter;
