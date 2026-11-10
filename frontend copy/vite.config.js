import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Attempt to load the Base44 Vite plugin if it's available. If not,
// fall back to a plain React + Vite setup so the app can run standalone.
export default async () => {
  return defineConfig({
    plugins: [react()],
    server: {
      proxy: {
        '/api': 'http://127.0.0.1:8000',
      },
    },
    // Support the `@/` import alias used throughout the codebase.
    resolve: {
      alias: [
        { find: '@', replacement: '/src' }
      ]
    }
  });
};
