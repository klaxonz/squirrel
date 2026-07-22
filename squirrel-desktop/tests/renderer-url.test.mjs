import assert from 'node:assert/strict'
import test from 'node:test'
import { resolveDesktopRendererUrl } from '../src/renderer-url.mjs'

test('unpackaged desktop always uses Vite instead of a stale built renderer', () => {
  assert.equal(
    resolveDesktopRendererUrl({
      configuredUrl: '',
      isPackaged: false,
      packagedRendererUrl: 'file:///app/renderer/dist/index.html',
      devRendererUrl: 'http://127.0.0.1:5174/',
    }),
    'http://127.0.0.1:5174/',
  )
})

test('packaged desktop uses the shipped renderer unless explicitly configured', () => {
  assert.equal(
    resolveDesktopRendererUrl({
      configuredUrl: '',
      isPackaged: true,
      packagedRendererUrl: 'file:///app/renderer/dist/index.html',
      devRendererUrl: 'http://127.0.0.1:5174/',
    }),
    'file:///app/renderer/dist/index.html',
  )

  assert.equal(
    resolveDesktopRendererUrl({
      configuredUrl: 'http://localhost:4173',
      isPackaged: true,
      packagedRendererUrl: 'file:///app/renderer/dist/index.html',
      devRendererUrl: 'http://127.0.0.1:5174/',
    }),
    'http://localhost:4173/',
  )
})
