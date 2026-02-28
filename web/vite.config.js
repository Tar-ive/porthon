import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 8888,
    proxy: {
      '/query': 'http://localhost:9621',
      '/chat': 'http://localhost:9621',
      '/health': 'http://localhost:9621',
    },
  },
})
