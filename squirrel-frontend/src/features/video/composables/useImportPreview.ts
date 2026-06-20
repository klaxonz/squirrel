import { computed, ref, type ComputedRef, type Ref } from 'vue'
import { previewImportSubscriptions } from '@/shared/api'

/**
 * Paginated subscription-import preview state machine.
 *
 * Owns the preview batch (total + subscriptions + has_more + cursor), the
 * initial-vs-load-more loading flags, and the request-error string. The cursor
 * drives `loadMore` (append) while `handlePreview` resets; appends de-dup by
 * url via `mergePreviewSubscriptions`. Derived counts (loaded / imported /
 * not-imported) are projections of the accumulated batch.
 *
 * Extracted from ImportSubscriptionDialog.vue so the cursor-pagination +
 * url-dedup + error-mapping policy live in one place rather than interleaved
 * with selection + step orchestration.
 */
const PREVIEW_BATCH_SIZE = 50

export interface ImportPreviewItem {
  url?: string | null
  is_imported?: boolean
  [key: string]: unknown
}

export interface ImportPreviewData {
  total: number | null
  subscriptions: ImportPreviewItem[]
  has_more: boolean
  cursor_payload: Record<string, unknown> | null
}

export interface UseImportPreviewOptions {
  selectedSite: ComputedRef<string> | Ref<string>
}

export interface UseImportPreviewReturn {
  previewData: Ref<ImportPreviewData>
  loadingPreview: Ref<boolean>
  loadingMorePreview: Ref<boolean>
  requestError: Ref<string>
  loadedCount: ComputedRef<number>
  importedCount: ComputedRef<number>
  notImportedCount: ComputedRef<number>
  fetchPreviewBatch: (opts?: { cursorPayload?: Record<string, unknown> | null; append?: boolean }) => Promise<boolean>
  loadMorePreview: () => Promise<void>
  resetPreview: () => void
}

// De-dup by url when appending a new batch onto the existing list.
const mergePreviewSubscriptions = (
  existing: ImportPreviewItem[] | null | undefined,
  incoming: ImportPreviewItem[] | null | undefined,
): ImportPreviewItem[] => {
  const merged: ImportPreviewItem[] = []
  const seen = new Set<string>()
  for (const item of [...(existing || []), ...(incoming || [])]) {
    if (!item?.url || seen.has(item.url)) continue
    seen.add(item.url)
    merged.push(item)
  }
  return merged
}

export function useImportPreview(options: UseImportPreviewOptions): UseImportPreviewReturn {
  const { selectedSite } = options

  const previewData = ref<ImportPreviewData>({
    total: null,
    subscriptions: [],
    has_more: false,
    cursor_payload: null,
  })
  const loadingPreview = ref(false)
  const loadingMorePreview = ref(false)
  const requestError = ref('')

  const loadedCount = computed(() => previewData.value.subscriptions.length)
  const importedCount = computed(() => previewData.value.subscriptions.filter((i) => i?.is_imported).length)
  const notImportedCount = computed(
    () => previewData.value.subscriptions.filter((i) => i && !i.is_imported).length,
  )

  const fetchPreviewBatch = async ({
    cursorPayload = null,
    append = false,
  }: { cursorPayload?: Record<string, unknown> | null; append?: boolean } = {}): Promise<boolean> => {
    const loadingState = append ? loadingMorePreview : loadingPreview
    loadingState.value = true
    try {
      const data = await previewImportSubscriptions(selectedSite.value, {
        cursorPayload,
        limit: PREVIEW_BATCH_SIZE,
      })
      requestError.value = ''
      previewData.value = {
        total: (data as { total?: number | null })?.total ?? previewData.value.total,
        subscriptions: append
          ? mergePreviewSubscriptions(previewData.value.subscriptions, (data as { subscriptions?: ImportPreviewItem[] })?.subscriptions || [])
          : (data as { subscriptions?: ImportPreviewItem[] })?.subscriptions || [],
        has_more: !!(data as { has_more?: boolean })?.has_more,
        cursor_payload: (data as { cursor_payload?: Record<string, unknown> | null })?.cursor_payload || null,
      }
      return true
    } catch (err) {
      requestError.value = err instanceof Error ? err.message : '预览订阅失败'
      return false
    } finally {
      loadingState.value = false
    }
  }

  const loadMorePreview = async () => {
    if (!selectedSite.value || !previewData.value.has_more) return
    await fetchPreviewBatch({
      cursorPayload: previewData.value.cursor_payload,
      append: true,
    })
  }

  const resetPreview = () => {
    previewData.value = { total: null, subscriptions: [], has_more: false, cursor_payload: null }
    loadingPreview.value = false
    loadingMorePreview.value = false
  }

  return {
    previewData,
    loadingPreview,
    loadingMorePreview,
    requestError,
    loadedCount,
    importedCount,
    notImportedCount,
    fetchPreviewBatch,
    loadMorePreview,
    resetPreview,
  }
}
