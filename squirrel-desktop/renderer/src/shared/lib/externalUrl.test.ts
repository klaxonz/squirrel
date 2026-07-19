// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'
import { normalizeHttpUrl } from './externalUrl'

describe('normalizeHttpUrl', () => {
  it('accepts only absolute HTTP and HTTPS URLs', () => {
    expect(normalizeHttpUrl('https://example.com/post')).toBe('https://example.com/post')
    expect(normalizeHttpUrl('http://example.com')).toBe('http://example.com/')
    expect(normalizeHttpUrl('javascript:alert(1)')).toBeNull()
    expect(normalizeHttpUrl('file:///etc/passwd')).toBeNull()
    expect(normalizeHttpUrl('/relative')).toBeNull()
    expect(normalizeHttpUrl('')).toBeNull()
  })
})
