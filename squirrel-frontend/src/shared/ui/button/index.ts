import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Button } from './Button.vue'

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-[background-color,border-color,color,box-shadow] duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/45 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-40 active:scale-[0.985] select-none',
  {
    variants: {
      variant: {
        default:
          'bg-primary text-primary-foreground shadow-primary hover:bg-primary/90 hover:shadow-primary-hover',
        destructive:
          'bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90',
        outline:
          'border border-border/65 bg-card/35 text-foreground shadow-surface hover:border-border/80 hover:bg-card/58',
        secondary:
          'border border-border/50 bg-card/48 text-secondary-foreground shadow-surface hover:bg-card/64',
        ghost:
          'border border-transparent text-muted-foreground hover:border-border/50 hover:bg-card/50 hover:text-foreground',
        link:
          'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2',
        xs: 'h-7 px-2.5 text-xs rounded',
        sm: 'h-8 px-3 text-xs rounded',
        lg: 'h-10 px-6 rounded-lg text-base',
        icon: 'h-9 w-9',
        'icon-sm': 'h-8 w-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export type ButtonVariants = VariantProps<typeof buttonVariants>
