import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

const apiProxy = {
  '/api': {
    target: 'http://127.0.0.1:8005',
    changeOrigin: true,
  },
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const isLanDevelopment = mode === 'lan'
  const { PORTAL_LAN_HOST } = loadEnv(mode, process.cwd(), 'PORTAL_LAN_HOST')

  return {
    plugins: [react()],
    server: {
      host: isLanDevelopment ? (PORTAL_LAN_HOST || '127.0.0.1') : '127.0.0.1',
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
