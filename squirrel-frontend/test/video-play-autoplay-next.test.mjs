import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayPath = new URL('../src/views/VideoPlay.vue', import.meta.url)

test('autoplay next uses playlist order before falling back to related videos', async () => {
  const source = await readFile(videoPlayPath, 'utf8')

  assert.match(source, /const handleAutoplayNext = async \(evt\) => \{[\s\S]*const playlistNext = goToNext\(\)[\s\S]*await goToVideo\(playlistNext\.id, playlistNext\)/)
})

test('autoplay next does not select the current video from related videos', async () => {
  const source = await readFile(videoPlayPath, 'utf8')

  assert.match(source, /const currentId = String\(video\.value\?\.id \?\? route\.params\.videoId \?\? ''\)/)
  assert.match(source, /String\(v\.id\) !== currentId/)
  assert.match(source, /!recentlyPlayed\.value\.includes\(v\.id\)/)
})
