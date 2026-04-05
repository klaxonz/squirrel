import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => readFile(new URL(relativePath, import.meta.url), 'utf8')

test('frontend auth cutover removes token persistence and bearer injection', async () => {
  const axiosSource = await read('../src/utils/axios.ts')
  const userSource = await read('../src/composables/useUser.ts')
  const appSource = await read('../src/App.vue')
  const routerSource = await read('../src/router/index.ts')

  assert.match(axiosSource, /withCredentials:\s*true/)
  assert.doesNotMatch(axiosSource, /Authorization/)
  assert.doesNotMatch(userSource, /localStorage\.setItem\('token'/)
  assert.doesNotMatch(appSource, /localStorage\.getItem\('token'/)
  assert.doesNotMatch(routerSource, /localStorage\.getItem\('token'/)
  assert.match(userSource, /const hasResolvedAuth = ref\(false\)/)
  assert.match(userSource, /const result = \(await getUserMe\(\)\)/)
})
