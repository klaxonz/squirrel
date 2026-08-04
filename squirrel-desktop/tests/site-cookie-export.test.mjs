import assert from 'node:assert/strict'
import test from 'node:test'

import {
  NETSCAPE_HEADER,
  buildCookieUploadPayload,
  exportSiteCookiesToBackend,
  serializeCookiesToNetscape,
} from '../src/site-cookie-export.mjs'

const bilibiliSessionCookie = () => ({
  name: 'SESSDATA',
  value: 'abc123',
  domain: '.bilibili.com',
  path: '/',
  secure: true,
  httpOnly: true,
  expirationDate: 1710000000,
})

test('serializeCookiesToNetscape emits Netscape lines with HttpOnly prefix and header', () => {
  const text = serializeCookiesToNetscape([bilibiliSessionCookie()])
  const lines = text.split('\n')
  assert.equal(lines[0], NETSCAPE_HEADER)
  assert.equal(lines[1], '#HttpOnly_.bilibili.com\tTRUE\t/\tTRUE\t1710000000\tSESSDATA\tabc123')
})

test('serializeCookiesToNetscape normalizes domain, flags, and session expiry', () => {
  const cookies = [
    { name: 'bili_jct', value: 'x', domain: 'bilibili.com', path: '/', secure: false, httpOnly: false, expirationDate: 1710000123 },
    { name: 'sessionOnly', value: 'y', domain: 'passport.bilibili.com', path: '/', secure: false, httpOnly: false },
  ]
  const lines = serializeCookiesToNetscape(cookies).split('\n')
  assert.equal(lines[1], 'bilibili.com\tFALSE\t/\tFALSE\t1710000123\tbili_jct\tx')
  // host-only cookie: no leading dot -> FALSE; no expirationDate -> expires 0
  assert.equal(lines[2], 'passport.bilibili.com\tFALSE\t/\tFALSE\t0\tsessionOnly\ty')
})

test('serializeCookiesToNetscape skips nameless cookies', () => {
  const text = serializeCookiesToNetscape([
    { name: '', value: 'v', domain: 'bilibili.com' },
    { name: 'ok', value: '', domain: 'bilibili.com' },
  ])
  assert.equal(text, NETSCAPE_HEADER)
})

test('buildCookieUploadPayload builds bilibili.txt payload with count', () => {
  const payload = buildCookieUploadPayload('bilibili', [bilibiliSessionCookie()])
  assert.equal(payload.fileName, 'bilibili.txt')
  assert.equal(payload.count, 1)
  assert.ok(payload.text.includes('#HttpOnly_.bilibili.com'))
})

test('exportSiteCookiesToBackend refuses without server url (no fetch)', async () => {
  let called = false
  const result = await exportSiteCookiesToBackend({
    siteName: 'bilibili',
    cookies: [bilibiliSessionCookie()],
    serverUrl: '',
    fetchImpl: async () => { called = true },
  })
  assert.equal(result.ok, false)
  assert.equal(result.reason, 'no-server-or-site')
  assert.equal(called, false)
})

test('exportSiteCookiesToBackend refuses with no cookies (no fetch)', async () => {
  let called = false
  const result = await exportSiteCookiesToBackend({
    siteName: 'bilibili',
    cookies: [],
    serverUrl: 'http://127.0.0.1:8001',
    fetchImpl: async () => { called = true },
  })
  assert.equal(result.ok, false)
  assert.equal(result.reason, 'no-cookies')
  assert.equal(called, false)
})

test('exportSiteCookiesToBackend posts multipart file and parses success', async () => {
  let capturedUrl = ''
  let capturedOptions = null
  const fetchImpl = async (url, options) => {
    capturedUrl = url
    capturedOptions = options
    return {
      ok: true,
      json: async () => ({ code: 0, msg: 'cookies updated', data: { site_name: 'bilibili', bytes: 42 } }),
    }
  }

  const result = await exportSiteCookiesToBackend({
    siteName: 'bilibili',
    cookies: [bilibiliSessionCookie()],
    serverUrl: 'http://127.0.0.1:8001/',
    fetchImpl,
  })

  assert.equal(capturedUrl, 'http://127.0.0.1:8001/api/site-cookies/bilibili')
  assert.equal(capturedOptions.method, 'POST')
  assert.ok(capturedOptions.body instanceof FormData)
  const file = capturedOptions.body.get('file')
  assert.ok(file instanceof Blob)
  assert.equal(file.name, 'bilibili.txt')
  assert.ok((await file.text()).includes('#HttpOnly_.bilibili.com'))
  assert.deepEqual(result, {
    ok: true,
    message: 'cookies updated',
    data: { site_name: 'bilibili', bytes: 42 },
    count: 1,
  })
})

test('exportSiteCookiesToBackend maps http errors', async () => {
  const result = await exportSiteCookiesToBackend({
    siteName: 'bilibili',
    cookies: [bilibiliSessionCookie()],
    serverUrl: 'http://127.0.0.1:8001',
    fetchImpl: async () => ({ ok: false, status: 401, json: async () => ({ code: 401, msg: '请先登录' }) }),
  })
  assert.equal(result.ok, false)
  assert.equal(result.reason, 'http-error')
  assert.equal(result.status, 401)
  assert.equal(result.message, '请先登录')
})

test('exportSiteCookiesToBackend maps api error codes', async () => {
  const result = await exportSiteCookiesToBackend({
    siteName: 'bilibili',
    cookies: [bilibiliSessionCookie()],
    serverUrl: 'http://127.0.0.1:8001',
    fetchImpl: async () => ({ ok: true, json: async () => ({ code: 1, msg: 'no cookie entries matched the site domain' }) }),
  })
  assert.equal(result.ok, false)
  assert.equal(result.reason, 'api-error')
  assert.equal(result.message, 'no cookie entries matched the site domain')
})

test('exportSiteCookiesToBackend maps network failures non-destructively', async () => {
  const result = await exportSiteCookiesToBackend({
    siteName: 'bilibili',
    cookies: [bilibiliSessionCookie()],
    serverUrl: 'http://127.0.0.1:8001',
    fetchImpl: async () => { throw new Error('ECONNREFUSED') },
  })
  assert.equal(result.ok, false)
  assert.equal(result.reason, 'network-error')
  assert.equal(result.message, 'ECONNREFUSED')
})
