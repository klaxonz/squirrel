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
 * One settle transition for every navigation. Directional slides made the
 * workspace read as "the page moved"; a short 6px rise plus a crossfade
 * explains that new content arrived without claiming a spatial direction.
 */
// Skip first paint transition to avoid a launch flash on the initial route.
const isInitialMount = ref(true)
const transitionName = computed(() => (isInitialMount.value ? '' : 'page-settle'))

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
   Page-level transition (crossfade, no out-in).
   Leaving page is taken out of flow and sunk under the entering
   page so the workspace never flashes empty mid-navigation.
     enter: 240ms, opacity 0→1 with a 6px rise
     leave: 160ms, opacity only — the old page never moves
   ───────────────────────────────────────────────────────────── */
.page-settle-enter-active {
  position: relative;
  z-index: 1;
  transition:
    opacity 240ms var(--ease-out),
    transform 240ms var(--ease-out);
  will-change: opacity, transform;
}

.page-settle-leave-active {
  position: absolute;
  inset: 0;
  z-index: 0;
  transition: opacity 160ms var(--ease-out);
}

.page-settle-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.page-settle-leave-to {
  opacity: 0;
}
</style>
