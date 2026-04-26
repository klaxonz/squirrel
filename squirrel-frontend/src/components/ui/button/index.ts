import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Button } from './Button.vue'

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-md)] border border-transparent text-sm font-medium tracking-[0.01em] transition-all duration-[var(--duration-normal)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default:
          'bg-primary text-primary-foreground shadow-sm hover:opacity-90 active:opacity-80',
        destructive:
          'bg-destructive text-destructive-foreground shadow-sm hover:opacity-90 active:opacity-80',
        outline:
          'border-border bg-background text-foreground shadow-sm hover:bg-accent hover:text-accent-foreground',
        secondary:
          'border-border/70 bg-secondary/88 text-secondary-foreground shadow-sm hover:bg-secondary',
        ghost: 'border-transparent bg-transparent text-muted-foreground hover:bg-accent hover:text-accent-foreground',
        link: 'border-transparent text-primary underline-offset-4 hover:opacity-80',
      },
      size: {
        default: 'h-8 px-3 py-1.5 text-xs',
        xs: 'h-6 px-2 text-[0.6875rem] rounded-[var(--radius-sm)]',
        sm: 'h-7 px-2.5 text-[0.6875rem] rounded-[var(--radius-sm)]',
        lg: 'h-9 px-4 text-sm rounded-[var(--radius-lg)]',
        icon: 'h-8 w-8 rounded-[var(--radius-md)]',
        'icon-sm': 'size-7 rounded-[var(--radius-md)]',
        'icon-lg': 'size-9 rounded-[var(--radius-lg)]',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export type ButtonVariants = VariantProps<typeof buttonVariants>
