import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'

// Vitest reuses the same `@` -> ./src alias as vite.config.ts so tests can
// import composables the same way app code does. No happy-dom / jsdom: the
// contract tests under src/composables/*.test.ts are pure state machines and
// need no DOM. When a test eventually needs a DOM, add environment: 'happy-dom'
// here and install happy-dom — that is a separate infrastructure decision.
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    include: ['src/**/*.test.ts'],
  },
})
