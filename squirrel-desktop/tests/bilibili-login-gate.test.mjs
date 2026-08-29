import assert from 'node:assert/strict'
import test from 'node:test'
import { isBilibiliLoginGated } from '../src/playback/providers/bilibili/index.mjs'

test('anonymous session on an HD video is flagged as login-gated', () => {
  const playData = {
    quality: 64,
    support_formats: [
      { quality: 116, new_description: '1080P 60帧' },
      { quality: 80, new_description: '1080P 高清' },
      { quality: 64, new_description: '720P 准高清' },
    ],
  }
  assert.equal(isBilibiliLoginGated(playData), true)
})

test('logged-in session with full grant is not flagged', () => {
  const playData = {
    quality: 116,
    support_formats: [
      { quality: 116, new_description: '1080P 60帧' },
      { quality: 80, new_description: '1080P 高清' },
    ],
  }
  assert.equal(isBilibiliLoginGated(playData), false)
})

test('native-low video granting its own top format is not flagged', () => {
  const playData = {
    quality: 32,
    support_formats: [
      { quality: 32, new_description: '480P 标清' },
      { quality: 16, new_description: '360P 流畅' },
    ],
  }
  assert.equal(isBilibiliLoginGated(playData), false)
})

test('logged-in session is not flagged for VIP-only tiers above the grant', () => {
  const playData = {
    quality: 116,
    support_formats: [
      { quality: 126, new_description: '4K' },
      { quality: 116, new_description: '1080P 60帧' },
    ],
  }
  assert.equal(isBilibiliLoginGated(playData, { loggedIn: true }), false)
})

test('anonymous session with VIP-only tiers above the grant is still flagged', () => {
  const playData = {
    quality: 116,
    support_formats: [
      { quality: 126, new_description: '4K' },
      { quality: 116, new_description: '1080P 60帧' },
    ],
  }
  assert.equal(isBilibiliLoginGated(playData), true)
})

test('missing quality fields are not flagged', () => {
  assert.equal(isBilibiliLoginGated({}), false)
  assert.equal(isBilibiliLoginGated(null), false)
  assert.equal(isBilibiliLoginGated({ quality: 0, support_formats: [] }), false)
})
