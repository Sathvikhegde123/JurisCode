/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: '#fffaf3',
        charcoal: '#f4ede0',
        electric: '#f97316',
        emeraldGlow: '#16a34a',
        mutedGold: '#f5b454',
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(249, 115, 22, 0.18), 0 24px 60px rgba(15, 23, 42, 0.08)',
      },
    },
  },
  plugins: [],
};