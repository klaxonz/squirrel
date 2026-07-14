/**
 * Desktop visual snapshots for Squirrel (Electron).
 *
 * Default driver: real Electron via Playwright `_electron` (CDP into the app).
 * That keeps `window.desktopApp`, preload bridge, IPC, title bar, and media
 * headers — plain Chromium cannot exercise those paths.
 *
 * Optional: VISUAL_DRIVER=browser for pure-layout probes only (no desktop bridge).
 *
 * Usage (from squirrel-desktop/):
 *   node renderer/scripts/visual-snapshot.mjs              # write actuals
 *   node renderer/scripts/visual-snapshot.mjs --update      # promote actuals → baseline
 *   node renderer/scripts/visual-snapshot.mjs --check       # compare actuals to baseline
 *
 * Auth (first match wins):
 *   VISUAL_TOKEN=…jwt…
 *   VISUAL_EMAIL + VISUAL_PASSWORD
 *   repo-root .env.dev → DEV_AUTH_EMAIL / DEV_AUTH_PASSWORD
 *
 * Env:
 *   VISUAL_DRIVER=electron|browser     default electron
 *   VISUAL_BASE_URL=…                  Vite renderer (auto-probes 5173–5176)
 *   DESKTOP_RENDERER_URL=…             passed into Electron (defaults to BASE_URL)
 *   VISUAL_OUT_DIR / VISUAL_BASELINE_DIR / VISUAL_THRESHOLD / VISUAL_MAX_DIFF_PIXELS
 *   VISUAL_CHROMIUM_PATH=…             browser driver only
 *   SQUIRREL_VISUAL_USER_DATA=…        isolated Electron userData (default tmp)
 */

import { createRequire } from 'node:module'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { PNG } from './visual-png-lite.mjs'

const require = createRequire(import.meta.url)
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const rendererDir = path.resolve(__dirname, '..')
const desktopDir = path.resolve(rendererDir, '..')
const repoRoot = path.resolve(desktopDir, '..')

const args = new Set(process.argv.slice(2))
const modeUpdate = args.has('--update')
const modeCheck = args.has('--check')
const forceBrowser = args.has('--browser')

async function pathExists(p) {
  try {
    await fs.access(p)
    return true
  } catch {
    return false
  }
}

/**
 * Load KEY=VALUE pairs from a dotenv-style file into process.env
 * without overwriting keys already set in the environment.
 */
async function loadEnvFile(filePath) {
  if (!(await pathExists(filePath))) return false
  const text = await fs.readFile(filePath, 'utf8')
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    const eq = line.indexOf('=')
    if (eq <= 0) continue
    const key = line.slice(0, eq).trim()
    let value = line.slice(eq + 1).trim()
    if (
      (value.startsWith('"') && value.endsWith('"'))
      || (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1)
    }
    if (process.env[key] === undefined) {
      process.env[key] = value
    }
  }
  return true
}

await loadEnvFile(path.join(repoRoot, '.env.dev'))
await loadEnvFile(path.join(repoRoot, '.env.visual.local'))

if (!process.env.VISUAL_EMAIL && process.env.DEV_AUTH_EMAIL) {
  process.env.VISUAL_EMAIL = process.env.DEV_AUTH_EMAIL
}
if (process.env.VISUAL_PASSWORD === undefined && process.env.DEV_AUTH_PASSWORD !== undefined) {
  process.env.VISUAL_PASSWORD = process.env.DEV_AUTH_PASSWORD
}

const DRIVER = forceBrowser
  || String(process.env.VISUAL_DRIVER || 'electron').trim().toLowerCase() === 'browser'
  ? 'browser'
  : 'electron'

const OUT_DIR = path.resolve(
  process.env.VISUAL_OUT_DIR || path.join(repoRoot, 'runtime-logs', 'visual-actual'),
)
const BASELINE_DIR = path.resolve(
  process.env.VISUAL_BASELINE_DIR || path.join(rendererDir, 'visual-baselines'),
)
const THRESHOLD = Number(process.env.VISUAL_THRESHOLD || '0.01')
const MAX_DIFF_PIXELS = Number(process.env.VISUAL_MAX_DIFF_PIXELS || '12000')
const VIEWPORT = { width: 1600, height: 1000 }

/** @type {string} */
let BASE_URL = String(process.env.VISUAL_BASE_URL || '').replace(/\/$/, '')

/** @type {{ id: string, route: string, theme: 'dark' | 'light', sidebarOpen: boolean, optional?: boolean, maskMain?: boolean }[]} */
const SCENARIOS = [
  { id: 'shell-home-dark', route: '/home', theme: 'dark', sidebarOpen: true, maskMain: true },
  { id: 'shell-home-dark-collapsed', route: '/home', theme: 'dark', sidebarOpen: false, maskMain: true },
  { id: 'shell-home-light', route: '/home', theme: 'light', sidebarOpen: true, maskMain: true },
  { id: 'videos-dark', route: '/videos/all', theme: 'dark', sidebarOpen: true, optional: true },
  { id: 'rss-dark', route: '/rss', theme: 'dark', sidebarOpen: true, optional: true },
  { id: 'music-dark', route: '/music', theme: 'dark', sidebarOpen: true, optional: true },
  // /settings redirects to a child tab — capture the default appearance tab.
  { id: 'settings-dark', route: '/settings/appearance', theme: 'dark', sidebarOpen: true, optional: true },
]

function looksLikeSquirrelShell(contentType, body) {
  if (!contentType.includes('text/html')) return false
  return (
    body.includes('/src/app/main.ts')
    || body.includes('src="/src/app/main')
    || body.includes("src='/src/app/main")
    || body.includes('squirrel-icon.png')
    || (body.includes('/@vite/client') && body.includes('归仓'))
  )
}

async function probeSquirrelBaseUrl() {
  if (process.env.VISUAL_BASE_URL) {
    return String(process.env.VISUAL_BASE_URL).replace(/\/$/, '')
  }

  const host = process.env.FRONTEND_DEV_HOST || '127.0.0.1'
  const bindHost = host === 'localhost' ? '127.0.0.1' : host
  const preferredPort = process.env.FRONTEND_DEV_PORT || '5173'
  const ports = [...new Set([preferredPort, '5173', '5174', '5175', '5176'])]
  const rejected = []

  for (const port of ports) {
    const url = `http://${bindHost}:${port}`
    try {
      const res = await fetch(url, { cache: 'no-store' })
      if (!res.ok) {
        rejected.push(`${url} HTTP ${res.status}`)
        continue
      }
      const contentType = String(res.headers.get('content-type') || '')
      const body = await res.text()
      if (looksLikeSquirrelShell(contentType, body)) {
        return url
      }
      rejected.push(`${url} not squirrel (title/body mismatch)`)
    } catch (err) {
      rejected.push(`${url} ${err.message || err}`)
    }
  }

  throw new Error(
    'Could not find Squirrel Vite renderer. Start `npm run dev:renderer` (or `npm run dev`) in squirrel-desktop, '
    + `or set VISUAL_BASE_URL. Probed:\n- ${rejected.join('\n- ')}`,
  )
}

function hashUrl(route) {
  const pathPart = route.startsWith('/') ? route : `/${route}`
  return `${BASE_URL}/#${pathPart}`
}

function appRouteFromUrl(url) {
  try {
    const u = new URL(url)
    const hash = u.hash || ''
    if (hash.startsWith('#/')) return hash.slice(1)
    if (hash.startsWith('#')) return hash.slice(1) || '/'
    return u.pathname || '/'
  } catch {
    return ''
  }
}

function isLoginRoute(url) {
  const route = appRouteFromUrl(url)
  return route === '/login' || route.startsWith('/login?')
}

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true })
}

async function loadPlaywright() {
  const candidates = [
    path.join(desktopDir, 'node_modules', 'playwright-core'),
    path.join(repoRoot, 'node_modules', 'playwright-core'),
    'playwright-core',
  ]
  let lastErr
  for (const c of candidates) {
    try {
      return require(c)
    } catch (err) {
      lastErr = err
    }
  }
  throw new Error(`Cannot load playwright-core: ${lastErr?.message || lastErr}`)
}

async function resolveElectronExecutable() {
  if (process.env.VISUAL_ELECTRON_PATH) {
    return process.env.VISUAL_ELECTRON_PATH
  }
  try {
    // `require('electron')` returns the binary path string in Node (not in Electron).
    return require('electron')
  } catch {
    const win = path.join(repoRoot, 'node_modules', 'electron', 'dist', 'electron.exe')
    if (await pathExists(win)) return win
    throw new Error('Cannot resolve electron binary. Install desktop deps or set VISUAL_ELECTRON_PATH.')
  }
}

async function resolveChromiumPath() {
  if (process.env.VISUAL_CHROMIUM_PATH) {
    return process.env.VISUAL_CHROMIUM_PATH
  }
  const home = process.env.USERPROFILE || process.env.HOME || ''
  const roots = [
    path.join(home, 'AppData', 'Local', 'ms-playwright'),
    path.join(home, '.cache', 'ms-playwright'),
  ]
  for (const root of roots) {
    if (!(await pathExists(root))) continue
    const entries = await fs.readdir(root, { withFileTypes: true })
    const chromiumDirs = entries
      .filter((e) => e.isDirectory() && e.name.startsWith('chromium-') && !e.name.includes('headless'))
      .map((e) => e.name)
      .sort()
      .reverse()
    for (const dir of chromiumDirs) {
      const candidates = [
        path.join(root, dir, 'chrome-win64', 'chrome.exe'),
        path.join(root, dir, 'chrome-win', 'chrome.exe'),
        path.join(root, dir, 'chrome-linux', 'chrome'),
        path.join(root, dir, 'chrome-mac', 'Chromium.app', 'Contents', 'MacOS', 'Chromium'),
      ]
      for (const c of candidates) {
        if (await pathExists(c)) return c
      }
    }
  }
  return null
}

async function waitForRenderer(baseUrl, timeoutMs = 30000) {
  const started = Date.now()
  let lastError = null
  while (Date.now() - started < timeoutMs) {
    try {
      const res = await fetch(baseUrl, { cache: 'no-store' })
      if (res.ok) {
        const contentType = String(res.headers.get('content-type') || '')
        const body = await res.text()
        if (looksLikeSquirrelShell(contentType, body)) {
          return
        }
        lastError = new Error('Port up but body is not squirrel Vite shell')
      } else {
        lastError = new Error(`HTTP ${res.status}`)
      }
    } catch (err) {
      lastError = err
    }
    await new Promise((r) => setTimeout(r, 400))
  }
  throw new Error(
    `Renderer not ready at ${baseUrl} within ${timeoutMs}ms. `
    + `Start with: npm run dev:renderer. Last: ${lastError?.message || lastError}`,
  )
}

/**
 * Wait until SPA chrome is actually usable — not just DOMContentLoaded.
 * Hash navigations often fire networkidle before Vue finishes painting the shell.
 */
async function waitForAppShell(page, { expectAuthShell = false } = {}) {
  if (expectAuthShell) {
    await page.locator('#email, input[type="email"]').first().waitFor({
      state: 'visible',
      timeout: 30000,
    })
    return
  }

  // Authenticated desktop shell: title bar (desktop) + workspace + sidebar tree.
  await page.waitForFunction(() => {
    const layout = document.querySelector('.app-layout')
    const workspace = document.querySelector('.app-layout__workspace, main.app-layout__workspace, main')
    if (!layout || !workspace) return false
    const wr = workspace.getBoundingClientRect()
    return wr.width > 200 && wr.height > 200
  }, { timeout: 45000 })

  // Prefer real nav items over generic sidebar class (more stable signal).
  const nav = page.locator('.app-layout__sidebar, aside, nav').first()
  await nav.waitFor({ state: 'attached', timeout: 15000 }).catch(() => {})
}

async function waitForHashRoute(page, expectedRoute, timeoutMs = 30000) {
  const expected = expectedRoute.startsWith('/') ? expectedRoute : `/${expectedRoute}`
  await page.waitForFunction(
    (want) => {
      const hash = window.location.hash || ''
      const route = hash.startsWith('#') ? hash.slice(1) : hash
      if (!route) return false
      // /videos/all matches want /videos or /videos/all
      return route === want || route.startsWith(`${want}/`) || route.startsWith(`${want}?`)
    },
    expected,
    { timeout: timeoutMs },
  )
}

/**
 * SPA APIs keep sockets open; classic networkidle is flaky.
 * Wait until in-flight document/XHR/fetch quiet for quietMs, with a hard cap.
 */
async function waitForNetworkQuiet(page, { quietMs = 800, timeoutMs = 25000 } = {}) {
  const started = Date.now()
  let lastBusy = Date.now()

  const touch = (req) => {
    try {
      const type = typeof req.resourceType === 'function' ? req.resourceType() : ''
      if (!type || type === 'xhr' || type === 'fetch' || type === 'document') {
        lastBusy = Date.now()
      }
    } catch {
      lastBusy = Date.now()
    }
  }

  page.on('request', touch)
  page.on('requestfinished', touch)
  page.on('requestfailed', touch)

  try {
    while (Date.now() - started < timeoutMs) {
      if (Date.now() - lastBusy >= quietMs) {
        return
      }
      await page.waitForTimeout(150)
    }
    console.warn('[visual] network quiet wait timed out — continuing')
  } finally {
    page.off('request', touch)
    page.off('requestfinished', touch)
    page.off('requestfailed', touch)
  }
}

async function waitForPaintSettle(page, samples = 3, intervalMs = 200) {
  // Two consecutive identical layout signatures → paint settled enough to shot.
  let prev = ''
  let stable = 0
  for (let i = 0; i < 30 && stable < samples; i += 1) {
    const sig = await page.evaluate(() => {
      const layout = document.querySelector('.app-layout')
      const stage = document.querySelector('.app-layout__stage, .app-layout__scroll, main')
      const lr = layout?.getBoundingClientRect()
      const sr = stage?.getBoundingClientRect()
      const textLen = (stage?.innerText || '').length
      return [
        Math.round(lr?.width || 0),
        Math.round(lr?.height || 0),
        Math.round(sr?.width || 0),
        Math.round(sr?.height || 0),
        textLen,
        document.querySelectorAll('.app-skeleton, [class*="skeleton"], [class*="Skeleton"]').length,
      ].join('|')
    })
    if (sig === prev) {
      stable += 1
    } else {
      stable = 0
      prev = sig
    }
    await page.waitForTimeout(intervalMs)
  }
}

async function gotoAppRoute(page, route, { ready = true } = {}) {
  const pathPart = route.startsWith('/') ? route : `/${route}`
  const target = hashUrl(pathPart)

  // Prefer in-app hash change: Electron + Vue hash history often ignores a second
  // full page.goto to the same origin with only the hash differing.
  const current = page.url()
  const sameOrigin = (() => {
    try {
      return new URL(current).origin === new URL(BASE_URL).origin
    } catch {
      return false
    }
  })()

  if (sameOrigin && !isLoginRoute(current) && pathPart !== '/login') {
    await page.evaluate((hashRoute) => {
      // Force hashchange even if already on a different hash.
      if (window.location.hash === `#${hashRoute}`) {
        window.location.hash = '#/__visual_nav__'
      }
      window.location.hash = `#${hashRoute}`
    }, pathPart)
  } else {
    await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 60000 })
  }

  await waitForHashRoute(page, pathPart)
  if (ready) {
    const authShell = pathPart === '/login' || pathPart.startsWith('/login')
    if (authShell) {
      await waitForAppShell(page, { expectAuthShell: true })
    } else {
      await waitForAppShell(page, { expectAuthShell: false })
      await waitForNetworkQuiet(page)
      await waitForPaintSettle(page)
    }
  }
}

async function seedAuth(page) {
  const token = process.env.VISUAL_TOKEN?.trim()
  const email = process.env.VISUAL_EMAIL?.trim()
  const password = process.env.VISUAL_PASSWORD ?? ''

  // Same-origin server URL so axios hits Vite proxy → backend (avoids CORS).
  await page.evaluate((serverUrl) => {
    localStorage.setItem('app:server-url', serverUrl)
    localStorage.setItem('app:server-url:version', '1')
  }, BASE_URL)

  if (token) {
    await page.evaluate((t) => {
      localStorage.setItem('token', t)
    }, token)
    await gotoAppRoute(page, '/home')
    return { method: 'token' }
  }

  if (email && password) {
    await gotoAppRoute(page, '/login')
    const emailInput = page.locator('#email, input[type="email"]').first()
    await emailInput.waitFor({ state: 'visible', timeout: 30000 })
    await emailInput.fill(email)
    await page.locator('#password, input[type="password"]').first().fill(password)
    await Promise.all([
      page.waitForFunction(() => {
        const hash = window.location.hash || ''
        return hash.startsWith('#/') && !hash.startsWith('#/login')
      }, { timeout: 30000 }),
      page.locator("button[type='submit']").click(),
    ])
    const url = page.url()
    if (isLoginRoute(url)) {
      const alertText = await page.locator('[role="alert"], .auth-form').innerText().catch(() => '')
      throw new Error(
        `Login failed — still on /login (url=${url}). Check DEV_AUTH_* / backend. UI: ${alertText.slice(0, 200)}`,
      )
    }
    // Land on home with full shell readiness before first scenario.
    await gotoAppRoute(page, '/home')
    return { method: 'form' }
  }

  throw new Error(
    'Auth required: set VISUAL_TOKEN or VISUAL_EMAIL+VISUAL_PASSWORD, '
    + 'or put DEV_AUTH_EMAIL/DEV_AUTH_PASSWORD in repo-root .env.dev.',
  )
}

async function applyChromeState(page, { theme, sidebarOpen }) {
  // Theme: pinia only reads localStorage at init — also force document classes for the shot.
  await page.evaluate(
    ({ themeMode, open }) => {
      localStorage.setItem('app:theme', themeMode)
      localStorage.setItem('ui.sidebarOpen', open ? 'true' : 'false')
      document.documentElement.classList.toggle('dark', themeMode === 'dark')
      document.documentElement.classList.toggle('light', themeMode !== 'dark')
      document.documentElement.dataset.theme = themeMode
      document.documentElement.style.colorScheme = themeMode
    },
    { themeMode: theme, open: sidebarOpen },
  )

  // Sidebar: ui store keeps isSidebarOpen in memory. Prefer live toggle over reload
  // (reload drops the hash route and re-bootstraps the SPA).
  const wantOpen = Boolean(sidebarOpen)
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const isOpen = await page.evaluate(() => {
      const sidebar = document.querySelector('.app-layout__sidebar')
      if (!sidebar) return true
      // AppLayout sets inert + aria-hidden when closed.
      if (sidebar.hasAttribute('inert')) return false
      if (sidebar.getAttribute('aria-hidden') === 'true') return false
      const r = sidebar.getBoundingClientRect()
      return r.width > 40
    })
    if (isOpen === wantOpen) break

    const toggle = page.locator(
      '.titlebar__navigation-button, .app-header__sidebar-toggle, button[aria-label*="侧栏"], button[title*="侧栏"]',
    ).first()
    if (await toggle.count() === 0) break
    await toggle.click({ timeout: 3000 }).catch(() => {})
    await page.waitForTimeout(250)
  }
}

async function stabilizeForSnapshot(page, { maskMain = false } = {}) {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        caret-color: transparent !important;
      }
      img, video, canvas, iframe {
        opacity: 0 !important;
      }
      img, video {
        background: hsl(28 8% 22%) !important;
      }
      ${maskMain ? `
      /* Shell contract only: blank stage so feed churn cannot flake baselines. */
      .app-layout__stage, .app-layout__scroll {
        background: hsl(28 8% 10%) !important;
      }
      .app-layout__stage *, .app-layout__scroll > *:not(.app-layout__header) {
        visibility: hidden !important;
      }
      ` : ''}
    `,
  })

  if (maskMain) {
    await page.evaluate(() => {
      document.querySelectorAll('[data-visual-mask="main"]').forEach((n) => n.remove())
      const stage = document.querySelector('.app-layout__stage')
        || document.querySelector('.app-layout__scroll')
        || document.querySelector('main')
      if (!stage) return
      const r = stage.getBoundingClientRect()
      if (r.width < 200 || r.height < 200) return
      const cover = document.createElement('div')
      cover.setAttribute('data-visual-mask', 'main')
      cover.style.cssText = [
        'position:fixed',
        `left:${Math.max(0, r.left)}px`,
        `top:${Math.max(0, r.top)}px`,
        `width:${r.width}px`,
        `height:${r.height}px`,
        'background:hsl(28 8% 10%)',
        'z-index:2147483646',
        'pointer-events:none',
      ].join(';')
      document.documentElement.appendChild(cover)
    })
  }

  // One short frame after style/mask injection.
  await page.waitForTimeout(200)
}

async function captureScenario(page, scenario) {
  console.log(`[visual] scenario start ${scenario.id} → ${scenario.route}`)

  // 1) Navigate and wait until the SPA route + shell + network + paint are ready.
  //    Do NOT reload() — Electron reload drops the hash and restarts on `/`.
  await gotoAppRoute(page, scenario.route)

  if (isLoginRoute(page.url())) {
    throw new Error(`Redirected to login for scenario ${scenario.id} (url=${page.url()})`)
  }

  const route = appRouteFromUrl(page.url())
  const expectedPrefix = scenario.route.split('?')[0]
  if (
    scenario.optional
    && !route.startsWith(expectedPrefix)
    && !route.startsWith(expectedPrefix.replace(/\/$/, ''))
  ) {
    return { skipped: true, reason: `route mismatch: route=${route}` }
  }

  // 2) Apply theme classes + sidebar open state (click toggle if needed).
  await applyChromeState(page, scenario)
  await waitForPaintSettle(page, 2, 180)

  // 3) Freeze dynamic paint, then screenshot.
  await stabilizeForSnapshot(page, { maskMain: Boolean(scenario.maskMain) })

  const fileName = `${scenario.id}.png`
  const outPath = path.join(OUT_DIR, fileName)
  await page.screenshot({ path: outPath, fullPage: false })
  console.log(`[visual] scenario done  ${scenario.id}`)
  return { skipped: false, outPath, fileName }
}

function pixelDiff(a, b) {
  if (a.width !== b.width || a.height !== b.height) {
    return {
      ok: false,
      reason: `size mismatch actual=${a.width}x${a.height} baseline=${b.width}x${b.height}`,
      diffPixels: Number.POSITIVE_INFINITY,
      ratio: 1,
    }
  }
  const total = a.width * a.height
  let diffPixels = 0
  for (let i = 0; i < a.data.length; i += 4) {
    const dr = Math.abs(a.data[i] - b.data[i])
    const dg = Math.abs(a.data[i + 1] - b.data[i + 1])
    const db = Math.abs(a.data[i + 2] - b.data[i + 2])
    const da = Math.abs(a.data[i + 3] - b.data[i + 3])
    if (dr > 8 || dg > 8 || db > 8 || da > 8) {
      diffPixels += 1
    }
  }
  const ratio = total === 0 ? 0 : diffPixels / total
  const ok = ratio <= THRESHOLD || diffPixels <= MAX_DIFF_PIXELS
  return { ok, diffPixels, ratio, reason: ok ? null : `diffPixels=${diffPixels} ratio=${ratio.toFixed(4)}` }
}

async function compareToBaseline(fileName) {
  const actualPath = path.join(OUT_DIR, fileName)
  const baselinePath = path.join(BASELINE_DIR, fileName)
  if (!(await pathExists(baselinePath))) {
    return { ok: false, reason: `missing baseline: ${baselinePath}` }
  }
  const actual = PNG.decode(await fs.readFile(actualPath))
  const baseline = PNG.decode(await fs.readFile(baselinePath))
  return pixelDiff(actual, baseline)
}

async function promoteBaselines(fileNames) {
  await ensureDir(BASELINE_DIR)
  for (const name of fileNames) {
    const src = path.join(OUT_DIR, name)
    const dest = path.join(BASELINE_DIR, name)
    await fs.copyFile(src, dest)
    console.log(`[visual] baseline ← ${name}`)
  }
}

/**
 * Launch real Squirrel Electron; Playwright attaches over CDP.
 * Exposes the same Page API as browser, but with preload + main-process IPC.
 */
async function launchElectronSession(pw) {
  const electronPath = await resolveElectronExecutable()
  const userData = process.env.SQUIRREL_VISUAL_USER_DATA
    || path.join(os.tmpdir(), 'squirrel-visual-userdata')
  await ensureDir(userData)

  const rendererUrl = (process.env.DESKTOP_RENDERER_URL || `${BASE_URL}/`).replace(/\/?$/, '/')
  const electronApi = pw._electron || pw.electron
  if (!electronApi?.launch) {
    throw new Error('playwright-core has no _electron.launch — upgrade playwright-core')
  }

  console.log(`[visual] electron=${electronPath}`)
  console.log(`[visual] renderer=${rendererUrl}`)
  console.log(`[visual] userData=${userData}`)

  const electronApp = await electronApi.launch({
    executablePath: electronPath,
    args: ['.'],
    cwd: desktopDir,
    env: {
      ...process.env,
      SQUIRREL_VISUAL_TEST: '1',
      SQUIRREL_VISUAL_USER_DATA: userData,
      DESKTOP_RENDERER_URL: rendererUrl,
      // Avoid inheriting a browser-only Chromium path into Electron.
      ELECTRON_RUN_AS_NODE: undefined,
    },
    timeout: 90000,
  })

  const page = await electronApp.firstWindow({ timeout: 90000 })

  // Fixed bounds for stable screenshots (title bar included in content size).
  await electronApp.evaluate(({ BrowserWindow }, size) => {
    const win = BrowserWindow.getAllWindows()[0]
    if (!win) return
    win.setMenuBarVisibility(false)
    win.setBounds({ x: 40, y: 40, width: size.width, height: size.height })
    if (win.isMinimized()) win.restore()
    win.show()
  }, VIEWPORT)

  // Wait until preload bridge is present — proves we are in desktop, not bare web.
  await page.waitForFunction(() => {
    return Boolean(window.desktopApp && window.desktopApp.isDesktop === true)
  }, { timeout: 30000 })

  const bridgeOk = await page.evaluate(() => ({
    isDesktop: window.desktopApp?.isDesktop === true,
    platform: window.desktopApp?.platform,
    hasMusic: typeof window.desktopApp?.callMusic === 'function',
    hasSiteLogin: typeof window.desktopApp?.openSiteLogin === 'function',
  }))
  console.log(`[visual] desktopBridge=${JSON.stringify(bridgeOk)}`)

  return {
    page,
    async close() {
      // Playwright's electronApp.close() can hang on Windows if the app
      // ignores window-all-closed while secondary windows/sessions linger.
      // Prefer graceful close with a hard kill timeout.
      const child = typeof electronApp.process === 'function' ? electronApp.process() : null
      const closePromise = electronApp.close().catch(() => {})
      const timed = await Promise.race([
        closePromise.then(() => 'closed'),
        new Promise((resolve) => setTimeout(() => resolve('timeout'), 8000)),
      ])
      if (timed === 'timeout' && child?.pid) {
        console.warn(`[visual] electron close timed out; killing pid=${child.pid}`)
        try {
          if (process.platform === 'win32') {
            const { spawn } = await import('node:child_process')
            await new Promise((resolve) => {
              const killer = spawn('taskkill', ['/pid', String(child.pid), '/t', '/f'], {
                stdio: 'ignore',
                windowsHide: true,
              })
              killer.once('exit', resolve)
              killer.once('error', resolve)
            })
          } else {
            child.kill('SIGKILL')
          }
        } catch {
          // ignore
        }
      }
    },
  }
}

async function launchBrowserSession(pw) {
  const { chromium } = pw
  const launchOpts = {
    headless: true,
    args: ['--force-device-scale-factor=1', '--hide-scrollbars'],
  }
  const chromiumPath = await resolveChromiumPath()
  if (chromiumPath) {
    launchOpts.executablePath = chromiumPath
    console.log(`[visual] chromium=${chromiumPath}`)
  }
  console.warn('[visual] WARNING: browser driver has no Electron preload/IPC — layout-only probe')

  const browser = await chromium.launch(launchOpts)
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 1,
    colorScheme: 'dark',
  })
  const page = await context.newPage()
  return {
    page,
    async close() {
      await context.close().catch(() => {})
      await browser.close().catch(() => {})
    },
  }
}

async function runScenarios(page) {
  const captured = []
  const skipped = []
  const failures = []

  const auth = await seedAuth(page)
  console.log(`[visual] auth=${auth.method}`)

  for (const scenario of SCENARIOS) {
    try {
      const result = await captureScenario(page, scenario)
      if (result.skipped) {
        skipped.push({ id: scenario.id, reason: result.reason })
        console.warn(`[visual] skip ${scenario.id}: ${result.reason}`)
        continue
      }
      captured.push(result.fileName)
      console.log(`[visual] shot ${scenario.id} → ${result.fileName}`)
    } catch (err) {
      if (scenario.optional) {
        skipped.push({ id: scenario.id, reason: err.message })
        console.warn(`[visual] skip ${scenario.id}: ${err.message}`)
      } else {
        failures.push({ id: scenario.id, reason: err.message })
        console.error(`[visual] FAIL ${scenario.id}: ${err.message}`)
      }
    }
  }

  return { captured, skipped, failures }
}

async function finish(captured, skipped, failures) {
  if (failures.length) {
    console.error(`[visual] capture failures: ${failures.length}`)
    process.exitCode = 1
    return
  }

  if (modeUpdate) {
    if (!captured.length) {
      console.error('[visual] nothing to promote')
      process.exitCode = 1
      return
    }
    await promoteBaselines(captured)
    console.log('[visual] baselines updated — review PNGs before commit')
    return
  }

  if (modeCheck) {
    if (!captured.length) {
      console.error('[visual] no captures to check')
      process.exitCode = 1
      return
    }
    let failed = 0
    for (const name of captured) {
      const cmp = await compareToBaseline(name)
      if (!cmp.ok) {
        failed += 1
        console.error(`[visual] DIFF ${name}: ${cmp.reason}`)
      } else {
        console.log(`[visual] OK   ${name} (diffPixels=${cmp.diffPixels ?? 0})`)
      }
    }
    if (failed) {
      console.error(`[visual] ${failed}/${captured.length} scenarios differ from baseline`)
      console.error('[visual] If intentional: npm run visual:update && review git diff of baselines')
      console.error('[visual] Note: electron baselines differ from old browser baselines — re-update once.')
      process.exitCode = 1
      return
    }
    console.log(`[visual] all ${captured.length} scenarios match baseline (threshold=${THRESHOLD})`)
    if (skipped.length) {
      console.warn(`[visual] skipped ${skipped.length} optional scenarios`)
    }
    return
  }

  console.log(`[visual] wrote ${captured.length} actuals to ${OUT_DIR}`)
  if (skipped.length) {
    console.warn(`[visual] skipped ${skipped.length} optional scenarios`)
  }
  console.log('[visual] next: npm run visual:update  (after reviewing actuals)')
  console.log('[visual]       npm run visual:check   (after baselines exist)')
}

async function main() {
  BASE_URL = await probeSquirrelBaseUrl()
  console.log(`[visual] driver=${DRIVER}`)
  console.log(`[visual] base=${BASE_URL}`)
  console.log(`[visual] out=${OUT_DIR}`)
  console.log(`[visual] baseline=${BASELINE_DIR}`)
  console.log(`[visual] mode=${modeUpdate ? 'update' : modeCheck ? 'check' : 'snapshot'}`)
  console.log(`[visual] authEmail=${process.env.VISUAL_EMAIL ? 'from env/.env.dev' : 'missing'}`)

  await waitForRenderer(BASE_URL)
  await ensureDir(OUT_DIR)

  const pw = await loadPlaywright()
  const session = DRIVER === 'electron'
    ? await launchElectronSession(pw)
    : await launchBrowserSession(pw)

  try {
    const { captured, skipped, failures } = await runScenarios(session.page)
    await finish(captured, skipped, failures)
  } finally {
    await session.close()
  }
}

main().catch((err) => {
  console.error('[visual] ERR', err)
  process.exit(1)
})
