import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => {
  return readFile(new URL(relativePath, import.meta.url), 'utf8')
}

test('global search bar provides bilibili-style suggestion interactions', async () => {
  const source = await read('../src/components/layout/GlobalSearchBar.vue')

  assert.match(source, /SEARCH_HISTORY_STORAGE_KEY = 'global-search-history'/)
  assert.match(source, /getSearchSuggestions/)
  assert.match(source, /@keydown\.down\.prevent="moveActiveSuggestion\(1\)"/)
  assert.match(source, /@keydown\.up\.prevent="moveActiveSuggestion\(-1\)"/)
  assert.match(source, /class="search-suggestions"/)
  assert.match(source, /'猜你想搜'/)
  assert.match(source, /showSearchFallback/)
  assert.match(source, /clearRecentSearches/)
  assert.doesNotMatch(source, /id: `search-\$\{directSearchValue\}`/)
})

test('global search exposes route-level scope metadata for suggestion history and server suggestions', async () => {
  const source = await read('../src/composables/useGlobalSearch.ts')

  assert.match(source, /searchScopeKey:\s*computed\(\(\)\s*=>\s*getPersistKey\(\)\)/)
  assert.match(source, /const searchScopeLabel = computed\(\(\) =>/)
  assert.match(source, /const searchSuggestionScope = computed\(\(\) =>/)
})
