import { onMounted, onUnmounted, ref } from 'vue'

export function useDropdown() {
  const isOpen = ref(false)
  const rootRef = ref<HTMLElement | null>(null)

  const toggle = () => {
    isOpen.value = !isOpen.value
  }

  const close = () => {
    isOpen.value = false
  }

  const handleClickOutside = (event: MouseEvent) => {
    const root = rootRef.value
    if (!root) return
    if (!(event.target instanceof Node)) return
    if (!root.contains(event.target)) {
      isOpen.value = false
    }
  }

  onMounted(() => {
    document.addEventListener('click', handleClickOutside)
  })

  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
  })

  return { isOpen, rootRef, toggle, close }
}


