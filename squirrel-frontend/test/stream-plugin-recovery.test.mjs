import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const hlsPluginPath = new URL('../src/components/video-player/plugins/hls/HlsPlugin.ts', import.meta.url)
const dashPluginPath = new URL('../src/components/video-player/plugins/dash/DashPlugin.ts', import.meta.url)

test('hls plugin provides targeted playback recovery for network and media failures', async () => {
  const source = await readFile(hlsPluginPath, 'utf8')

  assert.match(source, /recoverPlayback\(error: PlayerError/)
  assert.match(source, /this\.hls\.startLoad\(\)/)
  assert.match(source, /this\.hls\.recoverMediaError\(\)/)
})

test('dash plugin can ask the core player to reload the current source for recovery', async () => {
  const source = await readFile(dashPluginPath, 'utf8')

  assert.match(source, /recoverPlayback\(error: PlayerError/)
  assert.match(source, /return 'reload-source'/)
})
