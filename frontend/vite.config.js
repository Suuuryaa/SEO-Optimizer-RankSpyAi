import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

import { cloudflare } from "@cloudflare/vite-plugin";

export default defineConfig({
  plugins: [react(), tailwindcss(), cloudflare()],
  environments: {
    client: {
      build: {
        rollupOptions: {
          // Two pages: the app (/) and the FAQ (/faq → faq.html, its own title and description)
          input: { main: 'index.html', faq: 'faq.html' },
        },
      },
    },
  },
  server: {
    proxy: {
      '/analyze': 'http://localhost:8000',
      '/competitors': 'http://localhost:8000',
      '/jobs': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})