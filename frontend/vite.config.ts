import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev (npm run dev) the API is proxied so the app can use relative /api/v1 paths,
// exactly like it does behind nginx in Docker. One code path, two environments.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
})
