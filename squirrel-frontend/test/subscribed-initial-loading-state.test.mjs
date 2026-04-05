import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('subscribed view keeps empty state hidden until first load finishes', async () => {
  const source = await read('../src/views/Subscribed.vue')

  assert.match(source, /const hasLoadedOnce = ref\(false\)/)
  assert.match(source, /v-else-if="hasLoadedOnce && !loading && !subscriptions\.length"/)
  assert.match(source, /hasLoadedOnce\.value = true/)
})

test('subscribed view resets first-load guard before refetching the list', async () => {
  const source = await read('../src/views/Subscribed.vue')

  assert.match(source, /const resetSubscriptionList = \(\) => \{[\s\S]*?hasLoadedOnce\.value = false/)
  assert.match(source, /const handleGlobalSearch = \(query\) => \{[\s\S]*?resetSubscriptionList\(\)[\s\S]*?loadSubscriptions\(\)/)
  assert.match(source, /watch\(\[nsfw, site\], async \(\) => \{[\s\S]*?resetSubscriptionList\(\)[\s\S]*?await loadSubscriptions\(\)/)
  assert.match(source, /const handleChannelAdded = \(\) => \{[\s\S]*?resetSubscriptionList\(\)[\s\S]*?loadSubscriptions\(\)/)
  assert.match(source, /const handleSubscriptionsImported = \(\) => \{[\s\S]*?resetSubscriptionList\(\)[\s\S]*?loadSubscriptions\(\)/)
})

test('subscribed view swaps between empty and skeleton without out-in transition lag', async () => {
  const source = await read('../src/views/Subscribed.vue')

  assert.doesNotMatch(source, /<Transition name="fade-list" mode="out-in">/)
  assert.match(source, /<Transition name="fade-list">/)
})
