import test from 'node:test'
import assert from 'node:assert/strict'

import {
  PLAYER_INTERACTIVE_SELECTOR,
  getNextControlsVisibilityOnTouchTap,
  isPlayerInteractiveTarget,
  shouldHandlePointerVisibility,
  shouldAutoHideControls,
  shouldTogglePlayOnVideoClick
} from '../src/components/video-player/runtime/mobileControls.js'

test('touch and pen clicks do not toggle playback directly', () => {
  assert.equal(shouldTogglePlayOnVideoClick('touch'), false)
  assert.equal(shouldTogglePlayOnVideoClick('pen'), false)
  assert.equal(shouldTogglePlayOnVideoClick('mouse'), true)
})

test('touch-like pointers do not drive hover visibility logic', () => {
  assert.equal(shouldHandlePointerVisibility('touch'), false)
  assert.equal(shouldHandlePointerVisibility('pen'), false)
  assert.equal(shouldHandlePointerVisibility('mouse'), true)
  assert.equal(shouldHandlePointerVisibility(''), true)
})

test('single touch taps toggle control visibility', () => {
  assert.equal(getNextControlsVisibilityOnTouchTap(false), true)
  assert.equal(getNextControlsVisibilityOnTouchTap(true), false)
})

test('auto-hide only runs while playing with visible controls and no scrub', () => {
  assert.equal(shouldAutoHideControls({ controlsVisible: true, isPlaying: true, isScrubbing: false }), true)
  assert.equal(shouldAutoHideControls({ controlsVisible: false, isPlaying: true, isScrubbing: false }), false)
  assert.equal(shouldAutoHideControls({ controlsVisible: true, isPlaying: false, isScrubbing: false }), false)
  assert.equal(shouldAutoHideControls({ controlsVisible: true, isPlaying: true, isScrubbing: true }), false)
})

test('gesture layer treats player controls as interactive targets', () => {
  let receivedSelector = ''
  const interactiveTarget = {
    closest(selector) {
      receivedSelector = selector
      return {}
    }
  }

  assert.equal(isPlayerInteractiveTarget(interactiveTarget), true)
  assert.equal(receivedSelector, PLAYER_INTERACTIVE_SELECTOR)
  assert.match(PLAYER_INTERACTIVE_SELECTOR, /\[data-player-interactive\]/)

  const nonInteractiveTarget = {
    closest() {
      return null
    }
  }

  assert.equal(isPlayerInteractiveTarget(nonInteractiveTarget), false)
  assert.equal(isPlayerInteractiveTarget(null), false)
})
