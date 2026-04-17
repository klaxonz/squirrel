import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const enginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)
const runtimePath = new URL('../src/components/video-player/runtime/usePlayer.ts', import.meta.url)

test('player keeps source switches in loading until the current media source is ready', async () => {
  const source = await readFile(enginePath, 'utf8')

  assert.match(source, /let mediaLoadStartedForCurrentSource = false/)
  assert.match(source, /let mediaMetadataLoadedForCurrentSource = false/)
  assert.match(source, /const markSourceLoadingStarted = \(\): void => \{[\s\S]*loading = true[\s\S]*mediaLoadStartedForCurrentSource = false[\s\S]*mediaMetadataLoadedForCurrentSource = false[\s\S]*events\.emit\('loadsstart', undefined\)/)
  assert.match(source, /const canAcceptNativeCanPlay = \(\): boolean => \{[\s\S]*if \(!isNativeMediaSourceCurrent\(\)\) return false[\s\S]*return mediaLoadStartedForCurrentSource && mediaMetadataLoadedForCurrentSource/)
  assert.match(source, /const onCanPlay = \(\) => \{[\s\S]*if \(!canAcceptNativeCanPlay\(\)\) return[\s\S]*loading = false/)
  assert.match(source, /video\.addEventListener\('loadstart', onLoadStart\)/)
  assert.match(source, /video\.addEventListener\('loadeddata', onLoadedData\)/)
})

test('runtime shows the loading overlay again when a source load starts', async () => {
  const source = await readFile(runtimePath, 'utf8')

  assert.match(source, /engine\.on\('loadsstart', \(\) => \{[\s\S]*store\.setCanPlay\('video', false\)[\s\S]*store\.setLoading\(true, 'fetching'\)/)
})
