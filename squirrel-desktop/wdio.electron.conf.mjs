import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const desktopRoot = path.dirname(fileURLToPath(import.meta.url))
const electronRoot = path.join(desktopRoot, 'node_modules', 'electron')
const userData = path.join(os.tmpdir(), `squirrel-electron-smoke-${process.pid}`)
const fixture = path.join(desktopRoot, 'tests', 'fixtures', 'electron-smoke.html')

const driverCandidates = [
  process.env.SQUIRREL_CHROMEDRIVER_PATH,
  path.join(desktopRoot, 'node_modules', 'electron-chromedriver', 'chromedriver.exe'),
  path.join(desktopRoot, '..', '.cache', 'electron-chromedriver', '41.2.0', 'chromedriver.exe'),
].filter(Boolean)
const chromedriver = driverCandidates.find((candidate) => fs.existsSync(candidate))
const electronBinary = process.env.SQUIRREL_ELECTRON_BINARY || path.join(
  electronRoot,
  process.platform === 'win32' ? 'dist/electron.exe' : 'dist/electron',
)

if (!chromedriver) {
  throw new Error([
    'Electron smoke requires a local ChromeDriver matching Electron 41.2.0.',
    'The electron-chromedriver postinstall download was unavailable (ECONNRESET).',
    'Install/provide it locally and set SQUIRREL_CHROMEDRIVER_PATH, or place it at .cache/electron-chromedriver/41.2.0/chromedriver.exe.',
  ].join(' '))
}
if (!fs.existsSync(electronBinary)) {
  throw new Error(`Electron binary not found at ${electronBinary}. Restore the Electron 41.2.0 package cache or set SQUIRREL_ELECTRON_BINARY.`)
}

process.env.DESKTOP_RENDERER_URL = `file://${fixture.replaceAll('\\', '/')}`

export const config = {
  runner: 'local',
  specs: ['./tests/electron-smoke/**/*.spec.mjs'],
  maxInstances: 1,
  logLevel: 'warn',
  framework: 'mocha',
  reporters: ['spec'],
  services: ['electron'],
  capabilities: [{
    browserName: 'electron',
    browserVersion: '41.2.0',
    'wdio:chromedriverOptions': {
      binary: chromedriver,
    },
    'wdio:electronServiceOptions': {
      appEntryPoint: path.join(desktopRoot, 'src', 'main.mjs'),
      appArgs: [`--user-data-dir=${userData}`],
    },
  }],
  mochaOpts: {
    timeout: 60_000,
  },
  onComplete: async () => {
    const { rm } = await import('node:fs/promises')
    await rm(userData, { recursive: true, force: true })
  },
}
