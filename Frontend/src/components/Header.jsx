import React, { useEffect, useState } from "react";
import { Factory, Monitor, UserRound, Clock3 } from "lucide-react";

import { useResponsive } from "../hooks/useResponsive";

// ========================================
// HEADER COMPONENT
// ========================================

function Header({ station, technician }) {
  // ========================================
  // RESPONSIVE SCREEN DETECTION
  // ========================================

  const { isCompact, isSmallHeight } = useResponsive();

  const isKiosk = isCompact && isSmallHeight;

  // ========================================
  // STYLING
  // ========================================

  const styles = {
    header: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      width: "100%",
      height: isKiosk ? "42px" : "82px",
      minHeight: isKiosk ? "42px" : "82px",
      padding: isKiosk ? "0 10px" : "0 28px",
      backgroundColor: "#111827",
      borderBottom: "2px solid #38BDF8",
      gap: isKiosk ? "8px" : "24px",
      overflow: "hidden",
    },

    brand: {
      display: "flex",
      alignItems: "center",
      gap: isKiosk ? "6px" : "14px",
      flexShrink: 0,
    },

    title: {
      margin: 0,
      fontSize: isKiosk ? "16px" : "24px",
      fontWeight: "bold",
      lineHeight: 1.1,
      whiteSpace: "nowrap",
    },

    infoRow: {
      display: "flex",
      alignItems: "center",
      justifyContent: "flex-end",
      gap: isKiosk ? "12px" : "28px",
      minWidth: 0,
    },

    infoItem: {
      display: "flex",
      alignItems: "center",
      gap: "5px",
      whiteSpace: "nowrap",
      fontSize: isKiosk ? "12px" : "15px",
    },

    icon: {
      flexShrink: 0,
      color: "#CBD5E1",
    },

    demoBadge: {
      display: isKiosk ? "none" : "flex",
      alignItems: "center",
      gap: "7px",
      color: "#E2E8F0",
      fontSize: "14px",
    },

    demoDot: {
      width: "8px",
      height: "8px",
      backgroundColor: "#4ADE80",
      borderRadius: "50%",
    },
  };

  // ========================================
  // STATE
  // ========================================

  const [currentTime, setCurrentTime] = useState(() => new Date());

  // ========================================
  // CLOCK LOGIC
  // ========================================

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const formattedTime = currentTime.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });

  // ========================================
  // RETURN / JSX
  // ========================================

  return (
    <header style={styles.header}>
      {/* APPLICATION BRAND */}
      <div style={styles.brand}>
        <Factory size={isKiosk ? 19 : 28} color="#38BDF8" />

        <h1 style={styles.title}>
          {isKiosk ? "Glorp MES" : "Glorp MES Work Instructions"}
        </h1>
      </div>

      {/* HEADER INFORMATION */}
      <div style={styles.infoRow}>
        {/* DEMO MODE INDICATOR */}
        <div style={styles.demoBadge}>
          <span style={styles.demoDot} />
          Demo Mode
        </div>

        {/* STATION NUMBER */}
        <div style={styles.infoItem}>
          {!isKiosk && <Monitor size={17} style={styles.icon} />}
          <span>Station: {station}</span>
        </div>

        {/* TECHNICIAN ID */}
        <div style={styles.infoItem}>
          {!isKiosk && <UserRound size={17} style={styles.icon} />}
          <span>Tech: {technician}</span>
        </div>

        {/* CURRENT TIME */}
        <div style={styles.infoItem}>
          {!isKiosk && <Clock3 size={17} style={styles.icon} />}
          <span>{formattedTime}</span>
        </div>
      </div>
    </header>
  );
}

export default Header;
