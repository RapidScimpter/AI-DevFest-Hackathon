import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Production build is written into the FastAPI app, which serves it. In development, /api is proxied.
export default defineConfig({
  plugins: [react()],
  build: { outDir: '../app/static', emptyOutDir: true },
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
