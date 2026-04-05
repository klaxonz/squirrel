import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const hlsPluginPath = new URL('../src/components/video-player/plugins/hls/HlsPlugin.ts', import.meta.url)

test('hls plugin preloads the target level before switching when manually changing quality', async () => {
  const source = await readFile(hlsPluginPath, 'utf8')

  assert.match(
    source,
    /this\.hls\.nextLevel\s*=\s*targetLevel/
  )
})
