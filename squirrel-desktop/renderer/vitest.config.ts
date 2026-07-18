import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

const rendererRoot = fileURLToPath(new URL('.', import.meta.url))

// Vitest reuses the same `@` -> ./src alias as vite.config.ts so tests can
// import composables the same way app code does.
//
// Policy: unit tests must exercise shipped functions/state (logic, helpers,
// API client shapes). Do not add source-string "contract" tests that only
// readFile + regex Vue/CSS — they freeze aesthetics and catch nothing real.
// Component behavior tests opt into jsdom per file and run through the same
// Vue SFC transform as the production renderer.
export default defineConfig({
  root: rendererRoot,
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    include: ['src/**/*.test.ts'],
  },
})
