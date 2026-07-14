import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backendTarget = process.env.VITE_BACKEND_URL || 'http://localhost:8001'
const rendererRoot = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  root: rendererRoot,
  // Relative base so packaged Electron can load file:// assets.
  base: './',
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return
          }

          if (id.includes('vue') || id.includes('pinia') || id.includes('mitt') || id.includes('@vueuse')) {
            return 'vue-vendor'
          }

          if (id.includes('dashjs')) {
            return 'dash-vendor'
          }

          if (id.includes('shaka-player')) {
            return 'shaka-vendor'
          }

          if (id.includes('hls.js')) {
            return 'hls-vendor'
          }

          if (id.includes('lodash') || id.includes('axios') || id.includes('vue-virtual-scroller')) {
            return 'app-utils-vendor'
          }
        },
      },
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
        ws: true,
      },
      '/static': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
  plugins: [
    vue(),
  ],
})
