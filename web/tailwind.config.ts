import type { Config } from "tailwindcss";

/**
 * FlightCast design tokens. Source of truth for colors used in
 * Tailwind utility classes. Plain CSS variables live in globals.css.
 */
const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          base: "#08111F",      // Page background
          card: "#101A2B",      // Card surface
          alt: "#0F172A",       // Alternate (sidebar interior, chart card alt)
          deep: "#050A14",      // Code blocks + input wells
          sidebar: "#0B1220",
        },
        slate: {
          50: "#F8FAFC",
          100: "#F1F5F9",
          200: "#E2E8F0",
          300: "#CBD5E1",
          400: "#93A4BA",       // muted text per spec
          500: "#64748B",
          600: "#475569",
          700: "#334155",
          800: "#1E293B",
          900: "#0F172A",
        },
        accent: {
          blue: "#60A5FA",
          blueDeep: "#3B82F6",
          violet: "#A78BFA",
          violetSoft: "#C4B5FD",
          violetDeep: "#7C3AED",
          green: "#34D399",
          amber: "#FBBF24",
          red: "#F87171",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          '"SF Pro Display"',
          '"SF Pro Text"',
          '"Segoe UI"',
          "sans-serif",
        ],
        mono: [
          '"SF Mono"',
          '"JetBrains Mono"',
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      letterSpacing: {
        eyebrow: "0.21em",
        statlabel: "0.13em",
      },
      boxShadow: {
        card: "0 16px 40px rgba(0,0,0,0.22)",
        tooltip: "0 12px 32px rgba(0,0,0,0.35)",
      },
      keyframes: {
        "tour-pop-in": {
          from: { opacity: "0", transform: "scale(0.95) translateY(10px)" },
          to: { opacity: "1", transform: "scale(1) translateY(0)" },
        },
      },
      animation: {
        "tour-pop-in": "tour-pop-in 0.3s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
