// ========================================
// IMPORTS
// ========================================

import React from "react";
import ReactDOM from "react-dom/client";

import { BrowserRouter } from "react-router-dom";

import AppRouter from "./AppRouter";
import { MESProvider } from "./context/MESContext";

import "./index.css";

// ========================================
// APPLICATION ENTRY POINT
// ========================================

// Mounts the React application inside
// the root element from index.html.

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {/* =====================================
        ROUTER PROVIDER
        Enables navigation between pages.
    ===================================== */}
    <BrowserRouter>
      {/* =====================================
          MES CONTEXT PROVIDER
          Shares state between all routes.
      ===================================== */}
      <MESProvider>
        {/* MAIN APPLICATION ROUTER */}
        <AppRouter />
      </MESProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
