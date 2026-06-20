import { computed, ref, type ComputedRef, type Ref } from 'vue'

/**
 * URL-keyed multi-select for the subscription import preview.
 *
 * Owns the selected-URL map + derived count, plus the toggle/select-all/clear
 * flows. Selection is keyed by `url` (stable across pagination appends) and only
 * ever includes subscriptions that aren't already imported — `toggleSelection`
 * is a no-op for imported items, and `selectAllNotImported` seeds the map from
 * the not-yet-imported subset of a preview batch.
 *
 * Extracted from ImportSubscriptionDialog.vue so the "imported items are
 * immutable" invariant + the url-keying live in one reusable place.
 */
export interface ImportPreviewItem {
  url?: string | null
  is_imported?: boolean
}

export interface UseImportSelectionOptions {
  /** The current preview batch (read by selectAllNotImported). */
  subscriptions: ComputedRef<ImportPreviewItem[]> | Ref<ImportPreviewItem[]>
}

export interface UseImportSelectionReturn {
  selectedUrlMap: Ref<Record<string, boolean>>
  selectedCount: ComputedRef<number>
  toggleSelection: (sub: ImportPreviewItem) => void
  selectAllNotImported: () => void
  clearSelection: () => void
}

export function useImportSelection(options: UseImportSelectionOptions): UseImportSelectionReturn {
  const { subscriptions } = options

  const selectedUrlMap = ref<Record<string, boolean>>({})
  const selectedCount = computed(() => Object.keys(selectedUrlMap.value || {}).length)

  const toggleSelection = (sub: ImportPreviewItem) => {
    if (!sub?.url || sub.is_imported) return

    const map = { ...(selectedUrlMap.value || {}) }
    if (map[sub.url]) {
      delete map[sub.url]
    } else {
      map[sub.url] = true
    }
    selectedUrlMap.value = map
  }

  const selectAllNotImported = () => {
    const map: Record<string, boolean> = {}
    for (const sub of subscriptions.value || []) {
      if (sub?.url && !sub.is_imported) {
        map[sub.url] = true
      }
    }
    selectedUrlMap.value = map
  }

  const clearSelection = () => {
    selectedUrlMap.value = {}
  }

  return {
    selectedUrlMap,
    selectedCount,
    toggleSelection,
    selectAllNotImported,
    clearSelection,
  }
}
