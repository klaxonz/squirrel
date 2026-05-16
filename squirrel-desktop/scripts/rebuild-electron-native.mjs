import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const electronVersion = '41.2.0'
const nativePackage = 'better-sqlite3'
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(__dirname, '..')
const nodeGypBin = path.join(projectRoot, 'node_modules', 'node-gyp', 'bin', 'node-gyp.js')

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
    cwd: path.join(projectRoot, 'node_modules', nativePackage),
    stdio: 'inherit',
  },
)

process.exit(result.status ?? 1)
