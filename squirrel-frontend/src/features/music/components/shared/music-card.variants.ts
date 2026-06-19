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

export const musicCardSizeConfig: Record<MusicCardSize, { width: number; radius: number; gap: number }> = {
  xs: { width: 100, radius: 6, gap: 12 },
  sm: { width: 120, radius: 8, gap: 16 },
  md: { width: 160, radius: 12, gap: 20 },
  lg: { width: 200, radius: 14, gap: 24 },
  xl: { width: 280, radius: 16, gap: 32 },
}

export const musicCardGridVariants = cva('music-card-grid', {
  variants: {
    layout: {
      'grid-2': 'music-card-grid--cols-2',
      'grid-3': 'music-card-grid--cols-3',
      'grid-4': 'music-card-grid--cols-4',
      'grid-auto': 'music-card-grid--auto',
      'scroll-x': 'music-card-grid--scroll-x',
    },
  },
  defaultVariants: {
    layout: 'grid-auto',
  },
})
