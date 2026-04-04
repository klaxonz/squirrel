export const PLAYER_INTERACTIVE_SELECTOR = [
  'button',
  'a',
  'input',
  'textarea',
  'select',
  '[role="button"]',
  '[data-player-interactive]'
].join(', ')

export const isTouchLikePointer = (pointerType = '') => pointerType === 'touch' || pointerType === 'pen'

export const shouldHandlePointerVisibility = (pointerType = '') => !isTouchLikePointer(pointerType)

export const shouldTogglePlayOnVideoClick = (pointerType = '') => !isTouchLikePointer(pointerType)

export const getNextControlsVisibilityOnTouchTap = (controlsVisible) => !controlsVisible

export const shouldAutoHideControls = ({ controlsVisible, isPlaying, isScrubbing }) => (
  Boolean(controlsVisible) && Boolean(isPlaying) && !Boolean(isScrubbing)
)

export const isPlayerInteractiveTarget = (target) => {
  if (!target || typeof target !== 'object' || typeof target.closest !== 'function') {
    return false
  }

  return Boolean(target.closest(PLAYER_INTERACTIVE_SELECTOR))
}
