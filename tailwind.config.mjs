/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        oz: {
          blue:    '#1a4480', // USWDS-adjacent federal blue
          green:   '#2e8540', // rural/active state
          amber:   '#e5a000', // status / callout
          red:     '#cd2026', // alert / deadline
          neutral: {
            50:  '#f9fafb',
            100: '#f0f2f4',
            200: '#dfe1e6',
            300: '#a9aeb1',
            500: '#71767a',
            700: '#3d4551',
            900: '#1b1b1b',
          },
        },
      },
    },
  },
  plugins: [],
};
