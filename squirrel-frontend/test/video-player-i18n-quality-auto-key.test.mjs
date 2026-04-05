import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const localeTypePath = new URL('../src/components/video-player/i18n/types.ts', import.meta.url)
const zhPath = new URL('../src/components/video-player/i18n/zh-CN.ts', import.meta.url)
const enPath = new URL('../src/components/video-player/i18n/en-US.ts', import.meta.url)
const jaPath = new URL('../src/components/video-player/i18n/ja-JP.ts', import.meta.url)

test('video player i18n no longer defines unused quality or codec auto labels', async () => {
  const [typesSource, zhSource, enSource, jaSource] = await Promise.all([
    readFile(localeTypePath, 'utf8'),
    readFile(zhPath, 'utf8'),
    readFile(enPath, 'utf8'),
    readFile(jaPath, 'utf8')
  ])

  assert.doesNotMatch(typesSource, /qualityAuto:\s*string/)
  assert.doesNotMatch(typesSource, /codecAuto:\s*string/)
  assert.doesNotMatch(zhSource, /qualityAuto:\s*'自动'/)
  assert.doesNotMatch(zhSource, /codecAuto:\s*'自动选择'/)
  assert.doesNotMatch(enSource, /qualityAuto:\s*'Auto'/)
  assert.doesNotMatch(enSource, /codecAuto:\s*'Auto select'/)
  assert.doesNotMatch(jaSource, /qualityAuto:\s*'自動'/)
  assert.doesNotMatch(jaSource, /codecAuto:\s*'自動選択'/)
})
