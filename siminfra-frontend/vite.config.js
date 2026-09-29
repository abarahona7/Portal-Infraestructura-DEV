import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const apiProxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const isLanDevelopment = mode === 'lan'

  return {
    plugins: [react()],
    server: {
      host: isLanDevelopment ? '0.0.0.0' : '127.0.0.1',
      port: 5173,
      strictPort: isLanDevelopment,
      proxy: apiProxy,
    },
    preview: {
      proxy: apiProxy,
    },
  }
})
