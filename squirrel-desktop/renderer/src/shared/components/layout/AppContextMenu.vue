<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-150"
      leave-active-class="transition-opacity duration-100"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="visible"
        ref="rootRef"
        role="menu"
        :aria-label="label"
        :class="cn('app-context-menu', props.class)"
        :style="{ left: position.x + 'px', top: position.y + 'px', width }"
        @click.stop
        @contextmenu.stop
      >
        <div class="app-context-menu__list">
          <slot />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { onUnmounted, ref, watch } from 'vue'
import { cn } from '@/shared/lib/utils'

const props = withDefaults(defineProps<{
  visible: boolean
  position: { x: number; y: number }
  label: string
  width?: string
  class?: HTMLAttributes['class']
}>(), {
  width: '12.5rem',
})

const emit = defineEmits<{
  close: []
}>()

const rootRef = ref<HTMLElement | null>(null)
let listening = false

const handlePointerDown = (event: PointerEvent) => {
  if (!props.visible) return
  const target = event.target as Node | null
  if (target && rootRef.value?.contains(target)) return
  emit('close')
}

const handleKeydown = (event: KeyboardEvent) => {
  if (props.visible && event.key === 'Escape') emit('close')
}

const startListening = () => {
  if (listening) return
  window.addEventListener('pointerdown', handlePointerDown, true)
  window.addEventListener('keydown', handleKeydown)
  listening = true
}

const stopListening = () => {
  if (!listening) return
  window.removeEventListener('pointerdown', handlePointerDown, true)
  window.removeEventListener('keydown', handleKeydown)
  listening = false
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      startListening()
    } else {
      stopListening()
    }
  },
  { immediate: true },
)

onUnmounted(stopListening)

defineExpose({ rootRef })
</script>

<style scoped>
.app-context-menu {
  position: fixed;
  z-index: var(--z-dropdown);
  padding: 0.375rem;
  border: 1px solid hsl(var(--border) / 0.36);
  border-radius: var(--radius-lg);
  background: hsl(var(--popover));
  color: hsl(var(--popover-foreground));
  box-shadow: var(--app-floating-shadow);
}

.app-context-menu__list {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}
</style>
