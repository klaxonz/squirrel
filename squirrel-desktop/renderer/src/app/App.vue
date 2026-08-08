<template>
  <component :is="layout">
    <router-view v-slot="{ Component, route }">
      <!--
        Crossfade (no mode="out-in"): old + new pages coexist briefly so the
        stage is never empty. out-in waits for leave to finish before enter;
        if leave aborts (render throw, keep-alive edge), enter never starts
        and the user is stuck on a blank workspace until full reload.
      -->
      <Transition :name="transitionName" @enter="handleEnter" @after-enter="handleAfterEnter">
        <keep-alive :include="keepAliveIncludes" :max="10">
          <component
            :is="Component"
            :key="cacheKey(route)"
            v-bind="route.meta.componentProps || {}"
          />
        </keep-alive>
      </Transition>
    </router-view>
  </component>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from './layouts/AppLayout.vue'
import AuthLayout from './layouts/AuthLayout.vue'
import EmptyLayout from './layouts/EmptyLayout.vue'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'

const route = useRoute()
const router = useRouter()
const nav = useNavigationHistory()

const keepAliveIncludes = Array.from(new Set(
  router
    .getRoutes()
    .map((routeRecord) => routeRecord.meta.keepAliveComponent)
    .filter((componentName): componentName is string => typeof componentName === 'string'),
))

const layouts = {
  default: AppLayout,
  auth: AuthLayout,
  empty: EmptyLayout
}

const layout = computed(() => {
  const layoutName = (route.meta.layout as string) || 'default'
  return layouts[layoutName as keyof typeof layouts] || layouts.default
})

/**
 * 选择进入动画名（'page-forward' / 'page-back' / 'page-fade'），
 * 参考 Safari/Finder 的"我刚刚回退/前进"的方向感：
 *   - 前进：旧页向左推出，新页从右滑入；
 *   - 后退：旧页向右推回，新页从左滑入；
 *   - 同级替换（如设置 tab 切换）：仅淡入淡出。
 */
// Skip first paint transition to avoid a launch flash on the initial route.
const isInitialMount = ref(true)
const transitionName = computed(() => {
  if (isInitialMount.value) return ''
  const direction = nav.direction.value
  if (direction === 'back') return 'page-back'
  if (direction === 'forward') return 'page-forward'
  return 'page-fade'
})

/**
 * keep-alive 的缓存 key：用稳定的 transitionKey（路由自己定义），
 * 没有时退到 fullPath。目的是确保"同一逻辑页的不同子路由"（如
 * SubscriptionAllVideos / SubscriptionUnreadVideos）共享一个 keep-alive 实例。
 */
function cacheKey(r: typeof route): string {
  const tk = r.meta?.transitionKey as string | undefined
  if (tk) return tk
  return r.fullPath
}

/**
 * 进入动画结束后，把方向重置为 'replace'，这样下一次同层切换默认走 fade。
 * 不立刻重置是为了让方向信号在整个 transition 期间保持稳定。
 * First paint clears `isInitialMount` so subsequent navigations animate.
 */
function handleEnter() {
  nextTick(() => {
    isInitialMount.value = false
  })
}

/**
 * 消费方向信号：direction 只在 goBack/goForward/jumpTo 时被写入，普通
 * push/replace 不会重置它。若不消费，一次后退之后的所有前进导航都会沿用
 * 'back' 动画。@after-enter 在转场结束后触发，此时切换动画名不影响
 * 正在播放的转场；下一次导航会以 'replace'（fade）为默认方向。
 */
function handleAfterEnter() {
  nav.direction.value = 'replace'
}
</script>

<style>
/* Lock the viewport for App-like feel */
html, body {
  margin: 0;
  padding: 0;
  height: 100vh;
  overflow: hidden;
  background: hsl(var(--background));
}

#app {
  height: 100%;
}

/* ─────────────────────────────────────────────────────────────
   Page-level transitions (crossfade, no out-in).
   Leaving page is taken out of flow and sunk under the entering
   page so the workspace never flashes empty mid-navigation.
     - .page-fade      — same-level swap (Settings tab, music view)
     - .page-forward   — entering a detail page (push)
     - .page-back      — popping back (replace into parent)
   ───────────────────────────────────────────────────────────── */
.page-fade-enter-active,
.page-fade-leave-active,
.page-forward-enter-active,
.page-forward-leave-active,
.page-back-enter-active,
.page-back-leave-active {
  transition:
    opacity var(--duration-base, 180ms) var(--ease-default, cubic-bezier(0.4, 0, 0.2, 1)),
    transform var(--duration-base, 180ms) var(--ease-default, cubic-bezier(0.4, 0, 0.2, 1));
  will-change: opacity, transform;
}

.page-fade-enter-active,
.page-forward-enter-active,
.page-back-enter-active {
  position: relative;
  z-index: 1;
}

.page-fade-leave-active,
.page-forward-leave-active,
.page-back-leave-active {
  position: absolute;
  inset: 0;
  z-index: 0;
}

/* Forward / Back: keep only the crossfade — no horizontal slide, so a
   library → play → library round trip never reads as "the page moved". */
.page-forward-leave-to {
  opacity: 0;
}
.page-forward-enter-from {
  opacity: 0;
}

.page-back-leave-to {
  opacity: 0;
}
.page-back-enter-from {
  opacity: 0;
}

/* Same-level: pure fade. */
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}
</style>
