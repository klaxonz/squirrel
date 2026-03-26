import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Badge } from './Badge.vue'

export const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[0.6875rem] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
  {
    variants: {
      variant: {
        default:
          'border-primary/20 bg-primary/10 text-primary hover:bg-primary/15',
        secondary:
          'border-border/70 bg-secondary/80 text-secondary-foreground hover:bg-secondary',
        destructive:
          'border-destructive/20 bg-destructive/10 text-destructive hover:bg-destructive/15',
        outline: 'border-border/75 bg-card/80 text-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export type BadgeVariants = VariantProps<typeof badgeVariants>
