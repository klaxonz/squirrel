import { computed, ref } from 'vue'
import type { SyncCenterItem, SyncCenterOverview } from '@/composables/useSyncCenter'

const createEmptyOverview = (): SyncCenterOverview => ({
  running_count: 0,
  awaiting_extract_count: 0,
  queued_count: 0,
  failed_count: 0,
  due_soon_count: 0,
  deferred_count: 0,
  pending_videos: 0,
  queue_depth: 0,
  queue_messages: 0,
})

export function useExtractionCenter() {
  const overview = ref<SyncCenterOverview>(createEmptyOverview())
  const runningPreview = ref<SyncCenterItem[]>([])
  const queuedPreview = ref<SyncCenterItem[]>([])
  const recentPreview = ref<SyncCenterItem[]>([])
  const overviewError = ref('')
  const runningPreviewError = ref('')
  const queuedPreviewError = ref('')
  const recentPreviewError = ref('')
  const loadingOverview = ref(false)
  const loadingItems = ref(false)
  const hasLoadedOnce = ref(false)

  const pageError = computed(() => {
    return overviewError.value || runningPreviewError.value || queuedPreviewError.value || recentPreviewError.value
  })

  return {
    hasLoadedOnce,
    loadingItems,
    loadingOverview,
    overview,
    overviewError,
    pageError,
    queuedPreview,
    queuedPreviewError,
    recentPreview,
    recentPreviewError,
    runningPreview,
    runningPreviewError,
  }
}
