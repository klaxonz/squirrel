import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const enginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)

test('player engine delegates retry recovery to the active stream controller before falling back', async () => {
  const source = await readFile(enginePath, 'utf8')

  assert.match(
    source,
    /recoverPlayback\(error,\s*\{/
  )

  assert.match(
    source,
    /if\s*\(recoveryAction === 'reload-source'\)\s*\{\s*return reloadCurrentSource\(\)/
  )
})

test('player engine routes plugin reported errors through the shared recovery flow', async () => {
  const source = await readFile(enginePath, 'utf8')

  assert.match(
    source,
    /reportError\(error\)\s*\{\s*void handleRecoveryError\(error\)/
  )
})
