import assert from 'node:assert/strict'
import test from 'node:test'

import { createInAppWebViewController } from '../src/in-app-web-view.mjs'
import { WEB_CONTENT_SESSION_PARTITION } from '../src/web-content-window.mjs'

class FakeWebContents {
  constructor() {
    this.destroyed = false
    this.listeners = new Map()
    this.loadedUrls = []
    this.reloadCount = 0
    this.windowOpenHandler = null
  }

  on(eventName, listener) {
    this.listeners.set(eventName, listener)
  }

  setWindowOpenHandler(handler) {
    this.windowOpenHandler = handler
  }

  async loadURL(url) {
    this.loadedUrls.push(url)
  }

  reload() {
    this.reloadCount += 1
  }

  isDestroyed() {
    return this.destroyed
  }

  close() {
    this.destroyed = true
  }
}

class FakeWebContentsView {
  constructor() {
    this.bounds = null
    this.webContents = new FakeWebContents()
    this.visible = true
  }

  setBounds(bounds) {
    this.bounds = bounds
  }

  setVisible(visible) {
    this.visible = visible
  }
}

class FakeParentWindow {
  constructor() {
    this.id = 7
    this.destroyed = false
    this.closedListener = null
    this.contentView = {
      children: [],
      addChildView(view) {
        this.children.push(view)
      },
      removeChildView(view) {
        this.children = this.children.filter((child) => child !== view)
      },
    }
  }

  once(eventName, listener) {
    if (eventName === 'closed') this.closedListener = listener
  }

  isDestroyed() {
    return this.destroyed
  }
}

const createFakeSessionManager = () => {
  const session = {
    listeners: new Map(),
    setPermissionCheckHandler() {},
    setPermissionRequestHandler() {},
    on(eventName, listener) {
      this.listeners.set(eventName, listener)
    },
  }
  return {
    fromPartition: (partition, options) => {
      assert.equal(partition, WEB_CONTENT_SESSION_PARTITION)
      assert.deepEqual(options, { cache: false })
      return session
    },
  }
}

test('in-app web view opens inside the parent window bounds', async () => {
  const created = []
  const controller = createInAppWebViewController({
    createWebContentsView: () => {
      const view = new FakeWebContentsView()
      created.push(view)
      return view
    },
    openExternal: async () => {},
    sessionManager: createFakeSessionManager(),
  })
  const parentWindow = new FakeParentWindow()

  assert.equal(
    await controller.open(parentWindow, 'https://champhoon.xyz/log/hello-astro/', {
      x: 120,
      y: 80,
      width: 900,
      height: 640,
    }),
    true,
  )
  assert.equal(created.length, 1)
  assert.deepEqual(created[0].bounds, { x: 120, y: 80, width: 900, height: 640 })
  assert.deepEqual(created[0].webContents.loadedUrls, ['https://champhoon.xyz/log/hello-astro/'])
  assert.equal(parentWindow.contentView.children.length, 1)
})

test('in-app web view rejects non-http urls and invalid bounds', async () => {
  let createCount = 0
  const controller = createInAppWebViewController({
    createWebContentsView: () => {
      createCount += 1
      return new FakeWebContentsView()
    },
    openExternal: async () => {},
    sessionManager: createFakeSessionManager(),
  })
  const parentWindow = new FakeParentWindow()

  assert.equal(await controller.open(parentWindow, 'javascript:alert(1)', {
    x: 0, y: 0, width: 100, height: 100,
  }), false)
  assert.equal(await controller.open(parentWindow, 'https://example.com/', {
    x: 0, y: 0, width: 0, height: 100,
  }), false)
  assert.equal(createCount, 0)
})

test('in-app web view reuses one view, reloads, and hides cleanly', async () => {
  const created = []
  const controller = createInAppWebViewController({
    createWebContentsView: () => {
      const view = new FakeWebContentsView()
      created.push(view)
      return view
    },
    openExternal: async () => {},
    sessionManager: createFakeSessionManager(),
  })
  const parentWindow = new FakeParentWindow()

  assert.equal(await controller.open(parentWindow, 'https://example.com/a', {
    x: 10, y: 10, width: 400, height: 300,
  }), true)
  assert.equal(await controller.open(parentWindow, 'https://example.com/b', {
    x: 20, y: 30, width: 500, height: 400,
  }), true)
  assert.equal(created.length, 1)
  assert.deepEqual(created[0].webContents.loadedUrls, [
    'https://example.com/a',
    'https://example.com/b',
  ])
  assert.deepEqual(created[0].bounds, { x: 20, y: 30, width: 500, height: 400 })

  assert.equal(await controller.reload(parentWindow), true)
  assert.equal(created[0].webContents.reloadCount, 1)

  assert.equal(controller.hide(parentWindow), true)
  assert.equal(parentWindow.contentView.children.length, 0)
  assert.equal(created[0].webContents.destroyed, true)
})
