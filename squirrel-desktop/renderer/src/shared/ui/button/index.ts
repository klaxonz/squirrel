export { default as Button } from './Button.vue'
export { default as IconButton } from './IconButton.vue'

export type ButtonVariant =
  | 'default'
  | 'destructive'
  | 'outline'
  | 'secondary'
  | 'contrast'
  | 'ghost'
  | 'link'

export type ButtonSize =
  | 'default'
  | 'sm'
  | 'lg'

export type ButtonVariants = {
  variant?: ButtonVariant
  size?: ButtonSize
}
