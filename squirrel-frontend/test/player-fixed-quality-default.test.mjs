import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const usePlayerPath = new URL('../src/components/video-player/runtime/usePlayer.ts', import.meta.url)

test('usePlayer keeps automatic quality fallback disabled', async () => {
  const source = await readFile(usePlayerPath, 'utf8')

  assert.match(
    source,
    /errorRecovery:\s*\{\s*enableQualityFallback:\s*false,\s*\}/s
  )
})
