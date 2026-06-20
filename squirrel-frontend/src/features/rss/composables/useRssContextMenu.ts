import { computed, type ComputedRef, type Ref } from 'vue'
import type { RssEntry, RssFeed } from './rssTypes'

/**
 * Context-menu orchestration for the RSS sources view.
 *
 * The view renders two context menus (article + feed) whose root elements are
 * owned by child components but whose overflow-repositioning refs are owned by
 * useRssEntries / useRssFeeds. This composable owns the glue between them:
 *   - `closeContextMenu` dismisses both menus at once (window click/contextmenu),
 *   - `bindArticleMenuRef` / `bindFeedMenuRef` bridge a child's exposed
 *     `rootRef` onto the composable-owned menu ref,
 *   - `contextMenuFeedResolved` resolves the article menu's feed once per render
 *     (the inline template previously called findFeedByEntry 4× per render).
 *
 * Extracted from RssSources.vue: the two bind helpers were copy-pasted with the
 * same `instance.rootRef` extraction — centralised here behind one helper.
 */
type MenuChildInstance = { rootRef?: HTMLElement | null }

export interface UseRssContextMenuOptions {
  /** useRssFeeds-owned ref the feed menu measures for repositioning. */
  feedContextMenuRef: Ref<HTMLElement | null>
  /** useRssEntries-owned ref the article menu measures for repositioning. */
  contextMenuRef: Ref<HTMLElement | null>
  closeFeedContextMenu: () => void
  closeArticleContextMenu: () => void
  contextMenuEntry: ComputedRef<RssEntry | null> | Ref<RssEntry | null>
  findFeedByEntry: (feedId: number | RssEntry) => RssFeed | undefined
}

export interface UseRssContextMenuReturn {
  /** Dismiss both menus at once. */
  closeContextMenu: () => void
  /** Bridge the feed-menu child's exposed rootRef onto the composable-owned ref. */
  bindFeedMenuRef: (el: unknown) => void
  /** Bridge the article-menu child's exposed rootRef onto the composable-owned ref. */
  bindArticleMenuRef: (el: unknown) => void
  /** Feed for the article context menu, resolved once per render. */
  contextMenuFeedResolved: ComputedRef<RssFeed | null>
}

export function useRssContextMenu(options: UseRssContextMenuOptions): UseRssContextMenuReturn {
  const {
    feedContextMenuRef,
    contextMenuRef,
    closeFeedContextMenu,
    closeArticleContextMenu,
    contextMenuEntry,
    findFeedByEntry,
  } = options

  const closeContextMenu = () => {
    closeArticleContextMenu()
    closeFeedContextMenu()
  }

  // Shared extraction: a child menu component exposes `rootRef`; map a template
  // ref callback's unknown element onto the composable-owned measurement ref.
  const bridgeMenuRef = (target: Ref<HTMLElement | null>) => (el: unknown) => {
    const instance = el && typeof el === 'object' ? (el as MenuChildInstance) : null
    target.value = instance?.rootRef ?? null
  }

  const bindFeedMenuRef = bridgeMenuRef(feedContextMenuRef)
  const bindArticleMenuRef = bridgeMenuRef(contextMenuRef)

  const contextMenuFeedResolved = computed<RssFeed | null>(() =>
    contextMenuEntry.value ? (findFeedByEntry(contextMenuEntry.value) ?? null) : null,
  )

  return {
    closeContextMenu,
    bindFeedMenuRef,
    bindArticleMenuRef,
    contextMenuFeedResolved,
  }
}
