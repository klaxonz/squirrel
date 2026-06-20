import { ref, type Ref } from 'vue'
import type { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'

/**
 * HTML5 drag-and-drop queue reorder.
 *
 * Owns the in-flight drag source index and the drop handler that tells the
 * store to move the dragged item. A drop onto itself is a no-op (the item is
 * already there). The drag index is cleared after every drop so a subsequent
 * drag must start fresh.
 *
 * Extracted from GlobalMusicPlayerBar.vue so the drag state + the self-drop /
 * null-guard policy live in one reusable place; any queue surface that wants
 * drag-to-reorder can consume it.
 */
export interface UseQueueReorderOptions {
  store: ReturnType<typeof useMusicPlayerStore>
}

export interface UseQueueReorderReturn {
  dragIndex: Ref<number | null>
  onDragStart: (index: number, _event: DragEvent) => void
  onDrop: (targetIndex: number, _event: DragEvent) => void
}

export function useQueueReorder(options: UseQueueReorderOptions): UseQueueReorderReturn {
  const { store } = options

  const dragIndex = ref<number | null>(null)

  const onDragStart = (index: number, _event: DragEvent) => {
    dragIndex.value = index
  }

  const onDrop = (targetIndex: number, _event: DragEvent) => {
    if (dragIndex.value === null || dragIndex.value === targetIndex) return
    store.reorderQueue(dragIndex.value, targetIndex)
    dragIndex.value = null
  }

  return {
    dragIndex,
    onDragStart,
    onDrop,
  }
}
