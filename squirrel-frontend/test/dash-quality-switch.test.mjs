import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const dashPluginPath = new URL('../src/components/video-player/plugins/dash/DashPlugin.ts', import.meta.url)

test('dash plugin forces buffered replacement when manually switching quality', async () => {
  const source = await readFile(dashPluginPath, 'utf8')

  assert.match(
    source,
    /setQualityFor\('video',\s*targetIndex,\s*true\)/
  )
})
