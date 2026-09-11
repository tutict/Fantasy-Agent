import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Vitest reuses the app's Vite config so imports, TSX and path aliases behave
 * the same as in `vite build`. Only the test-specific bits are added here.
 */
export default defineConfig({
  base: "/frontend/",
  plugins: [react()],
  root: "apps/frontend",
  build: {
    outDir: "dist",
    emptyOutDir: true
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:7860",
      "/workbench": "http://127.0.0.1:7860"
    }
  },
  test: {
    // `apps/frontend` is the root, so this resolves to apps/frontend/src.
    include: ["src/**/*.test.{ts,tsx}"],
    environment: "jsdom",
    restoreMocks: true
  }
});
