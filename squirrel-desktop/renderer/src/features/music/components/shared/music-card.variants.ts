export type MusicCardSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl'
export type MusicCardVariant = 'playlist' | 'album' | 'artist' | 'rank'
export type MusicCardLayout = 'tile' | 'feature' | 'row'

const sizeClasses: Record<MusicCardSize, string> = {
  xs: 'music-card--xs',
  sm: 'music-card--sm',
  md: 'music-card--md',
  lg: 'music-card--lg',
  xl: 'music-card--xl',
}

const variantClasses: Record<MusicCardVariant, string> = {
  playlist: 'music-card--playlist',
  album: 'music-card--album',
  artist: 'music-card--artist',
  rank: 'music-card--rank',
}

const layoutClasses: Record<MusicCardLayout, string> = {
  tile: 'music-card--tile',
  feature: 'music-card--feature',
  row: 'music-card--row',
}

export const musicCardVariants = ({
  size,
  variant,
  layout,
}: {
  size?: MusicCardSize
  variant?: MusicCardVariant
  layout?: MusicCardLayout
}) => [
  'music-card',
  sizeClasses[size ?? 'md'],
  variant ? variantClasses[variant] : '',
  layoutClasses[layout ?? 'tile'],
].filter(Boolean).join(' ')
