import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('playlist view uses in-page workspace layout and shared UI primitives', async () => {
  const playlistViewSource = await readFile(new URL('../src/views/PlaylistView.vue', import.meta.url), 'utf8')

  assert.match(playlistViewSource, /<PageHeader/)
  assert.match(playlistViewSource, /class="playlist-workspace"/)
  assert.match(playlistViewSource, /class="playlist-library__list scrollbar-hide"/)
  assert.match(playlistViewSource, /class="playlist-detail__items scrollbar-hide"/)
  assert.match(playlistViewSource, /<Transition name="playlist-editor-fade">/)
  assert.match(playlistViewSource, /class="playlist-editor-layer"/)
  assert.match(playlistViewSource, /<Dialog :open="showDeleteConfirm" @update:open="handleDeleteConfirmOpenChange">/)
  assert.match(playlistViewSource, /<Textarea/)
  assert.match(playlistViewSource, /await syncSelectionWithList\(created\.id\)/)
  assert.doesNotMatch(playlistViewSource, /class="playlist-drawer"/)
  assert.doesNotMatch(playlistViewSource, /const isDrawerOpen = ref\(false\)/)
})
