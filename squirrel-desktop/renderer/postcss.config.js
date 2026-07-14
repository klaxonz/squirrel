import path from 'node:path'
import { fileURLToPath } from 'node:url'

const rendererRoot = path.dirname(fileURLToPath(import.meta.url))

export default {
  plugins: {
    tailwindcss: {
      // Vite is often started with cwd=squirrel-desktop; pin the config path.
      config: path.join(rendererRoot, 'tailwind.config.ts'),
    },
    autoprefixer: {},
  },
}
