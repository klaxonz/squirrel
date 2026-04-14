import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('playlist flow uses a shared store and supports dialog add plus aside list browsing', async () => {
  const usePlaylistSource = await readFile(new URL('../src/composables/usePlaylist.ts', import.meta.url), 'utf8')
  const playlistPanelSource = await readFile(new URL('../src/components/playlist/PlaylistPanel.vue', import.meta.url), 'utf8')
  const videoPlaySource = await readFile(new URL('../src/views/VideoPlay.vue', import.meta.url), 'utf8')
  const playlistViewSource = await readFile(new URL('../src/views/PlaylistView.vue', import.meta.url), 'utf8')

  assert.match(usePlaylistSource, /const playlistStore = createPlaylistStore\(\)/)
  assert.match(usePlaylistSource, /export default function usePlaylist\(\) \{\s*return playlistStore\s*\}/)
  assert.match(usePlaylistSource, /activePlaylistItems\.value = data \|\| \[][\s\S]*setCurrentVideo\(currentVideoId\.value\)/)
  assert.match(usePlaylistSource, /await fetchPlaylists\(\)/)

  assert.match(playlistPanelSource, /if \(props\.videoId\) \{\s*await addVideo\(props\.videoId, playlistId\)\s*\}/)
  assert.match(playlistPanelSource, /await reorder\(activePlaylist\.value\.id, moved\.video_id, targetIndex \+ 1\)/)
  assert.match(playlistPanelSource, /activePlaylistItems\.value = previousItems/)
  assert.match(playlistPanelSource, /v-if="videoId && !currentVideoAlreadyInActivePlaylist"/)

  assert.match(videoPlaySource, /:class="\{ 'is-active': asideTab === 'playlist' \}"/)
  assert.match(videoPlaySource, /<Dialog :open="showPlaylistPicker" @update:open="handlePlaylistPickerOpenChange">/)
  assert.match(videoPlaySource, /handleAddCurrentVideoToPlaylist\(playlist\.id\)/)
  assert.match(videoPlaySource, /handleCreatePlaylistFromPicker/)
  assert.match(videoPlaySource, /playPlaylistItem\(item\)/)
  assert.match(videoPlaySource, /v-if="playlists.length > 1" class="playlist-aside__playlist-list"/)
  assert.doesNotMatch(videoPlaySource, /playlist-aside__summary/)
  assert.doesNotMatch(videoPlaySource, /<PlaylistPanel/)
  assert.match(videoPlaySource, /setCurrentVideo\(videoId \?\? null\);/)
  assert.match(playlistViewSource, /setCurrentVideo\(item\.video\.id\)/)
})

test('playlist backend distinguishes missing lists and uses one-based reorder positions', async () => {
  const serviceSource = await readFile(new URL('../../squirrel-backend/services/playlist_service.py', import.meta.url), 'utf8')
  const schemaSource = await readFile(new URL('../../squirrel-backend/schemas/playlist.py', import.meta.url), 'utf8')
  const routeSource = await readFile(new URL('../../squirrel-backend/routes/playlist.py', import.meta.url), 'utf8')

  assert.match(serviceSource, /def get_playlist_items\(user_id: int, playlist_id: int\) -> list\[dict\] \| None:/)
  assert.match(serviceSource, /if not playlist:\s*return None/)
  assert.match(serviceSource, /new_position = max\(1, min\(new_position, max_position\)\)/)
  assert.match(schemaSource, /new_position: int = Field\(\.\.\., ge=1, description='新的位置（从 1 开始）'\)/)
  assert.match(routeSource, /if items is None:\s*return response\.not_found\("播放列表不存在"\)/)
})
