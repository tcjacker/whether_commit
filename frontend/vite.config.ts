import { defineConfig, type UserConfig } from 'vite'
import react from '@vitejs/plugin-react'

interface FrontendConfig extends UserConfig {
  test: {
    environment: string
    setupFiles: string[]
  }
}

const config: FrontendConfig = {
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8088',
      '/health': 'http://localhost:8088',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
}

export default defineConfig(config)
