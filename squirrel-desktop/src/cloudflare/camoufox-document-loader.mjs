import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { Camoufox } from 'camoufox-js'

const CHECK_INTERVAL_MS = 500
const TURNSTILE_CLICK_INTERVAL_MS = 2000
const COOKIE_SYNC_URL_PATH = '/'
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const CAMOUFOX_ADDON_PATH = path.join(__dirname, 'camoufox-addon')

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const hostKeyForUrl = (targetUrl) => new URL(targetUrl).hostname.toLowerCase()

const cookieUrlFromParts = (secure, domain) => {
  const hostname = String(domain || '').replace(/^\./, '')
  return `${secure ? 'https' : 'http'}://${hostname}${COOKIE_SYNC_URL_PATH}`
}

const toPlaywrightSameSite = (sameSite) => {
  const value = String(sameSite || '').toLowerCase()
  if (value === 'strict') return 'Strict'
  if (value === 'lax') return 'Lax'
  if (value === 'no_restriction' || value === 'none') return 'None'
  return undefined
}

const isChallengeHtml = (html, title = '') => {
  const titleText = String(title || '')
  if (/<title>\s*JavDB\b/i.test(html) || html.includes('m3u8|') || /class=["'][^"']*\bitem\b/i.test(html)) {
    return false
  }

  const source = `${title}\n${html}`.toLowerCase()
  return titleText.toLowerCase().includes('just a moment')
    || source.includes('please complete the captcha')
    || source.includes('cf-turnstile')
    || source.includes('cf_chl_')
    || source.includes('/cdn-cgi/challenge-platform/')
    || source.includes('challenges.cloudflare.com/turnstile')
}

const findShadowRootElements = async (queryable, selector) => {
  try {
    const handle = await queryable.evaluateHandle((targetSelector) => {
      const roots = []
      const collectRoots = (node) => {
        if (!node) return
        if (node.shadowRootUnl) {
          roots.push(node.shadowRootUnl)
          collectRoots(node.shadowRootUnl)
        }
        for (const child of node.querySelectorAll('*')) {
          if (child.shadowRootUnl) {
            collectRoots(child)
          }
        }
      }
      collectRoots(document)
      const elements = []
      for (const root of roots) {
        const element = root.querySelector(targetSelector)
        if (element) {
          elements.push(element)
        }
      }
      return elements
    }, selector)
    const properties = await handle.getProperties()
    return [...properties.values()]
      .map((property) => property.asElement())
      .filter(Boolean)
  } catch (err) {
    console.debug('[squirrel-desktop] findShadowRootElements error', err)
    return []
  }
}

const findCloudflareFrames = async (page) => {
  try {
    return await findShadowRootElements(page, 'iframe')
  } catch (err) {
    console.debug('[squirrel-desktop] findCloudflareFrames error', err)
    return []
  }
}

const clickCloudflareCheckbox = async (page) => {
  const iframeElements = await findCloudflareFrames(page)

  for (const element of iframeElements) {
    const src = await element.getAttribute('src').catch(() => '')
    if (!String(src || '').includes('https://challenges.cloudflare.com/cdn-cgi/challenge-platform/')) continue
    const frame = await element.contentFrame()
    if (!frame || frame.isDetached()) continue

    for (let attempt = 0; attempt < 10; attempt += 1) {
      const checkboxes = await findShadowRootElements(frame, 'input[type="checkbox"]')
      for (const checkbox of checkboxes) {
        if (await checkbox.isVisible().catch(() => false)) {
          await checkbox.click()
          await sleep(6000)
          return true
        }
      }
      await sleep(1000)
    }
  }
  return false
}

const attemptTurnstileClick = async (page) => {
  return clickCloudflareCheckbox(page)
}

export class CamoufoxDocumentLoader {
  constructor({ electronSession, userDataDir }) {
    this.electronSession = electronSession
    this.userDataDir = userDataDir
    this.entries = new Map()
    this.locks = new Map()
  }

  async close() {
    const entries = Array.from(this.entries.values())
    this.entries.clear()
    await Promise.all(entries.map(async (entry) => {
      await entry.context.close().catch((err) => {
        console.debug('[squirrel-desktop] context close error', err)
      })
    }))
  }

  async loadHtml(targetUrl, options = {}) {
    const normalizedUrl = new URL(targetUrl).toString()
    const key = hostKeyForUrl(normalizedUrl)
    return this.runWithLock(key, async () => {
      const entry = await this.getEntry(key)
      const page = await entry.context.newPage()
      try {
        await this.restoreElectronCookies(entry.context, normalizedUrl)
        await page.setExtraHTTPHeaders({
          'Accept-Language': 'en-US,en;q=0.9',
          ...(options.headers || {}),
        })
        await page.goto(normalizedUrl, {
          waitUntil: 'domcontentloaded',
          timeout: Number(options.timeoutMs) || 30000,
        })
        const html = await this.waitForReadablePage(page, Number(options.challengeTimeoutMs) || 120000)
        await this.syncCookiesToElectron(entry.context, normalizedUrl)
        return html
      } finally {
        await page.close().catch((err) => {
          console.debug('[squirrel-desktop] page close error', err)
        })
      }
    })
  }

  async getEntry(key) {
    const existing = this.entries.get(key)
    if (existing) return existing

    const profileDir = path.join(this.userDataDir, key)
    fs.mkdirSync(profileDir, { recursive: true })
    const context = await Camoufox({
      user_data_dir: profileDir,
      headless: true,
      os: 'windows',
      locale: 'en-US',
      config: { forceScopeAccess: true },
      addons: [CAMOUFOX_ADDON_PATH],
      block_webrtc: true,
      disable_coop: true,
      main_world_eval: true,
      humanize: true,
      enable_cache: true,
      i_know_what_im_doing: true,
    })
    const entry = { context }
    this.entries.set(key, entry)
    return entry
  }

  async runWithLock(key, task) {
    const previous = this.locks.get(key) || Promise.resolve()
    let release
    const next = new Promise((resolve) => {
      release = resolve
    })
    const current = previous.then(() => next, () => next)
    this.locks.set(key, current)

    await previous.catch((err) => {
      console.debug('[squirrel-desktop] lock previous error', err)
    })
    try {
      return await task()
    } finally {
      release()
      if (this.locks.get(key) === current) {
        this.locks.delete(key)
      }
    }
  }

  async restoreElectronCookies(context, targetUrl) {
    const cookies = await this.electronSession.cookies.get({ url: targetUrl })
    const playwrightCookies = cookies.map((cookie) => {
      const sameSite = toPlaywrightSameSite(cookie.sameSite)
      return {
        name: cookie.name,
        value: cookie.value,
        domain: cookie.domain,
        path: cookie.path || COOKIE_SYNC_URL_PATH,
        expires: Number.isFinite(cookie.expirationDate) ? cookie.expirationDate : -1,
        httpOnly: cookie.httpOnly === true,
        secure: cookie.secure === true,
        ...(sameSite ? { sameSite } : {}),
      }
    })
    if (playwrightCookies.length > 0) {
      await context.addCookies(playwrightCookies)
    }
  }

  async syncCookiesToElectron(context, targetUrl) {
    const cookies = await context.cookies(targetUrl)
    for (const cookie of cookies) {
      await this.electronSession.cookies.set({
        url: cookieUrlFromParts(cookie.secure, cookie.domain),
        name: cookie.name,
        value: cookie.value,
        domain: cookie.domain,
        path: cookie.path || COOKIE_SYNC_URL_PATH,
        secure: cookie.secure === true,
        httpOnly: cookie.httpOnly === true,
        expirationDate: Number.isFinite(cookie.expires) && cookie.expires > 0 ? cookie.expires : undefined,
      })
    }
    await this.electronSession.cookies.flushStore()
  }

  async waitForReadablePage(page, timeoutMs) {
    const deadline = Date.now() + timeoutMs
    let lastHtml = ''
    let lastClickAt = 0

    while (Date.now() < deadline) {
      const title = await page.title().catch(() => '')
      lastHtml = await page.content().catch(() => '')
      if (!isChallengeHtml(lastHtml, title)) {
        return lastHtml
      }

      if (Date.now() - lastClickAt >= TURNSTILE_CLICK_INTERVAL_MS) {
        const clicked = await attemptTurnstileClick(page)
        if (clicked) {
          lastClickAt = Date.now()
        }
      }
      await sleep(CHECK_INTERVAL_MS)
    }

    throw new Error('Cloudflare verification timed out')
  }
}
