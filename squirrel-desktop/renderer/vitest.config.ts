import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'

const rendererRoot = fileURLToPath(new URL('.', import.meta.url))

// Vitest reuses the same `@` -> ./src alias as vite.config.ts so tests can
// import composables the same way app code does.
//
// Policy: unit tests must exercise shipped functions/state (logic, helpers,
// API client shapes). Do not add source-string "contract" tests that only
// readFile + regex Vue/CSS — they freeze aesthetics and catch nothing real.
// When a test needs a DOM, add environment: 'happy-dom' (separate decision).
export default defineConfig({
  root: rendererRoot,
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    include: ['src/**/*.test.ts'],
  },
})
