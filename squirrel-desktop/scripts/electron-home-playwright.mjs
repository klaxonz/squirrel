import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { _electron as electron } from 'playwright-core'

const desktopRoot = path.dirname(fileURLToPath(import.meta.url)).replace(/[/\\]scripts$/, '')
const electronBinary = process.env.SQUIRREL_ELECTRON_BINARY || path.join(desktopRoot, 'node_modules', 'electron', process.platform === 'win32' ? 'dist/electron.exe' : 'dist/electron')
const userData = fs.mkdtempSync(path.join(os.tmpdir(), 'squirrel-electron-home-'))
const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm'
let rendererProcess
let app

const waitForRenderer = async () => {
  const deadline = Date.now() + 60_000
  while (Date.now() < deadline) {
    try { const response = await fetch('http://127.0.0.1:5174/') ; if (response.ok) return } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error('Vite renderer did not become ready on http://127.0.0.1:5174/')
}

try {
  assert.equal(fs.existsSync(electronBinary), true, `Electron binary not found at ${electronBinary}`)
  fs.writeFileSync(path.join(userData, 'server-config.json'), JSON.stringify({ serverUrl: 'http://127.0.0.1:8001' }))
  rendererProcess = spawn(npmCommand, ['run', 'dev:renderer', '--', '--host', '127.0.0.1'], { cwd: desktopRoot, stdio: 'ignore', windowsHide: true, shell: process.platform === 'win32' })
  await waitForRenderer()
  app = await electron.launch({ executablePath: electronBinary, args: [path.join(desktopRoot, 'src', 'main.mjs'), `--user-data-dir=${userData}`], env: { ...process.env, DESKTOP_RENDERER_URL: 'http://127.0.0.1:5174/' } })
  const context = app.context()
  await context.route('http://127.0.0.1:8001/**', async (route) => {
    const requestPath = new URL(route.request().url()).pathname
    let data = {}
    if (requestPath === '/api/users/me') data = { id: 1, username: 'playwright', nickname: 'Playwright' }
    if (requestPath === '/api/video/list') data = { items: [], total: 0, page: 1, page_size: 24 }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data }) })
  })
  const page = await app.firstWindow({ timeout: 30_000 })
  await page.waitForFunction(() => window.location.hash === '#/home', null, { timeout: 30_000 })
  await page.getByRole('heading', { name: '最新入库' }).waitFor({ state: 'visible', timeout: 30_000 })
  assert.equal(await page.locator('#home-inbox-title').count(), 1)
  assert.equal(await page.locator('body').evaluate((body) => body.innerText.includes('快捷入口')), true)
  console.log('Electron Home smoke passed: real Vite renderer reached #/home with deterministic API mocks')
} finally {
  await app?.close()
  rendererProcess?.kill()
  fs.rmSync(userData, { recursive: true, force: true })
}
