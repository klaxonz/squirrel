import assert from 'node:assert/strict'
import test from 'node:test'
import {
  attachBackendSessionCookies,
  isConfiguredBackendApiUrl,
} from '../src/backend-auth-headers.mjs'

test('backend auth matching is restricted to the configured origin and API path', () => {
  const serverUrl = 'http://127.0.0.1:8001'

  assert.equal(isConfiguredBackendApiUrl('http://127.0.0.1:8001/api/users/me', serverUrl), true)
  assert.equal(isConfiguredBackendApiUrl('http://127.0.0.1:8001/health', serverUrl), false)
  assert.equal(isConfiguredBackendApiUrl('http://localhost:8001/api/users/me', serverUrl), false)
  assert.equal(isConfiguredBackendApiUrl('https://example.com/api/users/me', serverUrl), false)
})

test('backend session cookies replace stale request values without leaking duplicates', () => {
  assert.deepEqual(
    attachBackendSessionCookies(
      { cookie: 'theme=dark; squirrel_auth=stale', Accept: 'application/json' },
      'squirrel_auth=fresh; locale=zh-CN',
    ),
    {
      Accept: 'application/json',
      Cookie: 'theme=dark; squirrel_auth=fresh; locale=zh-CN',
    },
  )
})
