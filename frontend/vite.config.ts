import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  // 独立验收库可以使用另一后端端口；日常开发仍默认连接 8009。
  const apiTarget =
    loadEnv(mode, process.cwd(), 'WORKSPACE_').WORKSPACE_API_TARGET || 'http://127.0.0.1:8009'
  return {
    plugins: [vue()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      // 开发时统一从前端地址访问 API 和文档，浏览器无需跨域请求。
      proxy: {
        '/api': apiTarget,
        '/docs': apiTarget,
        '/openapi.json': apiTarget,
      },
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
  }
})
