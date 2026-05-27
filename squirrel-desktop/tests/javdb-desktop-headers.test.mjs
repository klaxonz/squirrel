import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const mainPath = new URL('../src/main.mjs', import.meta.url)

test('desktop javdb playback registers media headers for resolved missav stream host', async () => {
  const source = await readFile(mainPath, 'utf8')

  assert.match(source, /const missavMediaHeaderRules = new Map\(\)/)
  assert.match(source, /const registerMissavMediaHeaders = \(streamUrl, referer\) => \{[\s\S]*?isMissavDocumentTarget\(normalizedReferer\)/)
  assert.match(source, /missavMediaHeaderRules\.set\(streamHost, \{[\s\S]*?Referer: normalizedReferer[\s\S]*?Origin: refererOrigin/)
  assert.match(source, /const missavHeaders = missavMediaHeaderRules\.get\(hostname\)[\s\S]*?return \{ hosts: \[hostname\], headers: missavHeaders \}/)
  assert.match(source, /const payload = await resolveJavdbPlayback\(normalizedUrl,[\s\S]*?registerMissavMediaHeaders\(payload\?\.video_url, payload\?\.metadata\?\.referer\)[\s\S]*?return payload/)
})
