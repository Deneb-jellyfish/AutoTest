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
    port: 5173,
    // 经 dev server 代理，避免浏览器直连远程时的 CORS 冲突（nginx 与 Spring 重复 CORS 头）
    proxy: {
      '/api/zdmj': {
        target: 'http://111.229.81.45',
        changeOrigin: true
      }
    }
    // 本地 SUT 后端：将 target 改为 http://localhost:8081
  }
});
