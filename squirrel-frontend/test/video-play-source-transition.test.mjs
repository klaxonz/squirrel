import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const orchestratorPath = new URL('../src/composables/usePlaybackOrchestrator.ts', import.meta.url)

test('playback orchestrator clears the previous video snapshot before resolving a different route video without seed data', async () => {
  const source = await readFile(orchestratorPath, 'utf8')

  assert.match(source, /const currentVideoId = video\.value && \(video\.value as any\)\.id != null\s*\? String\(\(video\.value as any\)\.id\) : ''/)
  assert.match(source, /const targetVideoId = String\(videoId\)/)
  assert.match(source, /if \(!initialVideoData && currentVideoId && currentVideoId !== targetVideoId\) \{\s*setVideoSnapshot\(null\)\s*\}/)
  assert.match(source, /const v: any = video\.value \|\| initialVideoData \|\| \{\}/)
})
