import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

test('clip marker control uses the shared player icon system', async () => {
  const iconTypeSource = await readFile(new URL('../src/components/video-player/core/useIcons.ts', import.meta.url), 'utf8')
  const playerIconSource = await readFile(new URL('../src/components/video-player/PlayerIcon.vue', import.meta.url), 'utf8')
  const playerSource = await readFile(new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url), 'utf8')
  const materialSymbolsSubsetSource = await readFile(new URL('../src/utils/materialSymbolsSubset.json', import.meta.url), 'utf8')

  assert.match(iconTypeSource, /\| 'markClip'/)
  assert.match(playerIconSource, /markClip: 'material-symbols:movie-edit'/)
  assert.match(materialSymbolsSubsetSource, /"movie-edit": \{/)
  assert.match(playerSource, /<PlayerIcon name="markClip" \/>/)
  assert.doesNotMatch(playerSource, /<circle cx="12" cy="13" r="3"/)
})
