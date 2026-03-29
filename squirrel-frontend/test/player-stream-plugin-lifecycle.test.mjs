import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const dashPluginPath = new URL('../src/components/video-player/plugins/dash/DashPlugin.ts', import.meta.url)
const hlsPluginPath = new URL('../src/components/video-player/plugins/hls/HlsPlugin.ts', import.meta.url)

const extractMethodBody = (source, signature) => {
  const start = source.indexOf(signature)
  assert.notEqual(start, -1, `expected to find method signature: ${signature}`)

  const bodyStart = source.indexOf('{', start)
  assert.notEqual(bodyStart, -1, `expected to find method body: ${signature}`)

  let depth = 0
  for (let index = bodyStart; index < source.length; index += 1) {
    const char = source[index]
    if (char === '{') depth += 1
    if (char === '}') {
      depth -= 1
      if (depth === 0) {
        return source.slice(bodyStart + 1, index)
      }
    }
  }

  assert.fail(`expected to find complete method body: ${signature}`)
}

test('dash plugin keeps its context when the current source is not dash', async () => {
  const source = await readFile(dashPluginPath, 'utf8')
  const body = extractMethodBody(source, 'onSourceChange(source: MediaSource): void')

  assert.match(body, /if\s*\(!isDash\)\s*\{/)
  assert.doesNotMatch(body, /if\s*\(!isDash\)\s*\{[\s\S]*?this\.destroy\(\)/)
})

test('hls plugin keeps its context when the current source is not hls', async () => {
  const source = await readFile(hlsPluginPath, 'utf8')
  const body = extractMethodBody(source, 'onSourceChange(source: MediaSource): void')

  assert.match(body, /if\s*\(!isHls\)\s*\{/)
  assert.doesNotMatch(body, /if\s*\(!isHls\)\s*\{[\s\S]*?this\.destroy\(\)/)
})
