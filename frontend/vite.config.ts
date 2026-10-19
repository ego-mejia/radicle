import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    // The backend serves the SPA in production; in dev Vite proxies the API to it.
    proxy: {
      '/api': 'http://localhost:8000',
      '/mcp': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
});
