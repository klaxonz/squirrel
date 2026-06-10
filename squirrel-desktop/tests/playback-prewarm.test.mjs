import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const playbackProvidersPath = new URL('../src/playback/providers/index.mjs', import.meta.url)

test('desktop playback prewarm registry includes javdb cloudflare prewarm', async () => {
  const source = await readFile(playbackProvidersPath, 'utf8')

  assert.match(source, /import \{ loadDocumentHtmlWithBrowserWindow \}/)
  assert.match(source, /import \{ prewarmJavdbCloudflare \}/)
  assert.match(source, /\{ name: 'javdb', prewarm: \(\) => prewarmJavdbCloudflare\(loadDocumentHtmlWithBrowserWindow\) \}/)
})
