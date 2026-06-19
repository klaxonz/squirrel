import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Alert } from './Alert.vue'
export { default as AlertDescription } from './AlertDescription.vue'
export { default as AlertTitle } from './AlertTitle.vue'

export const alertVariants = cva(
  'relative w-full rounded-[calc(var(--radius-xl)+2px)] border px-4 py-3.5 text-sm shadow-[0_18px_38px_hsl(var(--surface-shadow))] [&>svg+div]:translate-y-[-2px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground [&>svg~*]:pl-7',
  {
    variants: {
      variant: {
        default: 'border-border/75 bg-card/92 text-foreground',
        // `destructive` kept as an alias for `error` (red) — pre-existing call
        // sites in AddChannelDialog / ImportSubscriptionDialog use it. New code
        // should prefer `error` for consistency with the success/warning/info
        // status-color family.
        destructive:
          'border-destructive/30 bg-destructive/10 text-destructive [&>svg]:text-destructive',
        error:
          'border-destructive/30 bg-destructive/10 text-destructive [&>svg]:text-destructive',
        success:
          'border-success/30 bg-success/10 text-success [&>svg]:text-success',
        warning:
          'border-warning/30 bg-warning/10 text-warning [&>svg]:text-warning',
        info:
          'border-border/75 bg-muted/60 text-foreground [&>svg]:text-muted-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export type AlertVariants = VariantProps<typeof alertVariants>
