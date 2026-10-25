import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// El frontend usa rutas relativas (/api, /mqtt).
const BACKEND = process.env.BACKEND_URL || 'http://localhost:5000'
const MQTT_WS = process.env.MQTT_WS_URL || 'ws://localhost:9001'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
      '/health': { target: BACKEND, changeOrigin: true },
      '/mqtt': { target: MQTT_WS, ws: true, rewrite: () => '/' },
    },
  },
})
