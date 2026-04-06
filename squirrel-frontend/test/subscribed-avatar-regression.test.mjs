import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const subscribedViewPath = resolve(process.cwd(), 'src/views/Subscribed.vue')
const subscribedViewSource = readFileSync(subscribedViewPath, 'utf8')

test('subscribed view reuses the shared SubscriptionAvatar for subscription fallbacks', () => {
  assert.match(subscribedViewSource, /import SubscriptionAvatar from ['"]@\/components\/common\/SubscriptionAvatar\.vue['"]/)
  assert.match(subscribedViewSource, /<SubscriptionAvatar[\s\S]*?class="subscription-row__avatar"/)
  assert.match(subscribedViewSource, /<SubscriptionAvatar[\s\S]*?class="subscription-dialog__avatar"/)
})
