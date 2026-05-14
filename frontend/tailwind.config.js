/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: '#07111f',
        charcoal: '#0d1726',
        electric: '#3b82f6',
        emeraldGlow: '#10b981',
        mutedGold: '#c9a227',
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(59, 130, 246, 0.2), 0 20px 60px rgba(0, 0, 0, 0.45)',
      },
    },
  },
  plugins: [],
};