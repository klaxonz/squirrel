import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'

import {
  DEFAULT_WINDOW_STATE,
  loadWindowState,
  persistWindowState,
} from '../src/window-state.mjs'

const withTempUserData = async (fn) => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'squirrel-window-state-'))
  try {
    return await fn(dir)
  } finally {
    await rm(dir, { recursive: true, force: true })
  }
}

test('loadWindowState returns defaults when state file is missing', async () => {
  await withTempUserData(async (userDataPath) => {
    assert.deepEqual(loadWindowState(userDataPath), {
      width: DEFAULT_WINDOW_STATE.width,
      height: DEFAULT_WINDOW_STATE.height,
      isMaximized: false,
    })
  })
})

test('loadWindowState sanitizes stored bounds', async () => {
  await withTempUserData(async (userDataPath) => {
    await writeFile(
      path.join(userDataPath, 'window-state.json'),
      JSON.stringify({
        x: 10.4,
        y: '20',
        width: 200,
        height: 719.2,
        isMaximized: true,
      }),
      'utf8',
    )

    assert.deepEqual(loadWindowState(userDataPath), {
      x: 10,
      y: 20,
      width: DEFAULT_WINDOW_STATE.minWidth,
      height: DEFAULT_WINDOW_STATE.minHeight,
      isMaximized: true,
    })
  })
})

test('persistWindowState saves normal bounds and skips minimized windows', async () => {
  await withTempUserData(async (userDataPath) => {
    const windowStatePath = path.join(userDataPath, 'window-state.json')
    const window = {
      isDestroyed: () => false,
      isMinimized: () => false,
      isMaximized: () => false,
      getBounds: () => ({ x: 1, y: 2, width: 900, height: 700 }),
      getNormalBounds: () => ({ x: 0, y: 0, width: 1600, height: 1000 }),
    }

    persistWindowState(userDataPath, window)

    assert.deepEqual(JSON.parse(await readFile(windowStatePath, 'utf8')), {
      x: 1,
      y: 2,
      width: DEFAULT_WINDOW_STATE.minWidth,
      height: DEFAULT_WINDOW_STATE.minHeight,
      isMaximized: false,
    })

    const minimizedWindow = {
      ...window,
      isMinimized: () => true,
      getBounds: () => ({ x: 9, y: 9, width: 1900, height: 1200 }),
    }
    persistWindowState(userDataPath, minimizedWindow)

    assert.deepEqual(JSON.parse(await readFile(windowStatePath, 'utf8')), {
      x: 1,
      y: 2,
      width: DEFAULT_WINDOW_STATE.minWidth,
      height: DEFAULT_WINDOW_STATE.minHeight,
      isMaximized: false,
    })
  })
})
