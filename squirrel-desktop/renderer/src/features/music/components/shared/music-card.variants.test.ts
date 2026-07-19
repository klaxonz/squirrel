import { describe, expect, it } from 'vitest'
import { musicCardVariants } from './music-card.variants'

describe('musicCardVariants', () => {
  it('composes the requested size, variant, and layout without fallback classes', () => {
    const classes = musicCardVariants({
      size: 'sm',
      variant: 'album',
      layout: 'row',
    }).split(' ')

    expect(classes).toEqual([
      'music-card',
      'music-card--sm',
      'music-card--album',
      'music-card--row',
    ])
    expect(classes).not.toContain('music-card--md')
    expect(classes).not.toContain('music-card--tile')
  })

  it('uses the shared tile defaults when no options are provided', () => {
    expect(musicCardVariants({})).toBe('music-card music-card--md music-card--tile')
  })
})
