import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@docs': fileURLToPath(new URL('../docs', import.meta.url))
    }
  },

  // Configuración del servidor de desarrollo
  server: {
    port: 5173,
    strictPort: true,
    // Proxy para el backend FastAPI
    proxy: {
      '/api': {
        target: 'http://localhost:8008',
        changeOrigin: true,
        secure: false
      }
    }
  },

  // Build optimizations for local Tauri app
  build: {
    target: 'esnext',
    minify: 'esbuild',
    // No sourcemaps in production bundle (local app, not debuggable by users)
    sourcemap: false,
    // No gzip reporting — irrelevant for local filesystem (no HTTP content-encoding)
    reportCompressedSize: false,
    // Chunks >500KB are normal for a local app — suppress warning
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'ui-vendor': ['primevue'],
          'vis-network': ['vis-network/standalone'],
          'vis-timeline': ['vis-timeline/standalone', 'vis-data/standalone'],
          'chart': ['chart.js'],
        }
      }
    }
  }
})
