import assert from 'node:assert/strict'
import test from 'node:test'

import {
  createWebContentOpener,
  createWebContentSession,
  createWebContentWindowOptions,
  evaluateFrameEmbeddability,
  hardenWebContentSession,
  normalizeWebContentUrl,
  probeFrameEmbeddability,
  WEB_CONTENT_SESSION_PARTITION,
} from '../src/web-content-window.mjs'

class FakeWebContentSession {
  constructor() {
    this.listeners = new Map()
    this.listenerRegistrations = new Map()
    this.permissionCheckHandler = null
    this.permissionRequestHandler = null
  }

  on(eventName, listener) {
    this.listeners.set(eventName, listener)
    this.listenerRegistrations.set(
      eventName,
      (this.listenerRegistrations.get(eventName) || 0) + 1,
    )
  }

  setPermissionCheckHandler(handler) {
    this.permissionCheckHandler = handler
  }

  setPermissionRequestHandler(handler) {
    this.permissionRequestHandler = handler
  }
}

const createFakeSessionManager = (webContentSession = new FakeWebContentSession()) => {
  const calls = []
  return {
    calls,
    defaultSession: { name: 'default-session' },
    fromPartition: (partition, options) => {
      calls.push({ partition, options })
      return webContentSession
    },
    webContentSession,
  }
}

class FakeWebContents {
  constructor() {
    this.listeners = new Map()
    this.windowOpenHandler = null
  }

  on(eventName, listener) {
    this.listeners.set(eventName, listener)
  }

  setWindowOpenHandler(handler) {
    this.windowOpenHandler = handler
  }
}

class FakeBrowserWindow {
  constructor({ loadError = null } = {}) {
    this.destroyed = false
    this.loadError = loadError
    this.loadedUrls = []
    this.listeners = new Map()
    this.shown = false
    this.webContents = new FakeWebContents()
  }

  once(eventName, listener) {
    this.listeners.set(eventName, listener)
  }

  async loadURL(url) {
    this.loadedUrls.push(url)
    if (this.loadError) {
      throw this.loadError
    }
  }

  isDestroyed() {
    return this.destroyed
  }

  destroy() {
    this.destroyed = true
    this.listeners.get('closed')?.()
  }

  show() {
    this.shown = true
  }
}

test('normalizeWebContentUrl only accepts absolute HTTP(S) strings', () => {
  assert.equal(
    normalizeWebContentUrl('  HTTPS://Example.COM/articles?id=1#summary  '),
    'https://example.com/articles?id=1#summary',
  )
  assert.equal(normalizeWebContentUrl('http://localhost:8000/feed'), 'http://localhost:8000/feed')

  for (const value of [
    '',
    'example.com',
    'javascript:alert(1)',
    'data:text/html,unsafe',
    'file:///tmp/article.html',
    'mailto:reader@example.com',
    42,
    { toString: () => 'https://example.com/' },
  ]) {
    assert.equal(normalizeWebContentUrl(value), null)
  }
})

test('createWebContentSession uses a dedicated in-memory partition and denies capabilities', () => {
  const sessionManager = createFakeSessionManager()

  const webContentSession = createWebContentSession(sessionManager)
  assert.equal(webContentSession, sessionManager.webContentSession)
  assert.notEqual(webContentSession, sessionManager.defaultSession)
  assert.equal(WEB_CONTENT_SESSION_PARTITION.startsWith('persist:'), false)
  assert.deepEqual(sessionManager.calls, [{
    partition: WEB_CONTENT_SESSION_PARTITION,
    options: { cache: false },
  }])

  assert.equal(
    webContentSession.permissionCheckHandler({}, 'geolocation', 'https://example.com'),
    false,
  )

  let permissionDecision = null
  webContentSession.permissionRequestHandler(
    {},
    'notifications',
    (allowed) => { permissionDecision = allowed },
  )
  assert.equal(permissionDecision, false)

  let downloadPrevented = false
  webContentSession.listeners.get('will-download')({
    preventDefault: () => { downloadPrevented = true },
  })
  assert.equal(downloadPrevented, true)
})

test('hardenWebContentSession installs session-wide guards only once', () => {
  const webContentSession = new FakeWebContentSession()

  assert.equal(hardenWebContentSession(webContentSession), webContentSession)
  assert.equal(hardenWebContentSession(webContentSession), webContentSession)
  assert.equal(webContentSession.listenerRegistrations.get('will-download'), 1)
})

test('createWebContentWindowOptions enforces an isolated sandbox without preload', () => {
  const parentWindow = { isDestroyed: () => false }
  const webContentSession = new FakeWebContentSession()
  const options = createWebContentWindowOptions(parentWindow, webContentSession)

  assert.equal(options.parent, parentWindow)
  assert.deepEqual(options.webPreferences, {
    session: webContentSession,
    sandbox: true,
    contextIsolation: true,
    nodeIntegration: false,
    webSecurity: true,
    allowRunningInsecureContent: false,
  })
  assert.equal(Object.hasOwn(options.webPreferences, 'preload'), false)

  const destroyedParent = { isDestroyed: () => true }
  assert.equal(
    Object.hasOwn(createWebContentWindowOptions(destroyedParent, webContentSession), 'parent'),
    false,
  )
})

test('openWebContent loads valid content and sends remote popups to the system browser', async () => {
  const createdWindows = []
  const createdOptions = []
  const externalUrls = []
  const sessionManager = createFakeSessionManager()
  const opener = createWebContentOpener({
    createWindow: (options) => {
      createdOptions.push(options)
      const browserWindow = new FakeBrowserWindow()
      createdWindows.push(browserWindow)
      return browserWindow
    },
    openExternal: async (url) => externalUrls.push(url),
    sessionManager,
  })
  const parentWindow = { isDestroyed: () => false }

  assert.equal(await opener.openWebContent(' https://example.com/story ', parentWindow), true)
  assert.equal(createdWindows.length, 1)
  assert.equal(createdOptions[0].parent, parentWindow)
  assert.equal(createdOptions[0].webPreferences.session, sessionManager.webContentSession)
  assert.notEqual(createdOptions[0].webPreferences.session, sessionManager.defaultSession)
  assert.deepEqual(createdWindows[0].loadedUrls, ['https://example.com/story'])
  assert.equal(createdWindows[0].shown, true)

  assert.deepEqual(
    createdWindows[0].webContents.windowOpenHandler({ url: 'https://links.example/path' }),
    { action: 'deny' },
  )
  await Promise.resolve()
  await Promise.resolve()
  assert.deepEqual(externalUrls, ['https://links.example/path'])

  assert.deepEqual(
    createdWindows[0].webContents.windowOpenHandler({ url: 'javascript:alert(1)' }),
    { action: 'deny' },
  )
  await Promise.resolve()
  assert.deepEqual(externalUrls, ['https://links.example/path'])
})

test('openWebContent blocks non-web navigation inside the remote window', async () => {
  const browserWindow = new FakeBrowserWindow()
  const opener = createWebContentOpener({
    createWindow: () => browserWindow,
    openExternal: async () => {},
    sessionManager: createFakeSessionManager(),
  })

  assert.equal(await opener.openWebContent('https://example.com/'), true)

  for (const eventName of ['will-navigate', 'will-redirect']) {
    let prevented = false
    browserWindow.webContents.listeners.get(eventName)(
      { preventDefault: () => { prevented = true } },
      'file:///etc/passwd',
    )
    assert.equal(prevented, true)

    prevented = false
    browserWindow.webContents.listeners.get(eventName)(
      { preventDefault: () => { prevented = true } },
      'https://example.com/next',
    )
    assert.equal(prevented, false)
  }
})

test('openWebContent rejects invalid input before creating a window', async () => {
  let createCount = 0
  const opener = createWebContentOpener({
    createWindow: () => {
      createCount += 1
      return new FakeBrowserWindow()
    },
    openExternal: async () => {},
    sessionManager: createFakeSessionManager(),
  })

  assert.equal(await opener.openWebContent('file:///tmp/article.html'), false)
  assert.equal(createCount, 0)
})

test('openWebContent destroys a failed startup window and returns false', async () => {
  const loadError = new Error('load failed')
  const browserWindow = new FakeBrowserWindow({ loadError })
  const errors = []
  const opener = createWebContentOpener({
    createWindow: () => browserWindow,
    openExternal: async () => {},
    sessionManager: createFakeSessionManager(),
    onError: (error) => errors.push(error),
  })

  assert.equal(await opener.openWebContent('https://example.com/'), false)
  assert.equal(browserWindow.destroyed, true)
  assert.equal(browserWindow.shown, false)
  assert.deepEqual(errors, [loadError])
})

test('openWebContent returns false when BrowserWindow construction fails', async () => {
  const creationError = new Error('constructor failed')
  const errors = []
  const opener = createWebContentOpener({
    createWindow: () => { throw creationError },
    openExternal: async () => {},
    sessionManager: createFakeSessionManager(),
    onError: (error) => errors.push(error),
  })

  assert.equal(await opener.openWebContent('https://example.com/'), false)
  assert.deepEqual(errors, [creationError])
})

test('openWebContent keeps its false contract when error reporting also fails', async () => {
  const opener = createWebContentOpener({
    createWindow: () => { throw new Error('constructor failed') },
    openExternal: async () => {},
    sessionManager: createFakeSessionManager(),
    onError: () => { throw new Error('logger failed') },
  })

  assert.equal(await opener.openWebContent('https://example.com/'), false)
})

test('evaluateFrameEmbeddability blocks DENY and SAMEORIGIN frame options', () => {
  assert.deepEqual(
    evaluateFrameEmbeddability({ 'X-Frame-Options': 'DENY' }, 'https://champhoon.xyz/log/hello-astro/'),
    {
      ok: true,
      embeddable: false,
      reason: 'x-frame-options',
      finalUrl: 'https://champhoon.xyz/log/hello-astro/',
      detail: 'DENY',
    },
  )
  assert.equal(
    evaluateFrameEmbeddability({ 'x-frame-options': 'SAMEORIGIN' }).embeddable,
    false,
  )
  assert.equal(
    evaluateFrameEmbeddability({ 'content-security-policy': "frame-ancestors 'none'" }).embeddable,
    false,
  )
  assert.equal(
    evaluateFrameEmbeddability({ 'content-security-policy': "frame-ancestors 'self' https://partner.example" }).embeddable,
    false,
  )
  assert.equal(
    evaluateFrameEmbeddability({ 'content-security-policy': 'frame-ancestors *' }).embeddable,
    true,
  )
  assert.equal(evaluateFrameEmbeddability({}).embeddable, true)
})

test('probeFrameEmbeddability uses response headers and discards the body', async () => {
  const cancelled = []
  const fetchImpl = async (url, init) => {
    assert.equal(url, 'https://champhoon.xyz/log/hello-astro/')
    assert.equal(init.method, 'GET')
    assert.equal(init.headers.Range, 'bytes=0-0')
    return {
      url,
      headers: {
        entries: () => [['x-frame-options', 'DENY']],
      },
      body: {
        cancel: async () => {
          cancelled.push(url)
        },
      },
    }
  }

  const result = await probeFrameEmbeddability('https://champhoon.xyz/log/hello-astro/', { fetchImpl })
  assert.deepEqual(result, {
    ok: true,
    embeddable: false,
    reason: 'x-frame-options',
    finalUrl: 'https://champhoon.xyz/log/hello-astro/',
    detail: 'DENY',
  })
  assert.deepEqual(cancelled, ['https://champhoon.xyz/log/hello-astro/'])
})

test('probeFrameEmbeddability stays optimistic when the network probe fails', async () => {
  const result = await probeFrameEmbeddability('https://example.com/post', {
    fetchImpl: async () => {
      throw new Error('offline')
    },
  })
  assert.equal(result.ok, false)
  assert.equal(result.embeddable, true)
  assert.equal(result.reason, 'probe-failed')
})
