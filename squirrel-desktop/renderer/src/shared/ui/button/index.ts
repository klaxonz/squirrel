export { default as Button } from './Button.vue'

export type ButtonVariant =
  | 'default'
  | 'destructive'
  | 'outline'
  | 'secondary'
  | 'contrast'
  | 'ghost'
  | 'player'
  | 'link'

export type ButtonSize =
  | 'default'
  | 'xs'
  | 'sm'
  | 'lg'
  | 'icon'
  | 'icon-xs'
  | 'icon-sm'
  | 'mini-icon'
  | 'card-play'
  | 'player-sm'
  | 'player-lg'

export type ButtonVariants = {
  variant?: ButtonVariant
  size?: ButtonSize
}
