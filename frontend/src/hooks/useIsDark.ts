import { useEffect, useState } from "react";

/** Returns true when the page is in dark mode (no .light class on <html>). */
export function useIsDark(): boolean {
  const [isDark, setIsDark] = useState(
    () => !document.documentElement.classList.contains("light"),
  );

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setIsDark(!document.documentElement.classList.contains("light"));
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, []);

  return isDark;
}
