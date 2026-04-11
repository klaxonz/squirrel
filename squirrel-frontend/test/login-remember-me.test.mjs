import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => readFile(new URL(relativePath, import.meta.url), 'utf8')

test('login view exposes remember-me toggle and forwards it to the backend payload', async () => {
  const loginSource = await read('../src/views/Login.vue')

  assert.match(loginSource, /记住登录/)
  assert.match(loginSource, /rememberMe:\s*false/)
  assert.match(loginSource, /remember_me:\s*form\.value\.rememberMe/)
  assert.doesNotMatch(loginSource, /在当前浏览器保留 30 天登录状态/)
})
