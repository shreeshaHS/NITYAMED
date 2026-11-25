/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./App.{js,jsx,ts,tsx}", "./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0D6E6E",
          dark: "#094D4D",
          deep: "#063737",
          soft: "#E6F4F1",
          mint: "#10B981",
          mintSoft: "#DCFCE7",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          canvas: "#F3F6FA",
          subtle: "#F8FAFC",
        },
        ink: {
          DEFAULT: "#0F172A",
          muted: "#475569",
          soft: "#64748B",
        },
      },
      borderRadius: {
        card: "20px",
        pill: "999px",
      },
    },
  },
  plugins: [],
};
