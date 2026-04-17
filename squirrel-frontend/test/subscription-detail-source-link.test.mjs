import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const filePath = new URL('../src/components/feed/ChannelHeader.vue', import.meta.url)

test('subscription detail header makes avatar and title link to the source site', async () => {
  const source = await readFile(filePath, 'utf8')

  assert.match(source, /class="avatar-frame avatar-frame--link"/)
  assert.match(source, /class="channel-title-link"/)
  assert.match(source, /target="_blank"/)
  assert.match(source, /rel="noopener noreferrer"/)
  assert.match(source, /:href="detail\.url"/)
  assert.doesNotMatch(source, /打开源站/)
})
