import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Button } from './Button.vue'

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-fast ease-default focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/45 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-40 active:scale-[0.985] select-none motion-reduce:active:scale-100 motion-reduce:transition-none',
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
        contrast:
          'border border-foreground/80 bg-foreground text-background shadow-sm hover:border-foreground/90 hover:bg-foreground/88 hover:text-background',
        ghost:
          'border border-transparent text-muted-foreground hover:border-border/50 hover:bg-card/50 hover:text-foreground',
        player:
          'border border-primary/35 bg-primary/15 text-primary hover:bg-primary/20 hover:text-primary disabled:bg-muted-foreground/20 disabled:text-muted-foreground/40 disabled:shadow-none',
        link:
          'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2',
        xs: 'h-7 px-2.5 text-xs rounded',
        sm: 'h-8 px-3 text-xs rounded',
        lg: 'h-10 px-6 rounded-lg text-base',
        icon: 'h-9 w-9',
        'icon-xs': 'h-[1.375rem] w-[1.375rem] rounded-md',
        'icon-sm': 'h-8 w-8',
        'mini-icon': 'h-[1.625rem] w-[1.625rem] rounded-md',
        'card-play': 'h-11 w-11 rounded-lg',
        'player-sm': 'h-8 w-8 rounded-full',
        'player-lg': 'h-[3.25rem] w-[3.25rem] rounded-full',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export type ButtonVariants = VariantProps<typeof buttonVariants>
