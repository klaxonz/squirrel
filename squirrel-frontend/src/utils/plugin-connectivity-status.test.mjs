import test from 'node:test'
import assert from 'node:assert/strict'

import { getConnectivityBadge } from './plugin-connectivity-status.js'

test('maps successful connectivity checks to Pass', () => {
  assert.deepEqual(
    getConnectivityBadge({ accessible: true, status: 'success' }),
    {
      tone: 'success',
      label: 'Pass',
      title: 'Site is accessible',
    },
  )
})

test('maps restricted connectivity checks to Restricted instead of Pass', () => {
  assert.deepEqual(
    getConnectivityBadge({
      accessible: true,
      status: 'restricted',
      error_message: '站点响应限制HTTP状态码: 403',
    }),
    {
      tone: 'warning',
      label: 'Restricted',
      title: '站点响应限制HTTP状态码: 403',
    },
  )
})

test('maps failed connectivity checks to Fail', () => {
  assert.deepEqual(
    getConnectivityBadge({
      accessible: false,
      status: 'failed',
      error_message: 'HTTP状态码: 500',
    }),
    {
      tone: 'danger',
      label: 'Fail',
      title: 'HTTP状态码: 500',
    },
  )
})
