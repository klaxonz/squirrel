import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('import subscription api forwards preview cursor payload and batch size params', async () => {
  const source = await read('../src/api/subscription.ts')

  assert.match(source, /export const previewImportSubscriptions = async \(/)
  assert.match(source, /options: \{ cursorPayload\?: Record<string, unknown> \| null, limit\?: number \} = \{\}/)
  assert.match(source, /params\.cursor = JSON\.stringify\(options\.cursorPayload\)/)
  assert.match(source, /params\.limit = options\.limit/)
  assert.match(source, /return get\(`\/api\/subscription\/import\/\$\{site\}\/preview`, params\)/)
})

test('import subscription dialog fetches preview batches and exposes load-more flow', async () => {
  const source = await read('../src/components/dialogs/ImportSubscriptionDialog.vue')

  assert.match(source, /const PREVIEW_BATCH_SIZE = 50/)
  assert.match(source, /const loadingPreview = ref\(false\)/)
  assert.match(source, /const loadingMorePreview = ref\(false\)/)
  assert.match(source, /const fetchPreviewBatch = async \(\{ cursorPayload = null, append = false \} = \{\}\) =>/)
  assert.match(source, /const result = await previewImportSubscriptions\(selectedSite\.value, \{/)
  assert.match(source, /cursorPayload,/)
  assert.match(source, /limit: PREVIEW_BATCH_SIZE,/)
  assert.match(source, /const loadingState = append \? loadingMorePreview : loadingPreview/)
  assert.match(source, /loadingState\.value = true/)
  assert.match(source, /loadingState\.value = false/)
  assert.match(source, /subscriptions: append\s*\?[\s\S]*mergePreviewSubscriptions/)
  assert.match(source, /const loadMorePreview = async \(\) =>/)
  assert.match(source, /cursorPayload: previewData\.value\.cursor_payload,/)
  assert.match(source, /v-if="loadingPreview && !loadedCount"/)
  assert.match(source, /v-else/)
  assert.match(source, /v-if="previewData\.has_more"/)
  assert.match(source, /:disabled="loadingMorePreview"/)
  assert.match(source, /<Loader2 v-if="loadingMorePreview"/)
  assert.match(source, /@click="loadMorePreview"/)
})

test('import subscription dialog only imports currently selected urls', async () => {
  const source = await read('../src/components/dialogs/ImportSubscriptionDialog.vue')

  assert.match(source, /const subscriptionUrls = Object\.keys\(selectedUrlMap\.value \|\| \{\}\)/)
  assert.match(source, /const result = await importSubscriptions\(selectedSite\.value, subscriptionUrls\)/)
  assert.match(source, /全选已加载未导入/)
  assert.match(source, /已加载 {{ loadedCount }} \/ {{ previewData\.total \?\? '未知' }} 个/)
})
