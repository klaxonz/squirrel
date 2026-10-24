<template>
  <RouterLink
    v-slot="{ href, navigate }"
    :to="targetPath"
    custom
  >
    <a
      :href="href"
      class="sidebar-item"
      data-hover-fill-item
      :class="{ 'is-active': isActive, 'is-collapsed': collapsed }"
      :aria-current="isActive ? 'page' : undefined"
      :title="collapsed ? item.name : undefined"
      @click="(event) => handleClick(event, navigate)"
    >
      <span class="sidebar-item__icon-wrap" aria-hidden="true">
        <AppIcon
          :name="item.icon"
          class="sidebar-item__icon"
          :stroke-width="isActive ? 2.25 : 1.75"
        />
      </span>
      <span class="sidebar-item__label">{{ item.name }}</span>
    </a>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import {
  isNavigationHistoryEntryForItem,
  type NavigationItem,
} from '@/shared/constants/sidebar'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'

const props = defineProps<{
  item: NavigationItem
  isActive: boolean
  collapsed?: boolean
}>()

const route = useRoute()
const nav = useNavigationHistory()
const targetPath = computed(() => props.item.resolvePath?.(route.path) ?? props.item.path)
const previousEntry = computed(() => nav.findBackEntry((entry) => (
  isNavigationHistoryEntryForItem(props.item, entry)
)) ?? null)

type RouterNavigate = (event?: MouseEvent) => unknown

const handleClick = (event: MouseEvent, navigate: RouterNavigate) => {
  if (
    event.defaultPrevented
    || event.button !== 0
    || event.metaKey
    || event.ctrlKey
    || event.shiftKey
    || event.altKey
  ) return

  // Sidebar sections behave like persistent workspaces. When the requested
  // section already exists in app history (most notably list → playback),
  // return to that exact entry so its filters, loaded pages and scroll roots
  // survive. A genuinely new section still follows the RouterLink target.
  const entry = previousEntry.value
  if (entry && route.fullPath !== entry.fullPath) {
    event.preventDefault()
    nav.jumpTo(entry.id)
    return
  }

  // Re-clicking the section the user is already on must be a no-op: a plain
  // RouterLink push would add a duplicate browser-history entry that the app
  // stack cannot pop (reenteringSamePath replaces in place), silently breaking
  // Back until the page reloads.
  if (route.fullPath === targetPath.value) {
    event.preventDefault()
    return
  }

  void navigate(event)
}
</script>

<style scoped>
/*
  Nav row:
  - shared hover fill travels between siblings; the row itself paints no hover
  - active is a quiet ink wash, never brand color
*/
.sidebar-item {
  position: relative;
  display: flex;
  width: 100%;
  min-height: var(--sidebar-item-height);
  height: var(--sidebar-item-height);
  align-items: center;
  gap: 0.65rem;
  overflow: hidden;
  border: 0;
  border-radius: var(--radius-md);
  padding: 0 0.75rem 0 0.6rem;
  background: transparent;
  color: hsl(var(--foreground) / 0.86);
  font-size: var(--app-text-md);
  font-weight: 500;
  line-height: 1;
  text-decoration: none;
  outline: none;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default),
    box-shadow var(--duration-fast) var(--ease-default);
}

.sidebar-item:hover {
  background: var(--app-row-hover-bg);
  color: hsl(var(--foreground));
}

.sidebar-item:focus-visible {
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.8);
}

.sidebar-item.is-active {
  background: var(--app-selection-bg);
  color: hsl(var(--foreground));
  font-weight: 600;
}

.sidebar-item.is-collapsed {
  justify-content: center;
  gap: 0;
  width: 2.25rem;
  height: 2.25rem;
  min-height: 2.25rem;
  margin-inline: auto;
  padding: 0;
  border-radius: var(--radius-md);
}

.sidebar-item.is-collapsed .sidebar-item__label {
  display: none;
}

.sidebar-item__icon-wrap {
  display: inline-flex;
  width: 1.25rem;
  height: 1.25rem;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  color: currentColor;
}

.sidebar-item.is-active .sidebar-item__icon-wrap {
  color: hsl(var(--foreground));
}

.sidebar-item__icon {
  width: var(--sidebar-icon-size);
  height: var(--sidebar-icon-size);
  flex: 0 0 auto;
  color: currentColor;
  opacity: 0.92;
}

.sidebar-item.is-active .sidebar-item__icon {
  opacity: 1;
}

.sidebar-item__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .sidebar-item {
    transition: none;
  }
}
</style>
