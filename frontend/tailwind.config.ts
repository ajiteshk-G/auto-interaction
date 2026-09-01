import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        mahindra: {
          red: "#D6001C",
          dark: "#0F1115",
          charcoal: "#1A1D24",
          card: "#161920",
          border: "#2A2E39",
          gold: "#D4AF37",
          electric: "#00E5FF",
          electricBg: "#0B2230"
        }
      },
      boxShadow: {
        xs: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
      },
      scale: {
        '102': '1.02',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 15px rgba(214, 0, 28, 0.4)' },
          '100%': { boxShadow: '0 0 35px rgba(214, 0, 28, 0.85)' },
        }
      }
    },
  },
  plugins: [],
};
export default config;
