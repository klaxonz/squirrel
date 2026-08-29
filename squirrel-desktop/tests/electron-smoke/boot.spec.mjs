import assert from 'node:assert/strict'

describe('Electron application smoke', () => {
  it('boots a BrowserWindow with the preload bridge', async () => {
    await browser.waitUntil(
      async () => (await browser.getTitle()) === 'Squirrel Electron Smoke',
      { timeout: 30_000, timeoutMsg: 'offline Electron fixture did not load' },
    )

    const bridge = await browser.execute(() => ({
      isDesktop: window.desktopApp?.isDesktop,
      platform: window.desktopApp?.platform,
      electron: window.desktopApp?.versions?.electron,
    }))
    assert.equal(bridge.isDesktop, true)
    assert.equal(typeof bridge.platform, 'string')
    assert.match(bridge.electron, /^41\\./)

    const windowCount = await browser.electron.execute((electron) => (
      electron.BrowserWindow.getAllWindows().length
    ))
    assert.equal(windowCount, 1)
  })
})
