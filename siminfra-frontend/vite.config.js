import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const apiProxy = {
  '/api': {
    target: 'http://127.0.0.1:8005',
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
      port: 5178,
      strictPort: true,
      proxy: apiProxy,
    },
    preview: {
      port: 5178,
      strictPort: true,
      proxy: apiProxy,
    },
  }
})
