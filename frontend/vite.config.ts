import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  optimizeDeps: {
    exclude: ['cesium'],
    include: [
      'autolinker',
      'bitmap-sdf',
      'dompurify',
      'draco3d',
      'earcut',
      'grapheme-splitter',
      'jsep',
      'kdbush',
      'ktx-parse',
      'lerc',
      'mersenne-twister',
      'meshoptimizer',
      'protobufjs',
      'rbush',
      'topojson-client',
      'urijs',
      'nosleep.js',
    ],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          cesium: ['cesium'],
        },
      },
    },
  },
  define: {
    CESIUM_BASE_URL: JSON.stringify('/cesium/'),
  },
})
