import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b0e14",
        surface: "#11161f",
        border: "#1f2733",
        primary: "#3b82f6",
        muted: "#8b95a5",
      },
    },
  },
  plugins: [],
};

export default config;
