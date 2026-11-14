// ========================================
// IMPORTS
// ========================================

import React from "react";

import { Routes, Route, Navigate } from "react-router-dom";

import App from "./App";
import SupervisorPage from "./pages/SupervisorPage";

// ========================================
// ROUTER COMPONENT
// ========================================

function AppRouter() {
  // ========================================
  // STYLING
  // ========================================

  // No styling is required here.
  // Each page controls its own layout.

  // ========================================
  // STATE & LOGIC
  // ========================================

  // The technician and supervisor dashboards
  // are independent interfaces.
  //
  // Flask controls authorization for
  // protected supervisor actions.
  //
  // React routing does not authorize users.

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <Routes>
      {/* =====================================
          DEFAULT ROUTE
      ===================================== */}
      <Route path="/" element={<Navigate to="/tech" replace />} />

      {/* =====================================
          TECHNICIAN DASHBOARD
      ===================================== */}
      <Route path="/tech" element={<App />} />

      {/* =====================================
          SUPERVISOR DASHBOARD
      ===================================== */}
      <Route path="/supervisor" element={<SupervisorPage />} />

      {/* =====================================
          UNKNOWN ROUTES
      ===================================== */}
      <Route path="*" element={<Navigate to="/tech" replace />} />
    </Routes>
  );
}

// ========================================
// EXPORT
// ========================================

export default AppRouter;
