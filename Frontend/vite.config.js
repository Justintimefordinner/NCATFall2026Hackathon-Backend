
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// ========================================
// VITE CONFIGURATION
// ========================================

export default defineConfig({
  // ========================================
  // REACT PLUGIN
  // ========================================

  plugins: [react()],

  // ========================================
  // DEVELOPMENT SERVER
  // ========================================

  server: {
    port: 5173,

    // ========================================
    // FLASK BACKEND PROXY
    // ========================================

    proxy: {
      // Flask REST API endpoints
      "/api": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },

      // Flask WebSocket connection
      "/ws": {
        target: "ws://127.0.0.1:5000",
        ws: true,
        changeOrigin: true,
      },

      // Instruction images served by Flask
      "/static": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
});
