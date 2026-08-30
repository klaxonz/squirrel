import { nextTick, type Ref } from 'vue'
import { nextEntryIndex } from '@/features/rss/composables/rssEntryNav'
import { openExternalUrl } from '@/shared/lib/externalUrl'
import type { RssEntry, RssFeed } from '@/features/rss/types/rss'

type ReaderState = {
  readingEntry: Ref<RssEntry | null>
  showReaderSettings: Ref<boolean>
  showInAppBrowser: Ref<boolean>
  handleKeyDown: (event: KeyboardEvent) => void
  closeInAppBrowser: () => void
  openInAppBrowser: () => Promise<boolean>
}

export function useRssReaderWorkspace(options: {
  reader: ReaderState
  filteredEntries: Ref<RssEntry[]>
  entriesContainer: Ref<HTMLElement | null>
  findFeedByEntry: (feedId: number) => RssFeed | undefined
  toggleReadStatus: (entry: RssEntry, isRead?: boolean) => Promise<unknown>
  toggleStarStatus: (entry: RssEntry) => Promise<unknown>
  recordRecentlyViewed: (entry: RssEntry) => void
  onShowReaderPane: () => void
}) {
  const { reader } = options

  const isTypingTarget = (target: EventTarget | null) => {
    if (!(target instanceof HTMLElement)) return false
    const tag = target.tagName
    return target.isContentEditable
      || tag === 'INPUT'
      || tag === 'TEXTAREA'
      || tag === 'SELECT'
      || target.closest('[contenteditable="true"], [role="textbox"]') != null
  }

  const scrollEntryIntoView = (entryId: string | number) => {
    const root = options.entriesContainer.value
    if (!root) return
    const el = root.querySelector(`[data-entry-id="${String(entryId)}"]`)
    if (el instanceof HTMLElement) el.scrollIntoView({ block: 'nearest' })
  }

  const openReader = (entry: RssEntry) => {
    reader.readingEntry.value = entry
    const method = options.findFeedByEntry(entry.feed_id)?.open_method

    if (method === 'external_browser') {
      void openExternalUrl(entry.canonical_url)
      if (!entry.is_read) void options.toggleReadStatus(entry, false)
      options.recordRecentlyViewed(entry)
      return
    }

    if (!entry.is_read) void options.toggleReadStatus(entry, false)
    options.recordRecentlyViewed(entry)
    options.onShowReaderPane()
    if (method === 'app_browser') void reader.openInAppBrowser()
  }

  const stepReadingEntry = (delta: number) => {
    const list = options.filteredEntries.value
    if (!list.length) return
    const currentId = reader.readingEntry.value ? String(reader.readingEntry.value.id) : null
    const index = currentId ? list.findIndex((entry) => String(entry.id) === currentId) : -1
    const nextIndex = nextEntryIndex(list.length, index, delta)
    const next = nextIndex < 0 ? undefined : list[nextIndex]
    if (!next || (currentId && String(next.id) === currentId)) return
    openReader(next)
    void nextTick(() => scrollEntryIntoView(next.id))
  }

  const handleWorkspaceKeyDown = (event: KeyboardEvent) => {
    reader.handleKeyDown(event)
    if (event.defaultPrevented || event.isComposing || isTypingTarget(event.target)) return

    if (event.key === 'Escape') {
      if (reader.showReaderSettings.value) {
        event.preventDefault()
        reader.showReaderSettings.value = false
        return
      }
      if (reader.showInAppBrowser.value) {
        event.preventDefault()
        reader.closeInAppBrowser()
        return
      }
      if (reader.readingEntry.value) {
        event.preventDefault()
        reader.readingEntry.value = null
        return
      }
    }

    if (event.key === 'j' || event.key === 'J' || event.key === 'ArrowDown') {
      event.preventDefault()
      stepReadingEntry(1)
      return
    }
    if (event.key === 'k' || event.key === 'K' || event.key === 'ArrowUp') {
      event.preventDefault()
      stepReadingEntry(-1)
      return
    }

    const entry = reader.readingEntry.value
    if (!entry) return
    if (event.key === 's' || event.key === 'S') {
      event.preventDefault()
      void options.toggleStarStatus(entry)
    } else if (event.key === 'm' || event.key === 'M') {
      event.preventDefault()
      void options.toggleReadStatus(entry)
    }
  }

  return { openReader, stepReadingEntry, handleWorkspaceKeyDown }
}
