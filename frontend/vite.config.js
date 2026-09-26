import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

import { cloudflare } from "@cloudflare/vite-plugin";

export default defineConfig({
  plugins: [react(), tailwindcss(), cloudflare()],
  server: {
    proxy: {
      '/analyze': 'http://localhost:8000',
      '/competitors': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})