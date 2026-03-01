import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../backend/static",
    emptyOutDir: true,
    assetsDir: "assets",
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
