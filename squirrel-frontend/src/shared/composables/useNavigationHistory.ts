import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'

import {
  canStepBack,
  canStepForward,
  currentEntry,
  listBackCandidates,
  listForwardCandidates,
  pushEntryReactive,
  replaceEntryReactive,
  patchCurrentEntryReactive,
  resetReactive,
  stepBackReactive,
  stepForwardReactive,
  jumpToEntryReactive,
  subscribe,
  type HistoryEntry,
} from '@/shared/lib/navigationHistory'

// 让 router.afterEach 知道这次跳转是栈本身驱动的，避免「goBack → afterEach → 再次 push」的死循环。
import { suppressNextStackUpdate } from '@/app/router'

/**
 * 应用层导航历史。
 *
 * 取代旧版的三段式优先级（internalBack → videoBackTarget → meta.backTarget），
 * 统一以应用层 history stack 为单一真相：
 *   - 后退 / 前进只动栈指针；
 *   - 当前 entry 的滚动 / 过滤状态在 pop 时被恢复；
 *   - 路由切换由 router 接管，listener 只负责"修改 entry 内容"。
 *
 * 兼容旧调用点的轻量 shim：
 *   - `registerInternalBackHandler` / `setInternalBackAvailable` 仍然存在，
 *     但只是给视频页等场景提供"详情内部栈压栈"的入口；应用历史栈仍是
 *     唯一可信的回退信号。
 */
export function useNavigationHistory() {
  const router = useRouter()
  const route = useRoute()
  const tick = ref(0)

  let unsubscribe: (() => void) | null = null
  onMounted(() => {
    unsubscribe = subscribe(() => {
      tick.value += 1
    })
  })
  onUnmounted(() => {
    unsubscribe?.()
    unsubscribe = null
  })

  const backCandidates = computed(() => {
    // touch tick so the computed re-evaluates when the stack changes
    void tick.value
    return listBackCandidates(10)
  })
  const forwardCandidates = computed(() => {
    void tick.value
    return listForwardCandidates(10)
  })

  const canGoBack = computed(() => {
    void tick.value
    return canStepBack() || internalBackAvailable.value
  })

  const canGoForward = computed(() => {
    void tick.value
    return canStepForward()
  })

  const current = computed<HistoryEntry | null>(() => {
    void tick.value
    return currentEntry()
  })

  const direction = ref<'forward' | 'back' | 'replace'>('replace')

  async function goBack(): Promise<boolean> {
    if (internalBackAvailable.value && internalBackHandler?.()) {
      return true
    }
    const entry = stepBackReactive()
    if (!entry) return false
    direction.value = 'back'
    suppressNextStackUpdate()
    try {
      await router.replace(entry.fullPath)
    } catch {
      /* navigation guard aborted — restore entry pointer */
      pushEntryReactive({
        fullPath: route.fullPath,
        name: route.name as string | symbol | null | undefined,
        title: String(route.meta?.title ?? ''),
        breadcrumbs: [],
        sectionLabel: String(route.meta?.sectionLabel ?? ''),
        scrollY: 0,
      })
    }
    return true
  }

  async function goForward(): Promise<boolean> {
    const entry = stepForwardReactive()
    if (!entry) return false
    direction.value = 'forward'
    suppressNextStackUpdate()
    try {
      await router.replace(entry.fullPath)
    } catch {
      /* same recovery as back */
      pushEntryReactive({
        fullPath: route.fullPath,
        name: route.name as string | symbol | null | undefined,
        title: String(route.meta?.title ?? ''),
        breadcrumbs: [],
        sectionLabel: String(route.meta?.sectionLabel ?? ''),
        scrollY: 0,
      })
    }
    return true
  }

  function jumpTo(entryId: string): boolean {
    const entry = jumpToEntryReactive(entryId)
    if (!entry) return false
    direction.value = entry && currentEntry()?.id === entry.id ? 'replace' : 'back'
    suppressNextStackUpdate()
    void router.replace(entry.fullPath)
    return true
  }

  function recordEntry(input: Parameters<typeof pushEntryReactive>[0]) {
    return pushEntryReactive(input)
  }

  function replaceCurrentEntry(input: Parameters<typeof replaceEntryReactive>[0]) {
    return replaceEntryReactive(input)
  }

  function saveScrollPosition(scrollY: number) {
    patchCurrentEntryReactive({ scrollY })
  }

  // ── legacy internal-back bridge (music detail / artist detail etc.) ──
  let internalBackHandler: (() => boolean) | null = null
  const internalBackAvailable = ref(false)

  function registerInternalBackHandler(handler: () => boolean) {
    internalBackHandler = handler
    return () => {
      if (internalBackHandler === handler) {
        internalBackHandler = null
        internalBackAvailable.value = false
      }
    }
  }

  function setInternalBackAvailable(available: boolean) {
    internalBackAvailable.value = available
  }

  // ── 兼容旧 API ──
  const hasInternalBack = computed(() => internalBackAvailable.value)

  return {
    // 旧字段保留，避免破坏存量调用方
    canGoBack,
    goBack,
    hasInternalBack,
    registerInternalBackHandler,
    setInternalBackAvailable,

    // 新增字段
    canGoForward,
    goForward,
    jumpTo,
    backCandidates,
    forwardCandidates,
    current,
    direction,
    recordEntry,
    replaceCurrentEntry,
    saveScrollPosition,
    reset: resetReactive,

    // 兼容 VideoPlay 的旧字段（继续从历史栈的第一个非 video entry 推导）
    videoBackLabel: computed(() => {
      const list = backCandidates.value
      const last = list[list.length - 1]
      return last?.title || null
    }),
    videoBackTarget: computed<RouteLocationRaw | null>(() => {
      const list = backCandidates.value
      const last = list[list.length - 1]
      return last ? last.fullPath : null
    }),
    isVideoPage: computed(() => route.name === 'VideoPlay'),
    lastNonVideoRoute: computed<HistoryEntry | null>(() => {
      const list = backCandidates.value
      // 找最近的非 video entry
      for (let i = list.length - 1; i >= 0; i -= 1) {
        const e = list[i]
        if (e && e.name !== 'VideoPlay') return e
      }
      return null
    }),
  }
}
