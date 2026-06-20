<template>
  <div
    class="brand-logo flex items-center justify-center text-primary-foreground"
    :class="[sizeClass, roundedClass, props.class]"
    :style="{ backgroundImage: 'var(--brand-gradient)', boxShadow: glow }"
  >
    <AppIcon name="brand" :class="iconClass" />
  </div>
</template>

<script setup lang="ts">
/**
 * The product mark — caramel-amber gradient tile with the squirrel glyph.
 * Single source of truth for the brand visual, replacing 4 hand-inlined
 * copies (Login/Register/ServerConfig/Sidebar) that each re-declared the same
 * linear-gradient + box-shadow. The gradient + glow tokens live in
 * themes/dark.css (--brand-gradient / --brand-glow).
 */
import { computed } from 'vue'
import type { HTMLAttributes } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'

const props = withDefaults(defineProps<{
  /** Visual size preset. `sm` = sidebar rail (32px), `md` = auth/hero (48px). */
  size?: 'sm' | 'md'
  /** Extra classes merged onto the root (e.g. hover-scale interactions). */
  class?: HTMLAttributes['class']
}>(), {
  size: 'md',
})

const sizeClass = computed(() =>
  props.size === 'sm' ? 'w-8 h-8' : 'h-12 w-12',
)
const roundedClass = computed(() =>
  props.size === 'sm' ? 'rounded-lg' : 'rounded-xl',
)
const iconClass = computed(() =>
  props.size === 'sm' ? 'w-4 h-4' : 'h-6 w-6',
)
const glow = computed(() =>
  props.size === 'sm' ? 'var(--brand-glow-sm)' : 'var(--brand-glow)',
)
</script>
