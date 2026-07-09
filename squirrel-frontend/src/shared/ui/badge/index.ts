import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Badge } from './Badge.vue'

export const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium transition-colors duration-fast ease-default',
  {
    variants: {
      variant: {
        default:
          'border-primary/20 bg-primary/10 text-primary',
        secondary:
          'border-border/70 bg-secondary/80 text-secondary-foreground',
        destructive:
          'border-destructive/20 bg-destructive/10 text-destructive',
        outline: 'border-border/75 bg-card/80 text-foreground',
        /* Status indicators — color + label; never color alone */
        success: 'border-success/25 bg-success/10 text-success',
        warning: 'border-warning/25 bg-warning/10 text-warning',
        error: 'border-destructive/25 bg-destructive/10 text-destructive',
        muted: 'border-border/60 bg-secondary/60 text-muted-foreground',
        /* Active operational state (running / in-progress) */
        active: 'border-primary/20 bg-primary/10 text-primary',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export type BadgeVariants = VariantProps<typeof badgeVariants>
