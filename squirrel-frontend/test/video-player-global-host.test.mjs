import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const appPath = new URL('../src/App.vue', import.meta.url)
const videoPlayPath = new URL('../src/views/VideoPlay.vue', import.meta.url)
const hostPath = new URL('../src/components/video-player/GlobalVideoPlayerHost.vue', import.meta.url)
const playerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('app mounts a persistent global video player host outside route view teardown', async () => {
  const source = await readFile(appPath, 'utf8')

  assert.match(source, /import GlobalVideoPlayerHost from '@\/components\/video-player\/GlobalVideoPlayerHost\.vue'/)
  assert.match(source, /<GlobalVideoPlayerHost \/>/)
})

test('video play registers a dedicated player host target instead of rendering the player inline', async () => {
  const source = await readFile(videoPlayPath, 'utf8')

  assert.match(source, /ref="videoPlayerHostRef"/)
  assert.match(source, /class="video-player-host"/)
  assert.match(source, /activateGlobalVideoPlayerSession\(\{/)
  assert.match(source, /registerGlobalVideoPlayerTarget\(element\)/)
  assert.doesNotMatch(source, /<VideoPlayer/)
})

test('global player host keeps PiP mounted off-page and restores the video route when PiP closes', async () => {
  const source = await readFile(hostPath, 'utf8')

  assert.match(source, /<Teleport v-if="globalVideoPlayerSession\.active && teleportTarget" :to="teleportTarget">/)
  assert.match(source, /const teleportTarget = computed\(\(\) => globalVideoPlayerSession\.target \|\| detachedHostRef\.value\)/)
  assert.match(source, /@enterpictureinpicture="handleEnterPictureInPicture"/)
  assert.match(source, /@leavepictureinpicture="handleLeavePictureInPicture"/)
  assert.match(source, /await router\.push\(\{ name: 'VideoPlay', params: \{ videoId: currentVideoId \} \}\)/)
})

test('video player emits explicit PiP lifecycle events for the global host bridge', async () => {
  const source = await readFile(playerPath, 'utf8')

  assert.match(source, /'enterpictureinpicture'/)
  assert.match(source, /'leavepictureinpicture'/)
  assert.match(source, /watch\(\(\) => store\.pictureInPicture, \(inPictureInPicture, previousValue\) => \{/)
  assert.match(source, /emit\(inPictureInPicture \? 'enterpictureinpicture' : 'leavepictureinpicture'\)/)
})
