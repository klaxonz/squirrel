import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'

export type MusicView =
  | 'home'
  | 'search'
  | 'fm'
  | 'ranks'
  | 'playlists'
  | 'playlist-detail'
  | 'user-playlist-detail'
  | 'artist-detail'
  | 'album-detail'
  | 'profile'
  | 'new-songs'
  | 'new-albums'
  | 'ai-recommend'
  | 'everyday-recommend'
  | 'favorites'

const ROOT_VIEWS: ReadonlyArray<MusicView> = ['home', 'ranks', 'playlists', 'profile']
const DETAIL_VIEWS: ReadonlyArray<MusicView> = [
  'playlist-detail',
  'user-playlist-detail',
  'artist-detail',
  'album-detail',
]

/**
 * 音乐模块的视图状态。
 *
 * 之前内部维护了一个独立的 viewHistory 栈（[playlist-detail, ranks, home]）
 * 来支持"返回上一层"。现在把这一切都统一到全局 navigationHistory：
 *   - 当前 view 从 route.query.view 推导，刷新页面 / 深链 / 浏览器前进后退
 *     都能正确恢复；
 *   - "进入详情"通过 router.push 新增 URL（query 里带 view），全局栈会自然
 *     推入新 entry；
 *   - "返回上一层"通过 useNavigationHistory.goBack() 一次性弹出栈顶；
 *   - useMusicNavigation 只负责 view 字段的解析 / 派发，不再持有自己的栈。
 *
 * 应用历史因此能正确记录音乐内部视图，并响应 back/forward。
 */
export function useMusicNavigation() {
  const route = useRoute()
  const router = useRouter()
  const nav = useNavigationHistory()

  const parseViewFromQuery = (q: unknown): MusicView => {
    const value = String(q ?? '').trim() as MusicView
    if (!value) return 'home'
    return value
  }

  const activeView = ref<MusicView>(parseViewFromQuery(route.query.view))

  // 同步 route.query.view → activeView（处理浏览器后退 / 直跳）
  watch(
    () => route.query.view,
    (next) => {
      const value = parseViewFromQuery(next)
      if (value !== activeView.value) {
        activeView.value = value
      }
    },
  )

  function navigateTo(view: MusicView) {
    if (activeView.value === view) return

    const isDetail = DETAIL_VIEWS.includes(view)
    const wasDetail = DETAIL_VIEWS.includes(activeView.value)
    // 同根 → 替换；进入详情 → 推入栈；离开详情回到根 → 替换（一次 pop）。
    const query: Record<string, string> = view === 'home' ? {} : { view }

    if (isDetail && !wasDetail) {
      void router.push({ name: 'Music', query })
    } else if (!isDetail && wasDetail) {
      // 从详情回到根视图：不要 push 一条冗余 entry，replace 让浏览器栈保持精简。
      void router.replace({ name: 'Music', query })
    } else if (ROOT_VIEWS.includes(view)) {
      // 根视图间切换
      void router.replace({ name: 'Music', query })
    } else {
      void router.replace({ name: 'Music', query })
    }

    activeView.value = view
  }

  function goBack(): boolean {
    if (DETAIL_VIEWS.includes(activeView.value) && nav.canGoBack.value) {
      void nav.goBack()
      return true
    }
    return false
  }

  function goHome() {
    navigateTo('home')
  }

  const canGoBack = computed(() => {
    if (!DETAIL_VIEWS.includes(activeView.value)) return false
    return nav.canGoBack.value
  })

  const isDetailView = computed(() => DETAIL_VIEWS.includes(activeView.value))

  return {
    activeView,
    navigateTo,
    goBack,
    goHome,
    canGoBack,
    isDetailView,
  }
}
