import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('import subscription dialog uses configured site icons for supported sites', async () => {
  const source = await read('../src/components/dialogs/ImportSubscriptionDialog.vue')

  assert.match(source, /<SiteIcon/)
  assert.match(source, /useSiteCatalog/)
  assert.match(source, /:icon-url="getSiteIconUrl\(site\)"/)
  assert.match(source, /await loadCatalog\(\)/)
})
