export type MusicCardSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl'
export type MusicCardVariant = 'playlist' | 'album' | 'artist' | 'rank'

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

export const musicCardVariants = ({
  size,
  variant,
}: {
  size?: MusicCardSize
  variant?: MusicCardVariant
}) => [
  'music-card',
  sizeClasses[size ?? 'md'],
  variant ? variantClasses[variant] : '',
].filter(Boolean).join(' ')
