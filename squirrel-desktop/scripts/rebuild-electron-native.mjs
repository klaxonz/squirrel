import { createRequire } from 'node:module'
import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const electronVersion = '41.2.0'
const nativePackage = 'better-sqlite3'
const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Resolve packages using Node's module resolution (workspace-aware).
// This works regardless of whether dependencies are hoisted to the root
// node_modules or nested inside the workspace's own node_modules.
const nodeGypBin = require.resolve('node-gyp/bin/node-gyp.js')
const nativePackageDir = path.dirname(require.resolve(`${nativePackage}/package.json`))

const result = spawnSync(
  process.execPath,
  [
    nodeGypBin,
    'rebuild',
    '--release',
    '--runtime=electron',
    `--target=${electronVersion}`,
    '--dist-url=https://electronjs.org/headers',
  ],
  {
    cwd: nativePackageDir,
    stdio: 'inherit',
  },
)

process.exit(result.status ?? 1)
