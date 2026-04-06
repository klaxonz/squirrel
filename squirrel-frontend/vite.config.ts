import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backendTarget = process.env.VITE_BACKEND_URL || 'http://localhost:8001'

export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
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

          if (id.includes('hls.js')) {
            return 'hls-vendor'
          }

          if (id.includes('@fortawesome')) {
            return 'fontawesome-vendor'
          }

          if (id.includes('@heroicons')) {
            return 'heroicons-vendor'
          }

          if (id.includes('@iconify')) {
            return 'iconify-vendor'
          }

          if (id.includes('lodash') || id.includes('axios') || id.includes('vue-virtual-scroller')) {
            return 'app-utils-vendor'
          }
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
        ws: true
      },
      '/static': {
        target: backendTarget,
        changeOrigin: true
      }
    }
  },
  plugins: [
    vue(),
  ],
  base: '/',
})
