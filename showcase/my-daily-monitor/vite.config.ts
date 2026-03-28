import { defineConfig } from 'vite';
import { resolve } from 'path';
import { apiPlugin } from './vite-api-plugin';

export default defineConfig({
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  plugins: [
    apiPlugin(),  // Embeds API routes directly — no separate server needed
  ],
  build: {
    // MapLibre is intentionally loaded as its own lazy chunk and exceeds Vite's default warning threshold.
    chunkSizeWarningLimit: 1200,
  },
  server: {
    port: 5173,
  },
});
