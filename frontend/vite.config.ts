import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': process.env.VITE_API_PROXY_TARGET || 'http://localhost:8080',
      '/ws': {
        target: process.env.VITE_WS_PROXY_TARGET || 'ws://localhost:8080',
        ws: true,
      },
      '/health': process.env.VITE_API_PROXY_TARGET || 'http://localhost:8080',
    },
  },
})
