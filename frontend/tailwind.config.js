/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#0B0F14", soft: "#121820", muted: "#8B949E" },
        paper: { DEFAULT: "#F7F7F4", dim: "#ECECE7" },
        surface: { light: "#FFFFFF", dark: "#121820" },
        accent: { DEFAULT: "#3B82F6", dark: "#2563EB", soft: "#DBEAFE" },
        signal: { green: "#22C55E", rose: "#DC5C5C" },
        border: { light: "#E1E4E8", dark: "#202833" },
      },
      fontFamily: {
        display: ["Inter", "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(11,15,20,.04), 0 8px 30px rgba(11,15,20,.04)",
        darkcard: "0 1px 2px rgba(0,0,0,.18), 0 10px 30px rgba(0,0,0,.12)",
      },
      keyframes: {
        "fade-in-up": { "0%": { opacity: "0", transform: "translateY(6px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        "pulse-dot": { "0%, 80%, 100%": { opacity: ".25" }, "40%": { opacity: "1" } },
        "recording-pulse": { "0%, 100%": { transform: "scale(1)", opacity: ".25" }, "50%": { transform: "scale(1.14)", opacity: ".08" } },
      },
      animation: {
        "fade-in-up": "fade-in-up .3s ease-out",
        "pulse-dot": "pulse-dot 1.4s infinite ease-in-out",
        "recording-pulse": "recording-pulse 1.6s infinite ease-in-out",
      },
    },
  },
  plugins: [],
};
