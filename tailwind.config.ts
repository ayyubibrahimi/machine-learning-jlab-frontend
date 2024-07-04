module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: "black",
        secondary: "#e1e1da",
        purple: "#1c1919",
        orange: "#f35610",
        // Add red-500 back into the color palette if it's missing
        red: {
          500: '#f56565', // Tailwind's default red-500
        },
        blue: {
          500: '#e1e1da', // Tailwind's default red-500
        },
        // Explicitly set the default text color
        text: {
          DEFAULT: 'black',
        },
      },
      fontFamily: {
        body: ["Roboto", "sans-serif"],
      },
      fontSize: {
        body: "16px",
        heading: "32px",
      },
      lineHeight: {
        body: "24px",
        heading: "40px",
      },
      fontWeight: {
        body: 400,
        heading: 700,
      },
      screens: {
        xxl: "1600px",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
        "broken-camera": "url('/photos/camera-wide.jpg')",
      },
      backgroundColor: {
        black: '#000000',
      },
      width: {
        42: "10rem",
      },
      height: {
        42: "10rem",
      },
    },
  },
  darkMode: "class",
  plugins: [
    require("@tailwindcss/forms"),
  ],
};
