import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('unsubscribe actions broadcast subscription removal events', async () => {
  const channelHeader = await read('../src/components/feed/ChannelHeader.vue')
  const subscribed = await read('../src/views/Subscribed.vue')
  const videoPlay = await read('../src/views/VideoPlay.vue')

  assert.match(channelHeader, /import \{ notifySubscriptionRemoved \} from ['"]@\/utils\/subscriptionEvents['"]/)
  assert.match(channelHeader, /notifySubscriptionRemoved\(props\.subscriptionId\)/)
  assert.match(subscribed, /import \{ notifySubscriptionRemoved \} from ['"]@\/utils\/subscriptionEvents['"]/)
  assert.match(subscribed, /notifySubscriptionRemoved\(subscriptionId\)/)
  assert.match(videoPlay, /import \{ notifySubscriptionRemoved \} from ['"]@\/utils\/subscriptionEvents['"]/)
  assert.match(videoPlay, /notifySubscriptionRemoved\(subscriptionId\)/)
})

test('latest video list jumps away from removed channel without refreshing', async () => {
  const source = await read('../src/views/LatestVideos.vue')

  assert.match(source, /import \{ onSubscriptionRemoved \} from ['"]@\/utils\/subscriptionEvents['"]/)
  assert.match(source, /stopSubscriptionRemovedListener = onSubscriptionRemoved/)
  assert.match(source, /router\.replace\(\{ name: 'AllVideos' \}\)/)
  assert.doesNotMatch(source, /needsSubscriptionRefresh/)
  assert.doesNotMatch(source, /refreshAfterSubscriptionRemoved/)
  assert.doesNotMatch(source, /router\.replace\(\{ name: 'AllVideos' \}\)\.then/)
})
