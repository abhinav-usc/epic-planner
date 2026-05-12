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
          base: "#0B0B12",
          panel: "#13131D",
          card: "#1A1A26",
          hover: "#22222F",
        },
        ink: {
          primary: "#E8E8F0",
          secondary: "#9999AE",
          muted: "#5E5E72",
        },
        accent: "#FBBF24",  // amber for highlights
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
