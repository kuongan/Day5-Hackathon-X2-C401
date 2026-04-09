/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b1220",
        mist: "#e8eef8",
        ocean: "#0f4c81",
        tide: "#2e7bcf",
        glow: "#b8e2ff",
        ember: "#ffb454"
      },
      fontFamily: {
        display: ["'Plus Jakarta Sans'", "ui-sans-serif", "system-ui"],
        body: ["'Source Sans 3'", "ui-sans-serif", "system-ui"]
      },
      boxShadow: {
        panel: "0 24px 60px -24px rgba(15, 76, 129, 0.4)",
        float: "0 18px 40px -22px rgba(0, 0, 0, 0.35)"
      }
    }
  },
  plugins: []
};
