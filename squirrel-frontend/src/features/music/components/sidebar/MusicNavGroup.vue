<template>
  <section class="music-nav-group">
    <header class="music-nav-header" @click="toggleExpand">
      <h3 class="music-nav-title">{{ title }}</h3>
      <AppIcon
        v-if="collapsible"
        name="chevronDown"
        class="h-3.5 w-3.5 music-nav-chevron"
        :class="{ 'music-nav-chevron--expanded': isExpanded }"
      />
    </header>

    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      leave-active-class="transition-all duration-150 ease-in"
      enter-from-class="opacity-0 -translate-y-2"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <nav v-show="isExpanded" class="music-nav-list">
        <MusicNavItem
          v-for="item in items"
          :key="item.id"
          :item="item"
          :active="activeId === item.id"
          @click="$emit('select', item.id)"
        />
        <slot />
      </nav>
    </Transition>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'
import MusicNavItem from './MusicNavItem.vue'

interface NavItem {
  id: string
  label: string
  icon: AppIconName
}

const props = withDefaults(defineProps<{
  title: string
  items: NavItem[]
  activeId?: string
  collapsible?: boolean
  defaultExpanded?: boolean
}>(), {
  collapsible: false,
  defaultExpanded: true,
})

defineEmits<{
  select: [id: string]
}>()

const isExpanded = ref(props.defaultExpanded)

watch(() => props.defaultExpanded, (val) => {
  isExpanded.value = val
})

function toggleExpand() {
  if (props.collapsible) {
    isExpanded.value = !isExpanded.value
  }
}
</script>

<style scoped>
.music-nav-group {
  padding: 0.5rem 0;
}

.music-nav-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.375rem 1.25rem;
  cursor: default;
}

.music-nav-title {
  font-size: 0.625rem;
  font-weight: 700;
  color: hsl(var(--muted-foreground) / 0.7);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.music-nav-chevron {
  color: hsl(var(--muted-foreground) / 0.5);
  transition: transform 0.2s ease;
}

.music-nav-chevron--expanded {
  transform: rotate(180deg);
}

.music-nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
</style>
