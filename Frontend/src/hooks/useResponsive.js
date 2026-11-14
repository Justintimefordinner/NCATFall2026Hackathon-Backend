// ========================================
// IMPORTS
// ========================================

import { useEffect, useState } from "react";

// ========================================
// RESPONSIVE SCREEN HOOK
// ========================================

export function useResponsive() {

  // Get the current viewport dimensions.
  const getScreenSize = () => ({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  // ========================================
  // STATE
  // ========================================

  const [screen, setScreen] = useState(getScreenSize);

  // ========================================
  // RESIZE LISTENER
  // ========================================

  useEffect(() => {

    const handleResize = () => {
      setScreen(getScreenSize());
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
    };

  }, []);

  // ========================================
  // SCREEN BREAKPOINTS
  // ========================================

  const isMobile = screen.width < 600;

  const isCompact = screen.width < 1000;

  const isSmallHeight = screen.height <= 600;

  const isPiDisplay =
    screen.width <= 800 && screen.height <= 480;

  // ========================================
  // RETURN
  // ========================================

  return {
    width: screen.width,
    height: screen.height,
    isMobile,
    isCompact,
    isSmallHeight,
    isPiDisplay,
  };
}