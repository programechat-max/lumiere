import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    allowedHosts: ['.monkeycode-ai.live'],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // AI üretimi (antrenman programı / beslenme planı) 1-2 dk sürebildiği için
        // proxy'nin uzun istekleri kesmemesi için timeout yükseltildi (5 dk).
        timeout: 300000,
        proxyTimeout: 300000,
      },
    },
  },
})