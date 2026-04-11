import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('subscribed view shows a subscription skeleton before the first page arrives', async () => {
  const source = await read('../src/views/Subscribed.vue')

  assert.match(source, /import SubscriptionSkeleton from ['"]@\/components\/feed\/SubscriptionSkeleton\.vue['"]/)
  assert.match(source, /<div v-if="loading && !subscriptions\.length" key="skeleton" class="subscription-list subscription-list--loading">/)
  assert.match(source, /<SubscriptionSkeleton v-for="i in 14" :key="i" :delay="i \* 70" \/>/)
  assert.match(source, /\.subscription-list--loading\s*\{[\s\S]*min-height:\s*calc\(100dvh - 12rem\);/)
})

test('subscribed view still shows an inline loading indicator while refreshing an existing list', async () => {
  const source = await read('../src/views/Subscribed.vue')

  assert.match(source, /<div v-if="loading && subscriptions\.length" class="subscribed-inline-loading">/)
  assert.match(source, /<LoadingIndicator :loading="true" text="正在加载订阅" size="sm" \/>/)
  assert.match(source, /\.subscribed-inline-loading\s*\{[\s\S]*position:\s*sticky;/)
})

test('subscription skeleton uses the same theme-aware loading palette as the history page', async () => {
  const source = await read('../src/components/feed/SubscriptionSkeleton.vue')

  assert.match(source, /:style="\{ animationDelay: `\$\{delay\}ms`, '--skeleton-delay': `\$\{delay\}ms` \}"/)
  assert.match(source, /class="skeleton-avatar skeleton-surface"/)
  assert.match(source, /\.skeleton-surface::after\s*\{[\s\S]*animation:\s*shimmer 1\.6s ease-in-out infinite;/)
  assert.match(source, /background:\s*hsl\(var\(--secondary\) \/ 0\.25\);/)
  assert.match(source, /border:\s*1px solid hsl\(var\(--border\) \/ 0\.3\);/)
  assert.match(source, /background:\s*hsl\(var\(--secondary\) \/ 0\.2\);/)
  assert.match(source, /hsl\(var\(--primary\) \/ 0\.03\)/)
})
