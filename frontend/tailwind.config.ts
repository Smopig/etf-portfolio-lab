import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Background layers (02 §1.1)
        bg: {
          base: "var(--bg-base)",
          surface: "var(--bg-surface)",
          raised: "var(--bg-surface-raised)",
          inset: "var(--bg-inset)",
        },
        // Borders
        border: {
          subtle: "var(--border-subtle)",
          strong: "var(--border-strong)",
          DEFAULT: "var(--border-subtle)",
        },
        // Text (02 §1.2)
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        // Accent (02 §1.3)
        accent: {
          primary: "var(--accent-primary)",
          "primary-hover": "var(--accent-primary-hover)",
          secondary: "var(--accent-secondary)",
        },
        // Semantic status (02 §1.4)
        status: {
          success: "var(--status-success)",
          warning: "var(--status-warning)",
          error: "var(--status-error)",
          info: "var(--status-info)",
          neutral: "var(--status-neutral)",
        },
        // Chart series palette (02 §1.5)
        series: {
          1: "var(--series-1)",
          2: "var(--series-2)",
          3: "var(--series-3)",
          4: "var(--series-4)",
          5: "var(--series-5)",
          6: "var(--series-6)",
          7: "var(--series-7)",
          8: "var(--series-8)",
          9: "var(--series-9)",
          10: "var(--series-10)",
          unclassified: "var(--series-unclassified)",
        },
        // Legacy aliases (keep older usages working)
        background: "var(--bg-base)",
        surface: "var(--bg-surface)",
        primary: "var(--accent-primary)",
        muted: "var(--text-muted)",
      },
      fontFamily: {
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      fontSize: {
        display: ["28px", { lineHeight: "36px", fontWeight: "600" }],
        h2: ["20px", { lineHeight: "28px", fontWeight: "600" }],
        h3: ["16px", { lineHeight: "24px", fontWeight: "600" }],
        body: ["14px", { lineHeight: "20px", fontWeight: "400" }],
        small: ["12px", { lineHeight: "16px", fontWeight: "400" }],
        "mono-num": ["13px", { lineHeight: "18px", fontWeight: "400" }],
      },
      spacing: {
        "space-1": "4px",
        "space-2": "8px",
        "space-3": "12px",
        "space-4": "16px",
        "space-6": "24px",
        "space-8": "32px",
      },
      borderRadius: {
        sm: "4px",
        md: "8px",
        lg: "12px",
      },
    },
  },
  plugins: [],
};

export default config;
