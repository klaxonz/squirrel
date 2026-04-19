import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const dashPluginPath = new URL('../src/components/video-player/plugins/dash/DashPlugin.ts', import.meta.url)

test('dash plugin does not immediately reload the source for transient network or buffering errors', async () => {
  const source = await readFile(dashPluginPath, 'utf8')

  assert.match(source, /private isTransientDashError\(signature: string\): boolean \{/)
  assert.match(source, /'NETWORK'/)
  assert.match(source, /'STALL'/)
  assert.match(source, /Transient recovery handled without source reload/)
  assert.match(source, /return 'handled'/)
})
