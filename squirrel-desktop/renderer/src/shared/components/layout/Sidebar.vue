<template>
  <aside
    class="sidebar-rail"
    :class="{ 'has-player': showSidebarMusicPlayer, 'is-collapsed': collapsed }"
    aria-label="应用侧边栏"
  >
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
/* Persistent navigation rail with grouped destinations and a compact brand row. */
.sidebar-rail {
  display: flex;
  width: 100%;
  height: 100%;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid hsl(var(--sidebar-border));
  background: hsl(var(--sidebar));
  color: hsl(var(--sidebar-foreground));
  user-select: none;
}

.sidebar-brand {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  min-height: var(--app-titlebar-height);
  padding: 0 0.85rem;
  border-bottom: 1px solid hsl(var(--sidebar-border) / 0.9);
}

.sidebar-brand.is-collapsed {
  justify-content: center;
  padding-inline: 0.375rem;
}

.sidebar-brand__link {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 0.55rem;
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
  font-size: var(--app-text-xl);
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
  gap: 0.15rem;
  padding: 0.55rem 0.75rem;
}

.sidebar-top-nav {
  padding-top: 0.7rem;
  padding-bottom: 0.3rem;
}

.sidebar-footer {
  border-top: 1px solid hsl(var(--sidebar-border) / 0.9);
  padding-top: 0.55rem;
  padding-bottom: 0.7rem;
}

.sidebar-nav {
  min-height: 0;
  flex: 1 1 auto;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 0.3rem 0.75rem 0.8rem;
  transition: padding-bottom var(--duration-base) var(--ease-out);
}

.sidebar-rail.has-player .sidebar-nav {
  padding-bottom: calc(0.75rem + var(--sidebar-player-height));
}

.sidebar-group + .sidebar-group {
  margin-top: 0.85rem;
  padding-top: 0.7rem;
  border-top: 1px solid hsl(var(--sidebar-border) / 0.7);
}

.sidebar-group__label {
  margin: 0 0 0.3rem;
  padding: 0.125rem 0.8rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  font-weight: 650;
  letter-spacing: 0.01em;
  line-height: 1.4;
  white-space: nowrap;
}

.sidebar-group__label--collapsed {
  display: none;
}

.sidebar-group__items {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
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
.sidebar-rail { border-right-color: hsl(var(--border)); background: hsl(var(--sidebar)); }
.sidebar-brand { min-height: 3.5rem; border-bottom-color: hsl(var(--border)); padding-inline: 1.125rem; }
.sidebar-brand__mark { color: hsl(var(--primary)); }
.sidebar-brand__name { color: hsl(var(--foreground)); letter-spacing: 0; }
.sidebar-top-nav, .sidebar-footer { padding-inline: 0.75rem; }
.sidebar-group + .sidebar-group { border-top-color: hsl(var(--border) / 0.7); }
.sidebar-group__label { color: hsl(var(--muted-foreground)); font-size: var(--app-text-xs); letter-spacing: 0.08em; text-transform: uppercase; }
.sidebar-footer { border-top-color: hsl(var(--border)); }
@media (max-width: 640px) {
  .sidebar-brand { padding-inline: 0.75rem; }
}
 </style>
