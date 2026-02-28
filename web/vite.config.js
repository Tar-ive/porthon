import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/chat': 'http://localhost:8888',
      '/ws': {
        target: 'http://localhost:8888',
        ws: true,
      },
      '/health': 'http://localhost:8888',
    },
  },
})
