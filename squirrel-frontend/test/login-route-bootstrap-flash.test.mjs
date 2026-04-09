import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const mainPath = new URL('../src/main.ts', import.meta.url)

test('frontend waits for the initial router navigation before mounting to avoid auth page shell flashes', async () => {
  const source = await readFile(mainPath, 'utf8')

  assert.match(source, /const bootstrap = async \(\) => \{/)
  assert.match(source, /app\.use\(router\)/)
  assert.match(source, /await router\.isReady\(\)/)
  assert.match(source, /app\.mount\('#app'\)/)

  const routerReadyIndex = source.indexOf('await router.isReady()')
  const mountIndex = source.indexOf("app.mount('#app')")

  assert.notStrictEqual(routerReadyIndex, -1)
  assert.notStrictEqual(mountIndex, -1)
  assert.ok(routerReadyIndex < mountIndex, 'router readiness should resolve before mounting the app')
})
