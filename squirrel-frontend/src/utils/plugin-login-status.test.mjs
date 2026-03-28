import test from 'node:test'
import assert from 'node:assert/strict'

import {
  getLoginStatusBadge,
  shouldRefreshLoginStatusesAfterCookieImport,
} from './plugin-login-status.js'

test('maps missing cookie status to Missing instead of Expired', () => {
  assert.deepEqual(
    getLoginStatusBadge({
      logged_in: false,
      message: 'cookies.txt 中未找到 YouTube 条目',
      supported: true,
    }),
    {
      tone: 'warning',
      label: 'Missing',
      title: 'cookies.txt 中未找到 YouTube 条目',
    },
  )
})

test('maps request failures to Error instead of Expired', () => {
  assert.deepEqual(
    getLoginStatusBadge({
      logged_in: false,
      message: '请求失败: timeout',
      supported: true,
    }),
    {
      tone: 'danger',
      label: 'Error',
      title: '请求失败: timeout',
    },
  )
})

test('maps challenge-style statuses to Blocked', () => {
  assert.deepEqual(
    getLoginStatusBadge({
      logged_in: false,
      message: '需要登录或通过风控校验后才能播放',
      supported: true,
    }),
    {
      tone: 'danger',
      label: 'Blocked',
      title: '需要登录或通过风控校验后才能播放',
    },
  )
})

test('keeps logged-in statuses as Valid', () => {
  assert.deepEqual(
    getLoginStatusBadge({
      logged_in: true,
      message: '已登录',
      supported: true,
    }),
    {
      tone: 'success',
      label: 'Valid',
      title: '已登录',
    },
  )
})

test('marks all-site cookie imports for status refresh', () => {
  assert.equal(shouldRefreshLoginStatusesAfterCookieImport({ sites: { youtube: { cookies: 10 } } }), true)
  assert.equal(shouldRefreshLoginStatusesAfterCookieImport({}), false)
})
