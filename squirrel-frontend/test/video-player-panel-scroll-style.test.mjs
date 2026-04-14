import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('playlist panel and video aside use single hidden-scrollbar scroll regions', async () => {
  const playlistPanelSource = await readFile(new URL('../src/components/playlist/PlaylistPanel.vue', import.meta.url), 'utf8')
  const videoPlaySource = await readFile(new URL('../src/views/VideoPlay.vue', import.meta.url), 'utf8')

  assert.match(playlistPanelSource, /class="playlist-panel__scroll scrollbar-hide"/)
  assert.match(playlistPanelSource, /\.playlist-panel__content\s*\{[\s\S]*overflow: hidden;[\s\S]*display: flex;[\s\S]*flex-direction: column;/)
  assert.match(playlistPanelSource, /\.playlist-panel__scroll\s*\{[\s\S]*overflow-y: auto;[\s\S]*scrollbar-width: none;[\s\S]*-ms-overflow-style: none;/)
  assert.match(playlistPanelSource, /\.playlist-panel__scroll::-webkit-scrollbar\s*\{\s*display: none;\s*\}/)

  assert.match(videoPlaySource, /\.video-aside\s*\{[\s\S]*min-height: 0;/)
  assert.match(videoPlaySource, /\.video-aside__panel\s*\{[\s\S]*min-height: 0;[\s\S]*max-height: calc\(100vh - var\(--app-topbar-height, 0px\) - 2rem\);[\s\S]*max-height: calc\(100dvh - var\(--app-topbar-height, 0px\) - 2rem\);[\s\S]*overflow: hidden;/)
  assert.match(videoPlaySource, /\.video-aside__content\s*\{[\s\S]*overflow-y: auto;[\s\S]*scrollbar-width: none;[\s\S]*-ms-overflow-style: none;/)
  assert.match(videoPlaySource, /\.video-aside__content::-webkit-scrollbar\s*\{\s*display: none;\s*\}/)
})
