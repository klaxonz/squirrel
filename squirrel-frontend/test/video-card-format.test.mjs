import test from 'node:test'
import assert from 'node:assert/strict'

import { formatVideoCardId } from '../src/utils/videoCard.js'

test('formatVideoCardId formats numeric ids without throwing', () => {
  assert.equal(formatVideoCardId(123456), '3456')
})

test('formatVideoCardId keeps the last four chars of string ids and uppercases them', () => {
  assert.equal(formatVideoCardId('ab12cd34'), 'CD34')
})

test('formatVideoCardId supports short display tokens for numeric ids', () => {
  assert.equal(formatVideoCardId(123456, { length: 2, placeholder: '--' }), '56')
})

test('formatVideoCardId returns placeholder for empty ids', () => {
  assert.equal(formatVideoCardId(null), '----')
})
