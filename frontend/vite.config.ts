import { cpSync } from 'node:fs';
import { resolve } from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig, type Plugin } from 'vite';

/** Excalidraw's fonts, served by Radicle itself instead of a CDN (Folio 3.5). */
function excalidrawFonts(): Plugin {
  return {
    name: 'radicle-excalidraw-fonts',
    apply: 'build',
    writeBundle(options) {
      const from = new URL(
        './node_modules/@excalidraw/excalidraw/dist/prod/fonts',
        import.meta.url,
      );
      cpSync(from, resolve(options.dir ?? 'dist', 'assets/excalidraw/fonts'), { recursive: true });
    },
  };
}

export default defineConfig({
  plugins: [react(), excalidrawFonts()],
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
      // Public inbox pages are rendered by the backend.
      '/b/': 'http://localhost:8000',
    },
  },
});
