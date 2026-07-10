import { cva } from 'class-variance-authority'

export type MusicCardSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl'
export type MusicCardVariant = 'playlist' | 'album' | 'artist' | 'rank'

export const musicCardVariants = cva('music-card', {
  variants: {
    size: {
      xs: 'music-card--xs',
      sm: 'music-card--sm',
      md: 'music-card--md',
      lg: 'music-card--lg',
      xl: 'music-card--xl',
    },
    variant: {
      playlist: 'music-card--playlist',
      album: 'music-card--album',
      artist: 'music-card--artist',
      rank: 'music-card--rank',
    },
  },
  defaultVariants: {
    size: 'md',
  },
})

export const musicCardGridVariants = cva('music-card-grid', {
  variants: {
    layout: {
      'grid-2': 'music-card-grid--cols-2',
      'grid-3': 'music-card-grid--cols-3',
      'grid-4': 'music-card-grid--cols-4',
      'grid-5': 'music-card-grid--cols-5',
      'grid-auto': 'music-card-grid--auto',
      'scroll-x': 'music-card-grid--scroll-x',
    },
  },
  defaultVariants: {
    layout: 'grid-auto',
  },
})
