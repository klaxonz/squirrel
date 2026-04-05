import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayPath = new URL('../src/views/VideoPlay.vue', import.meta.url)
const appPath = new URL('../src/App.vue', import.meta.url)

test('video play theater mode keeps the related rail mounted and switches layout through container classes', async () => {
  const source = await readFile(videoPlayPath, 'utf8')

  assert.match(
    source,
    /<div :class="\['video-page__container', \{ 'is-widescreen': isWidescreen \}\]">/,
  )
  assert.match(source, /<div class="video-aside">/)
  assert.doesNotMatch(source, /isWidescreen \? 'hidden' : ''/)
})

test('video play theater mode defines a single-column widescreen layout and disables the sidebar rail behavior', async () => {
  const source = await readFile(videoPlayPath, 'utf8')

  assert.match(source, /\.video-page__container\.is-widescreen\s*\{/)
  assert.match(source, /grid-template-columns:\s*minmax\(0,\s*1fr\);/)
  assert.match(source, /\.video-page__container\.is-widescreen\s+\.video-aside\s*\{/)
  assert.match(source, /position:\s*static;/)
  assert.match(source, /\.video-page__container\.is-widescreen\s+\.related-video-card\s*\{/)
})

test('video play theater mode caps the player height to the viewport instead of letting the widened player overflow', async () => {
  const source = await readFile(videoPlayPath, 'utf8')

  assert.match(source, /--video-theater-top-offset:\s*calc\(var\(--app-topbar-height,\s*0px\) \+ 0\.5rem\);/)
  assert.match(source, /--video-theater-meta-peek:\s*clamp\(6\.5rem,\s*12vh,\s*8\.5rem\);/)
  assert.match(source, /--video-theater-bottom-gap:\s*0\.75rem;/)
  assert.match(source, /--video-theater-max-height:\s*calc\(100dvh - var\(--video-theater-top-offset\) - var\(--video-theater-meta-peek\) - var\(--video-theater-bottom-gap\)\);/)
  assert.match(
    source,
    /\.video-page__container\.is-widescreen\s+\.video-section\s*\{[\s\S]*?width:\s*100vw;[\s\S]*?height:\s*var\(--video-theater-max-height\);[\s\S]*?margin-inline:\s*calc\(50% - 50vw\);/,
  )
  assert.match(
    source,
    /\.video-page__container\.is-widescreen\s+\.video-container\s*\{[\s\S]*?width:\s*100%;[\s\S]*?height:\s*100%;[\s\S]*?max-height:\s*var\(--video-theater-max-height\);/,
  )
})

test('video play route uses a compact shell header so theater mode matches youtube top spacing more closely', async () => {
  const source = await readFile(appPath, 'utf8')

  assert.match(source, /const isVideoPlayRoute = computed\(\(\) => route\.name === 'VideoPlay'\)/)
  assert.match(source, /:class="\['minimal-header', \{ 'minimal-header--compact': isVideoPlayRoute \}\]"/)
  assert.match(source, /:class="\['header-left-spacer', \{ 'is-compact': isVideoPlayRoute \}\]"/)
  assert.match(source, /:class="\['minimal-search', \{ 'minimal-search--compact': isVideoPlayRoute \}\]"/)
  assert.match(source, /\.minimal-header--compact\s*\{/)
  assert.match(source, /padding:\s*0\.5rem 1rem;/)
})
