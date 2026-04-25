import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const operationsPath = new URL('../src/composables/useVideoOperations.ts', import.meta.url)

test('desktop playback does not force local DASH blob manifests through shaka', async () => {
  const source = await readFile(operationsPath, 'utf8')

  assert.match(source, /key: 'resolveYouTubePlayback'[\s\S]*?matches: \(url\) => includesAny\(url, \['youtube\.com\/', 'youtu\.be\/'\]\)/)
  assert.match(source, /key: 'resolveBilibiliPlayback'[\s\S]*?matches: \(url\) => includesAny\(url, \['bilibili\.com\/video\/', 'b23\.tv\/'\]\)/)
  assert.doesNotMatch(source, /prefersShaka/)
  assert.doesNotMatch(source, /playbackEngine:\s*'shaka'/)
})
