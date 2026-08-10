/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        ink: "var(--ink)",
        panel: "var(--panel)",
        chassis: "var(--chassis)",
        led: "var(--led)",
        danger: "var(--danger)",
      },
      fontFamily: {
        display: ["Press Start 2P", "cursive"],
        body: ["Space Grotesk", "sans-serif"],
        data: ["JetBrains Mono", "monospace"],
      },
      fontSize: {
        display: ["3.5rem", { lineHeight: "1.15" }],
        eyebrow: ["0.75rem", { lineHeight: "1.4", letterSpacing: "0.08em" }],
        h1: ["2.25rem", { lineHeight: "1.2" }],
        h2: ["1.5rem", { lineHeight: "1.3" }],
        body: ["1rem", { lineHeight: "1.5" }],
        small: ["0.875rem", { lineHeight: "1.5" }],
        data: ["1rem", { lineHeight: "1.4" }],
        "data-sm": ["0.8125rem", { lineHeight: "1.4" }],
      },
      borderRadius: {
        sm: "4px",
        md: "10px",
        full: "9999px",
      },
      spacing: {
        4.5: "18px",
      },
      transitionTimingFunction: {
        wipe: "ease-in-out",
      },
      boxShadow: {
        float: "0 8px 24px rgba(0,0,0,.12)",
      },
    },
  },
  plugins: [],
};
