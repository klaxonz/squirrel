import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Button } from './Button.vue'

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-40 active:scale-[0.97] select-none',
  {
    variants: {
      variant: {
        default:
          'bg-foreground text-background shadow-[0_1px_2px_rgba(0,0,0,0.1)] hover:opacity-90',
        destructive:
          'bg-destructive text-destructive-foreground shadow-sm hover:opacity-90',
        outline:
          'border border-border/60 bg-background text-foreground shadow-[0_1px_2px_rgba(0,0,0,0.02)] hover:bg-accent hover:border-border',
        secondary:
          'bg-accent/50 text-foreground hover:bg-accent',
        ghost: 
          'text-muted-foreground hover:bg-accent hover:text-foreground',
        link: 
          'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2',
        xs: 'h-7 px-2.5 text-[11px] rounded-md',
        sm: 'h-8 px-3 text-xs rounded-md',
        lg: 'h-10 px-6 rounded-xl text-[15px]',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export type ButtonVariants = VariantProps<typeof buttonVariants>
