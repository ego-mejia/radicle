import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  build: {
    // CodeMirror alone is ~180 kB gzipped and only loads when editing.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // Heavy editors and markdown load as separate, cacheable chunks.
        manualChunks: {
          react: ['react', 'react-dom', 'styled-components'],
          router: ['@tanstack/react-router', '@tanstack/react-query'],
          editor: [
            '@codemirror/state',
            '@codemirror/view',
            '@codemirror/commands',
            '@codemirror/lang-markdown',
            '@codemirror/autocomplete',
            '@codemirror/language',
          ],
          markdown: ['react-markdown', 'remark-gfm', 'rehype-sanitize'],
        },
      },
    },
  },
  server: {
    // The backend serves the SPA in production; in dev Vite proxies the API to it.
    proxy: {
      '/api': 'http://localhost:8000',
      '/mcp': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
});
