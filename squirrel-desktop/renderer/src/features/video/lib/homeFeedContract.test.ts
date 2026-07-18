/**
 * Home feed contract: stacked rails only — no hero stage / side queue.
 */
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (relativePath: string) =>
  readFileSync(new URL(relativePath, import.meta.url), 'utf8')

const home = read('../views/HomeView.vue')
const continueWatching = read('../components/feed/ContinueWatching.vue')
const featured = read('../components/feed/FeaturedVideos.vue')
const specialFollow = read('../components/feed/SpecialFollowVideos.vue')
const railHeader = read('../components/feed/FeedRailHeader.vue')
const videoItem = read('../components/feed/VideoItem.vue')

describe('FreeTube home feed contract', () => {
  it('renders only stacked home rails without a focus stage or side queue', () => {
    expect(home).toContain('<h1 class="home-page-header__title">首页</h1>')
    expect(home).toContain('width="media"')
    expect(home).toContain('class="home-rails"')
    expect(home).toContain('ContinueWatching')
    expect(home).toContain('FeaturedVideos')
    expect(home).toContain('SpecialFollowVideos')
    expect(home).not.toContain('SpotlightRow')

    expect(home).not.toMatch(/home-stage|home-queue|home-focus/)
    expect(home).not.toMatch(/heroMode|heroVideo|loadFeaturedVideos|getFeaturedVideos/)
  })

  it('does not couple continue-watching to a page-level hero picker', () => {
    expect(continueWatching).not.toMatch(/heroChange|excludeVideoId|pickHeroVideo|pushRecentHero/)
    expect(continueWatching).toContain('title="继续观看"')
    expect(continueWatching).toContain('getWatchHistory')
  })

  it('keeps curated featured content as a horizontal rail', () => {
    expect(featured).toContain('title="精选推荐"')
    expect(featured).toContain('getFeaturedVideos')
    expect(featured).toContain('app-video-rail-card')
  })

  it('uses one visible browse-all affordance for every capped home rail', () => {
    for (const rail of [continueWatching, featured, specialFollow]) {
      expect(rail).toContain('view-more')
      expect(rail).toContain('@view-more')
    }
    expect(railHeader).toContain('<span>{{ viewMoreLabel }}</span>')
    expect(home.match(/@viewMore="goToAllVideos"/g)).toHaveLength(2)
    expect(home).toContain('@viewMore="goToContinueWatching"')
    expect(home).not.toContain('goToSpecialFollowVideos')
  })

  it('keeps home metadata text-first and limits media-frame status chrome', () => {
    expect(continueWatching).toContain('thumbnail-status="progress-only"')
    for (const rail of [featured, specialFollow]) {
      expect(rail).toContain('thumbnail-status="none"')
      expect(rail).not.toContain('show-avatar')
    }
    expect(continueWatching).not.toContain('show-avatar')
    expect(videoItem).toContain("thumbnailStatus?: 'full' | 'progress-only' | 'none'")
    expect(videoItem).toContain("props.thumbnailStatus === 'full'")
    expect(videoItem).toContain("props.thumbnailStatus !== 'none'")
  })
})
