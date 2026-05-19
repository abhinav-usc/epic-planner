/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Land theme colors (also returned by the backend)
        land: {
          celestial: "#4F46E5",
          nintendo: "#DC2626",
          ministry: "#7C3AED",
          berk: "#059669",
          dark: "#9333EA",
        },
        bg: {
          base: "var(--bg-base)",
          panel: "var(--bg-panel)",
          card: "var(--bg-card)",
          hover: "var(--bg-hover)",
        },
        ink: {
          primary: "var(--ink-primary)",
          secondary: "var(--ink-secondary)",
          muted: "var(--ink-muted)",
        },
        accent: "#FBBF24",  // amber for highlights
        status: {
          ok:   "var(--status-ok)",
          warn: "var(--status-warn)",
          bad:  "var(--status-bad)",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ['"Space Grotesk"', "Inter", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 24px rgba(251, 191, 36, 0.15)",
      },
    },
  },
  plugins: [],
};
