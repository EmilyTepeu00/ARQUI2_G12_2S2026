import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// El frontend usa rutas relativas (/api, /mqtt). En produccion las reparte
// Caddy; en desarrollo las reparte este proxy, para que el codigo sea el mismo
// en los dos casos y no haya que tocar variables de entorno.
//
// BACKEND_URL / MQTT_WS_URL solo hacen falta si el backend o el broker no estan
// en localhost (por ejemplo, corriendo el backend en Windows para leer el COM).
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
      // Mosquitto sirve su listener WebSocket en la raiz, asi que se recorta
      // el prefijo /mqtt igual que hace Caddy.
      '/mqtt': { target: MQTT_WS, ws: true, rewrite: () => '/' },
    },
  },
})
