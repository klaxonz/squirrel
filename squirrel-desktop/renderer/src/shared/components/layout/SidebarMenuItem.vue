<template>
  <RouterLink
    :to="targetPath"
    :replace="!item.resolvePath"
    custom
    v-slot="{ href, navigate }"
  >
    <a
      :href="href"
      class="sidebar-item"
      :class="{ 'is-active': isActive, 'is-collapsed': collapsed }"
      :aria-current="isActive ? 'page' : undefined"
      :title="collapsed ? item.name : undefined"
      @click="handleClick($event, navigate)"
    >
      <AppIcon
        :name="item.icon"
        class="sidebar-item__icon"
        :stroke-width="isActive ? 2 : 1.75"
      />
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

  void navigate(event)
}
</script>

<style scoped>
.sidebar-item {
  position: relative;
  display: flex;
  width: 100%;
  min-height: 2.25rem;
  align-items: center;
  gap: 0.7rem;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 0 0.625rem;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 520;
  line-height: 1.2;
  text-decoration: none;
  outline: none;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.sidebar-item:hover {
  background: hsl(var(--accent) / 0.56);
  color: hsl(var(--foreground));
}

.sidebar-item:focus-visible {
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.46);
}

.sidebar-item.is-active {
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--foreground));
  font-weight: 620;
}

.sidebar-item.is-collapsed {
  justify-content: center;
  gap: 0;
  padding-inline: 0;
}

.sidebar-item.is-collapsed .sidebar-item__label {
  display: none;
}

.sidebar-item__icon {
  width: var(--sidebar-icon-size);
  height: var(--sidebar-icon-size);
  flex: 0 0 auto;
  color: hsl(var(--muted-foreground));
}

.sidebar-item.is-active .sidebar-item__icon {
  color: hsl(var(--primary));
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
