import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const videoPlayPath = resolve(process.cwd(), 'src/views/VideoPlay.vue')
const videoPlaySource = readFileSync(videoPlayPath, 'utf8')

test('video play view reuses the shared SubscriptionAvatar for channel fallbacks', () => {
  assert.match(videoPlaySource, /import SubscriptionAvatar from ['"]@\/components\/common\/SubscriptionAvatar\.vue['"]/)
  assert.match(videoPlaySource, /<SubscriptionAvatar[\s\S]*?class="video-channel__avatar"/)
  assert.doesNotMatch(videoPlaySource, /<img[\s\S]*?class="video-channel__avatar"/)
})
