import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const DEV_SERVER_PORT = 5173;

export default defineConfig({
  root: '.',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: DEV_SERVER_PORT,
    strictPort: true
  }
});
