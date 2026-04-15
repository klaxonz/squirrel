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

test('hls plugin uses stable quality ids instead of exposing raw level indexes', async () => {
  const source = await readFile(hlsPluginPath, 'utf8')

  assert.match(source, /private qualityIdByLevelIndex = new Map<number, string>\(\)/)
  assert.match(source, /private levelIndexByQualityId = new Map<string, number>\(\)/)
  assert.match(source, /private sourceQualityHints: QualityLevel\[\] = \[\]/)
  assert.match(source, /private currentQualities: QualityLevel\[\] = \[\]/)
  assert.match(source, /private buildStableQualityId\(level: Level, index: number\): string/)
  assert.match(source, /const hintedLevels = this\.matchHintedLevels\(levels\)/)
  assert.match(source, /private buildHintedQualities\(\): QualityLevel\[\]/)
  assert.match(source, /runtimeSelection:\s*\{\s*kind:\s*'hls-level',\s*levelIndex\s*\}/)
  assert.match(source, /const currentQuality = this\.findQualityForLevel\(data\.level\)/)
  assert.match(source, /this\.context\?\.registerCurrentQualityId\?\.\(qualityId\)/)
  assert.match(source, /this\.context\?\.emit\('qualitychange',\s*\{\s*quality,\s*auto:\s*this\.hls\?\.autoLevelEnabled \?\? false,\s*id:\s*qualityId/s)
  assert.match(source, /this\.sourceQualityHints = Array\.isArray\(source\.qualities\) \? source\.qualities : \[\]/)
  assert.match(source, /const hintedQualities = this\.buildHintedQualities\(\)/)
  assert.match(source, /this\.context\.setQuality\(qualities\[0\]\.id \?\? qualities\[0\]\.label\)/)
  assert.match(source, /const matchedLevelIndex = this\.levelIndexByQualityId\.get\(quality\)/)
})
