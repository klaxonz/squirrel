import test from 'node:test'
import assert from 'node:assert/strict'

import {
  getLoginStatusBadge,
  mergeLoginStatusResult,
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
      label: '缺失',
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
      label: '错误',
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
      label: '已拦截',
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
      label: '有效',
      title: '已登录',
    },
  )
})

test('maps explicit logged-out statuses to Logged Out instead of Invalid', () => {
  assert.deepEqual(
    getLoginStatusBadge({
      logged_in: false,
      message: '未登录，当前 Cookie 被站点识别为游客态',
      supported: true,
    }),
    {
      tone: 'warning',
      label: '未登录',
      title: '未登录，当前 Cookie 被站点识别为游客态',
    },
  )
})

test('marks all-site cookie imports for status refresh', () => {
  assert.equal(shouldRefreshLoginStatusesAfterCookieImport({ sites: { youtube: { cookies: 10 } } }), true)
  assert.equal(shouldRefreshLoginStatusesAfterCookieImport({}), false)
})

test('keeps previous valid login status when a transient check failure arrives', () => {
  assert.deepEqual(
    mergeLoginStatusResult(
      {
        logged_in: true,
        message: '已登录',
        supported: true,
      },
      {
        logged_in: false,
        message: '检测失败: 返回内容显示为站点错误页',
        supported: true,
        extra: { transient_failure: true },
      },
    ),
    {
      logged_in: true,
      message: '已登录',
      supported: true,
    },
  )
})

test('accepts explicit logged-out results instead of preserving a stale valid status', () => {
  assert.deepEqual(
    mergeLoginStatusResult(
      {
        logged_in: true,
        message: '已登录',
        supported: true,
      },
      {
        logged_in: false,
        message: '被重定向到登录页',
        supported: true,
      },
    ),
    {
      logged_in: false,
      message: '被重定向到登录页',
      supported: true,
    },
  )
})
