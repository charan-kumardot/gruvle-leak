import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Restrained neutral scale (near-black / off-white) + a single accent
        // used sparingly for primary actions and financial-risk emphasis.
        ink: {
          950: "#0b0c0e",
          900: "#131417",
          800: "#1d1f24",
          700: "#2a2d33",
          600: "#43474f",
          500: "#5c6169",
          400: "#7a7f88",
          300: "#a1a5ac",
          200: "#c9ccd1",
          100: "#e6e7ea",
          50: "#f4f4f5",
        },
        paper: {
          DEFAULT: "#faf9f7",
          muted: "#f2f1ee",
        },
        accent: {
          50: "#fdf3f0",
          100: "#fbe3db",
          200: "#f4c2b0",
          300: "#e89a7e",
          400: "#d97350",
          500: "#c1512e", // primary accent — burnt terracotta, used sparingly
          600: "#a33f22",
          700: "#82321c",
          800: "#642619",
          900: "#4a1c14",
        },
        risk: {
          low: "#4a7c59",
          medium: "#b9862f",
          high: "#a33f22",
        },
      },
      fontFamily: {
        sans: [
          "var(--font-sans)",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgb(0 0 0 / 0.04), 0 1px 1px 0 rgb(0 0 0 / 0.03)",
        card: "0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.04)",
      },
      borderRadius: {
        lg: "0.625rem",
        xl: "0.875rem",
      },
    },
  },
  plugins: [],
};

export default config;
