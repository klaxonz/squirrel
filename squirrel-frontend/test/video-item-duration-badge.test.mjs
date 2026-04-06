import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const filePath = new URL('../src/components/feed/VideoItem.vue', import.meta.url)

test('video item renders duration as a standalone always-visible badge', async () => {
  const source = await readFile(filePath, 'utf8')

  assert.ok(source.includes('class="video-duration-badge"'))
  assert.ok(source.includes('{{ formatDuration(video.duration) }}'))
  assert.ok(!source.includes('<div class="tech-time">{{ formatDuration(video.duration) }}</div>'))
  assert.match(source, /\.video-duration-badge\s*\{[\s\S]*position:\s*absolute;[\s\S]*z-index:\s*6;/)
  assert.doesNotMatch(
    source,
    /\.video-terminal-item:hover \.video-duration-badge\s*\{[\s\S]*opacity\s*:/,
  )
})
