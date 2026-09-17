"use client";

import { useEffect, useState, useRef } from "react";
import { usePathname, useSearchParams } from "next/navigation";

/**
 * BACII-Themed Navigation Progress Bar
 * 
 * Provides instantaneous visual feedback when navigating between routes.
 * Styled in BACII amber/gold with warm chalk-glow to match the academic parchment aesthetic.
 */
export default function NavigationProgressBar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Complete progress on route change
  useEffect(() => {
    if (!visible) return;
    setProgress(100);
    const hideTimer = setTimeout(() => {
      setVisible(false);
      setProgress(0);
    }, 280);

    return () => clearTimeout(hideTimer);
  }, [pathname, searchParams]);

  const startProgress = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setVisible(true);
    setProgress(15);

    timerRef.current = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          if (timerRef.current) clearInterval(timerRef.current);
          return 90;
        }
        // Smooth logarithmic creep toward 90%
        const diff = 90 - prev;
        return prev + Math.max(1, Math.round(diff * 0.15));
      });
    }, 120);
  };

  useEffect(() => {
    // Intercept clicks on links to start progress immediately
    const handleClick = (e: MouseEvent) => {
      const target = (e.target as HTMLElement)?.closest("a");
      if (!target) return;

      const href = target.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("javascript:") || href.startsWith("mailto:") || href.startsWith("tel:")) {
        return;
      }

      if (target.getAttribute("target") === "_blank" || target.getAttribute("download") !== null) {
        return;
      }

      // Check if external
      try {
        const url = new URL(href, window.location.href);
        if (url.origin !== window.location.origin) return;
        // Same page with same search query (no-op)
        if (url.pathname === window.location.pathname && url.search === window.location.search && !url.hash) {
          return;
        }
      } catch {
        return;
      }

      // Don't trigger if modifier keys are pressed (cmd/ctrl click opens new tab)
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

      startProgress();
    };

    const handleCustomStart = () => startProgress();

    document.addEventListener("click", handleClick, { capture: true });
    window.addEventListener("bacii-nav-start", handleCustomStart);

    return () => {
      document.removeEventListener("click", handleClick, { capture: true });
      window.removeEventListener("bacii-nav-start", handleCustomStart);
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  if (!visible) return null;

  return (
    <div
      aria-hidden="true"
      className="fixed top-0 left-0 right-0 z-[9999] pointer-events-none transition-opacity duration-300"
      style={{ opacity: visible ? 1 : 0 }}
    >
      <div
        className="h-[3px] transition-all ease-out duration-200"
        style={{
          width: `${progress}%`,
          background: "linear-gradient(90deg, #b45309 0%, #d97706 40%, #f59e0b 70%, #fcd34d 100%)",
          boxShadow: "0 0 10px rgba(245, 158, 11, 0.75), 0 0 5px rgba(217, 119, 6, 0.9)",
        }}
      />
    </div>
  );
}
