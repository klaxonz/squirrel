<template>
  <header class="app-header">
    <div class="app-header__center">
      <Transition name="fade" mode="out-in">
        <div v-if="showSearch" key="search" class="app-header__search-wrap">
          <GlobalSearchBar
            :key="searchScope"
            class="app-header__search"
            :search-scope="searchScope"
            :placeholder="String(route.meta.searchPlaceholder || '搜索或输入命令...')"
            :suggestion-scope="String(route.meta.search || 'home')"
            :suggestions-enabled="searchSuggestionsEnabled"
            :search-modes="showVideoSearchMode ? searchModeOptions : []"
            :active-search-mode="videoSearchMode"
            :search-redirect-name="searchRedirectName"
            @search-mode-change="setVideoSearchMode"
          />
        </div>
        <div v-else key="spacer" class="app-header__spacer" />
      </Transition>
    </div>

    <div class="app-header__actions">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        class="app-header__user"
        :title="`${userDisplayName} - 个人资料`"
        @click="goToProfile"
      >
        <span class="app-header__avatar">
          <template v-if="userInitial">{{ userInitial }}</template>
          <AppIcon v-else name="user" class="size-3.5" />
        </span>
        <span class="app-header__user-name">{{ userDisplayName }}</span>
      </Button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import AppIcon from '@/shared/icons/AppIcon.vue'
import GlobalSearchBar from '@/shared/components/layout/GlobalSearchBar.vue'
import { Button } from '@/shared/ui/button'
import { useUIStore } from '@/shared/stores/ui'
import { useUserStore } from '@/shared/stores/user'

const route = useRoute()
const router = useRouter()
const uiStore = useUIStore()
const userStore = useUserStore()
const { isDesktop: isDesktopEnv } = useDesktopBridge()

const userDisplayName = computed(() => {
  if (!userStore.currentUser) return '未登录'
  return userStore.currentUser.nickname || '用户'
})
const userInitial = computed(() => {
  const name = userDisplayName.value
  return name && name !== '未登录' ? name.charAt(0) : ''
})

const goToProfile = () => {
  router.push('/profile')
}

const showSearch = computed(() => !!route.meta?.showSearch)
const searchScope = computed(() => String(route.meta.searchPersistKey || route.meta.search))
const searchSuggestionsEnabled = computed(() => route.meta.searchSuggestions !== false)
const isVideosRoute = computed(() => route.matched.some((record) => record.name === 'VideosView'))
const showVideoSearchMode = computed(() => {
  return isDesktopEnv()
    && (
      route.matched.some((record) => record.name === 'HomeView')
      || isVideosRoute.value
      || route.name === 'VideoPlay'
    )
})
const videoSearchMode = computed(() => {
  if (isVideosRoute.value) return route.query.mode === 'remote' ? 'remote' : 'local'
  return uiStore.homeSearchMode
})
const searchRedirectName = computed(() => (
  showVideoSearchMode.value && !isVideosRoute.value
    ? 'AllVideos'
    : isVideosRoute.value
      ? String(route.name || 'AllVideos')
      : String(route.meta.searchRedirectName || '')
))
const searchModeOptions = [
  { value: 'local', label: '本地' },
  { value: 'remote', label: '远端' },
] as const

function setVideoSearchMode(mode: 'local' | 'remote') {
  uiStore.setHomeSearchMode(mode)
  if (!isVideosRoute.value) return
  const query = { ...route.query }
  if (mode === 'remote') query.mode = 'remote'
  else {
    delete query.mode
    delete query.site
  }
  router.replace({ query })
}

</script>

<style scoped>
.app-header {
  height: 3.25rem;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(20rem, 36rem) minmax(0, 1fr);
  align-items: center;
  gap: var(--space-4);
  padding: 0 var(--space-5);
  border-bottom: 1px solid hsl(var(--border) / 0.32);
  /* Flat chrome on the shared canvas — no card band that reads as a third box. */
  background: hsl(var(--background) / 0.92);
  backdrop-filter: blur(10px);
  position: relative;
  z-index: var(--z-header);
  user-select: none;
}

.app-header__center {
  grid-column: 2;
  min-width: 0;
  display: flex;
  justify-content: center;
}

.app-header__search-wrap {
  width: 100%;
  max-width: 40rem;
  display: flex;
  justify-content: center;
}

.app-header__search {
  width: 100%;
}

.app-header__spacer {
  flex: 1 1 auto;
}

.app-header__actions {
  grid-column: 3;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 0;
}

.app-header__user {
  min-width: 0;
  max-width: 11rem;
  gap: 0.5rem;
  height: 2rem;
  padding: 0 0.5rem 0 0.375rem;
}

.app-header__user:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.app-header__avatar {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: var(--radius-md);
  background: hsl(var(--primary));
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6875rem;
  font-weight: 700;
  color: hsl(var(--primary-foreground));
  flex: 0 0 auto;
  letter-spacing: 0;
}

.app-header__user-name {
  overflow: hidden;
  font-size: 0.8125rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-fast) var(--ease-default);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 980px) {
  .app-header {
    grid-template-columns: minmax(0, 1fr) minmax(16rem, 32rem) minmax(0, 1fr);
  }

  .app-header__user-name {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-header__user,
  .fade-enter-active,
  .fade-leave-active {
    transition: none;
  }
}
</style>
