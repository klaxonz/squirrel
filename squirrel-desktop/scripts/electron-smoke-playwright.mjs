import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { _electron as electron } from 'playwright-core'

const desktopRoot = path.dirname(fileURLToPath(import.meta.url)).replace(/[/\\]scripts$/, '')
const fixture = path.join(desktopRoot, 'tests', 'fixtures', 'electron-smoke.html')
const electronBinary = process.env.SQUIRREL_ELECTRON_BINARY || path.join(
  desktopRoot,
  'node_modules',
  'electron',
  process.platform === 'win32' ? 'dist/electron.exe' : 'dist/electron',
)
const userData = fs.mkdtempSync(path.join(os.tmpdir(), 'squirrel-electron-smoke-'))

assert.equal(fs.existsSync(electronBinary), true, `Electron binary not found at ${electronBinary}`)

let app
try {
  app = await electron.launch({
    executablePath: electronBinary,
    args: [path.join(desktopRoot, 'src', 'main.mjs'), `--user-data-dir=${userData}`],
    env: {
      ...process.env,
      DESKTOP_RENDERER_URL: `file://${fixture.replaceAll('\\', '/')}`,
    },
  })
  app.process().stderr?.on('data', (chunk) => process.stderr.write(`[electron] ${chunk}`))
  const page = await app.firstWindow({ timeout: 30_000 })
  await page.waitForFunction(() => document.title === 'Squirrel Electron Smoke', null, { timeout: 30_000 })
  const bridge = await page.evaluate(() => ({
    isDesktop: window.desktopApp?.isDesktop,
    platform: window.desktopApp?.platform,
    electron: window.desktopApp?.versions?.electron,
  }))
  assert.equal(bridge.isDesktop, true)
  assert.equal(typeof bridge.platform, 'string')
  assert.match(bridge.electron, /^41\./)
  assert.equal(app.windows().length, 1)
  const screenshotPath = path.join(desktopRoot, 'test-results', 'electron-smoke.png')
  fs.mkdirSync(path.dirname(screenshotPath), { recursive: true })
  await page.screenshot({ path: screenshotPath })
  console.log(`Electron smoke passed: BrowserWindow=1 preload=true renderer=true screenshot=${screenshotPath}`)
} finally {
  await app?.close()
  fs.rmSync(userData, { recursive: true, force: true })
}
