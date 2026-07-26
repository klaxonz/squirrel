<template>
  <aside
    class="sidebar-rail"
    :class="{ 'has-player': showSidebarMusicPlayer, 'is-collapsed': collapsed }"
    aria-label="应用侧边栏"
  >
    <!-- Brand lives only here (current Reddit desktop). Titlebar has no logo. -->
    <div class="sidebar-brand" :class="{ 'is-collapsed': collapsed }">
      <RouterLink
        to="/home"
        class="sidebar-brand__link"
        :title="collapsed ? '归仓' : undefined"
        aria-label="归仓"
      >
        <BrandMark class="sidebar-brand__mark" />
        <strong v-if="!collapsed" class="sidebar-brand__name">归仓</strong>
      </RouterLink>
    </div>

    <nav class="sidebar-top-nav" aria-label="主要入口">
      <SidebarMenuItem
        v-for="item in SIDEBAR_TOP_ITEMS"
        :key="item.path"
        :item="item"
        :is-active="isNavigationItemActive(item, $route)"
        :collapsed="collapsed"
      />
    </nav>

    <nav :id="NAV_ID" class="sidebar-nav custom-scrollbar" aria-label="主导航">
      <section
        v-for="group in primaryNavGroups"
        :key="group.key"
        class="sidebar-group"
        :aria-labelledby="`sidebar-group-${group.key}`"
      >
        <h2
          :id="`sidebar-group-${group.key}`"
          class="sidebar-group__label"
          :class="{ 'sidebar-group__label--collapsed': collapsed }"
          :title="collapsed ? group.label : undefined"
        >
          {{ group.label }}
        </h2>
        <div class="sidebar-group__items">
          <SidebarMenuItem
            v-for="item in group.items"
            :key="item.path"
            :item="item"
            :is-active="isNavigationItemActive(item, $route)"
            :collapsed="collapsed"
          />
        </div>
      </section>
    </nav>

    <footer class="sidebar-footer">
      <SidebarMenuItem
        v-for="item in SIDEBAR_FOOTER_ITEMS"
        :key="item.path"
        :item="item"
        :is-active="isNavigationItemActive(item, $route)"
        :collapsed="collapsed"
      />
    </footer>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import BrandMark from '@/shared/components/BrandMark.vue'
import SidebarMenuItem from './SidebarMenuItem.vue'
import {
  NAV_GROUPS,
  SIDEBAR_FOOTER_ITEMS,
  SIDEBAR_TOP_ITEMS,
  isNavigationItemActive,
} from '@/shared/constants/sidebar'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'

defineProps<{ collapsed?: boolean }>()

const NAV_ID = 'app-sidebar-nav'
const route = useRoute()
const musicPlayerStore = useMusicPlayerStore()
const primaryNavGroups = NAV_GROUPS

const showSidebarMusicPlayer = computed(() =>
  route.name !== 'Music' && Boolean(
    musicPlayerStore.currentTrack
    && (musicPlayerStore.resolvingUrl || musicPlayerStore.audioSrc || musicPlayerStore.error),
  ),
)
</script>

<style scoped>
/*
  Current Reddit desktop rail:
  - brand wordmark at top of rail (orange)
  - home + nav rows with soft gray active wash
  - muted group labels
  - single right border; no double brand with titlebar
*/
.sidebar-rail {
  display: flex;
  width: 100%;
  height: 100%;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid hsl(var(--border));
  background: hsl(var(--sidebar));
  color: hsl(var(--sidebar-foreground));
  user-select: none;
}

.sidebar-brand {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  min-height: var(--app-titlebar-height);
  padding: 0 0.75rem;
  border-bottom: 1px solid hsl(var(--border) / 0.55);
}

.sidebar-brand.is-collapsed {
  justify-content: center;
  padding-inline: 0.375rem;
}

.sidebar-brand__link {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 0.5rem;
  color: inherit;
  text-decoration: none;
}

.sidebar-brand__mark {
  width: 1.5rem;
  height: 1.5rem;
  flex: 0 0 auto;
  color: hsl(var(--primary));
}

.sidebar-brand__name {
  overflow: hidden;
  font-family: var(--font-sans);
  font-size: 1.125rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1;
  color: hsl(var(--primary));
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-top-nav,
.sidebar-footer {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.5rem 0.75rem;
}

.sidebar-top-nav {
  padding-top: 0.625rem;
  padding-bottom: 0.25rem;
}

.sidebar-footer {
  border-top: 1px solid hsl(var(--border) / 0.55);
  padding-top: 0.5rem;
  padding-bottom: 0.625rem;
}

.sidebar-nav {
  min-height: 0;
  flex: 1 1 auto;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 0.25rem 0.75rem 0.75rem;
  transition: padding-bottom var(--duration-base) var(--ease-out);
}

.sidebar-rail.has-player .sidebar-nav {
  padding-bottom: calc(0.75rem + var(--sidebar-player-height));
}

.sidebar-group + .sidebar-group {
  margin-top: 0.75rem;
  padding-top: 0.625rem;
  border-top: 1px solid hsl(var(--border) / 0.4);
}

.sidebar-group__label {
  margin: 0 0 0.25rem;
  padding: 0.125rem 0.75rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0;
  line-height: 1.4;
  white-space: nowrap;
}

.sidebar-group__label--collapsed {
  overflow: hidden;
  padding-inline: 0;
  text-align: center;
  letter-spacing: 0;
  font-size: 0.5rem;
  text-overflow: clip;
}

.sidebar-group__items {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.sidebar-rail.is-collapsed :is(.sidebar-top-nav, .sidebar-nav, .sidebar-footer) {
  padding-inline: 0.375rem;
}

.sidebar-rail.is-collapsed .sidebar-group + .sidebar-group {
  margin-top: 0.5rem;
  padding-top: 0.375rem;
}

@media (prefers-reduced-motion: reduce) {
  .sidebar-nav {
    transition: none;
  }
}
</style>
