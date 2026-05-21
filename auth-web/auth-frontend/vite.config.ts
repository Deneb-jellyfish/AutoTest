import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173
    // API 直连远程：见 .env 中 VITE_API_BASE
    // 若改回本地 SUT 后端，可设 VITE_API_BASE=/api/zdmj 并恢复 proxy 到 localhost:8081
  }
});
