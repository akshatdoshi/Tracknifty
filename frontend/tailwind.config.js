/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        buy: "#16a34a",
        sell: "#dc2626",
        hold: "#d97706",
      },
    },
  },
  plugins: [],
};
