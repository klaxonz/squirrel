export { default as Badge } from './Badge.vue'

export type BadgeVariant =
  | 'default'
  | 'secondary'
  | 'destructive'
  | 'outline'
  | 'success'
  | 'warning'
  | 'error'
  | 'muted'
  | 'active'

export type BadgeVariants = { variant?: BadgeVariant }
