import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Button } from './Button.vue'

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full border border-transparent text-sm font-medium tracking-[0.01em] transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default:
          'bg-primary text-primary-foreground shadow-[0_18px_40px_hsl(var(--surface-shadow))] hover:-translate-y-0.5 hover:bg-primary/95 hover:shadow-[0_24px_48px_hsl(var(--surface-shadow))]',
        destructive:
          'bg-destructive text-destructive-foreground shadow-[0_18px_40px_hsl(var(--surface-shadow))] hover:-translate-y-0.5 hover:bg-destructive/95 hover:shadow-[0_24px_48px_hsl(var(--surface-shadow))]',
        outline:
          'border-border/80 bg-card/88 text-foreground shadow-[0_10px_28px_hsl(var(--surface-shadow))] hover:-translate-y-0.5 hover:bg-accent/70 hover:text-accent-foreground',
        secondary:
          'border-border/70 bg-secondary/88 text-secondary-foreground shadow-[0_10px_24px_hsl(var(--surface-shadow))] hover:-translate-y-0.5 hover:bg-secondary',
        ghost: 'border-transparent bg-transparent text-muted-foreground hover:bg-accent/65 hover:text-accent-foreground',
        link: 'border-transparent text-primary underline-offset-4 hover:text-primary/90 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        xs: 'h-7 px-2.5 text-[0.7rem]',
        sm: 'h-8 px-3 text-xs',
        lg: 'h-11 px-8 text-sm',
        icon: 'h-10 w-10',
        'icon-sm': 'size-8',
        'icon-lg': 'size-11',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export type ButtonVariants = VariantProps<typeof buttonVariants>
