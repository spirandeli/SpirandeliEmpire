import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

// O SPA é acessado via Nginx (porta WEB_PORT). O HMR precisa apontar para essa porta.
const hmrPort = Number(process.env.VITE_HMR_CLIENT_PORT || 8080)

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    hmr: { clientPort: hmrPort },
    watch: { usePolling: true, interval: 300 },
  },
})
