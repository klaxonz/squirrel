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
        @contextmenu.stop
        @click.stop="handleMenuClick"
        @keydown.stop="handleMenuKeydown"
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
import { nextTick, onUnmounted, ref, watch } from 'vue'
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
let previouslyFocused: HTMLElement | null = null
let typeaheadBuffer = ''
let typeaheadTimer: ReturnType<typeof setTimeout> | null = null

const menuItems = () => Array.from(
  rootRef.value?.querySelectorAll<HTMLElement>('[role="menuitem"], [role="menuitemradio"]') || [],
).filter((item) => !item.hasAttribute('disabled') && item.getAttribute('aria-disabled') !== 'true')

const focusItem = (index: number) => {
  const items = menuItems()
  if (!items.length) return
  const normalizedIndex = (index + items.length) % items.length
  items.forEach((item, itemIndex) => item.setAttribute('tabindex', itemIndex === normalizedIndex ? '0' : '-1'))
  items[normalizedIndex]?.focus()
}

const handleMenuClick = (event: MouseEvent) => {
  const target = event.target
  if (target instanceof Element && target.closest('[role="menuitem"], [role="menuitemradio"]')) {
    emit('close')
  }
}

const handleMenuKeydown = (event: KeyboardEvent) => {
  const items = menuItems()
  const activeIndex = items.findIndex((item) => item === document.activeElement)
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    focusItem(activeIndex + 1)
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    focusItem(activeIndex - 1)
    return
  }
  if (event.key === 'Home') {
    event.preventDefault()
    focusItem(0)
    return
  }
  if (event.key === 'End') {
    event.preventDefault()
    focusItem(items.length - 1)
    return
  }
  if (event.key === 'Tab') {
    emit('close')
    return
  }
  if (event.key.length !== 1 || event.ctrlKey || event.metaKey || event.altKey) return
  typeaheadBuffer += event.key.toLocaleLowerCase()
  if (typeaheadTimer) clearTimeout(typeaheadTimer)
  typeaheadTimer = setTimeout(() => {
    typeaheadBuffer = ''
    typeaheadTimer = null
  }, 500)
  const matchIndex = items.findIndex((item) => item.textContent?.trim().toLocaleLowerCase().startsWith(typeaheadBuffer))
  if (matchIndex >= 0) focusItem(matchIndex)
}

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

const restorePreviousFocus = () => {
  const target = previouslyFocused
  previouslyFocused = null
  if (target?.isConnected) target.focus({ preventScroll: true })
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null
      startListening()
      void nextTick(() => focusItem(0))
    } else {
      stopListening()
      restorePreviousFocus()
    }
  },
  { immediate: true },
)

onUnmounted(() => {
  stopListening()
  if (typeaheadTimer) clearTimeout(typeaheadTimer)
  restorePreviousFocus()
})

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
