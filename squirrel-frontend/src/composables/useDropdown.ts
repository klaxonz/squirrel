import { onMounted, onUnmounted, ref } from 'vue'

type UseDropdownOptions = {
  closeOnEscape?: boolean
}

export function useDropdown(options: UseDropdownOptions = {}) {
  const { closeOnEscape = false } = options
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

  const handleEscKey = (event: KeyboardEvent) => {
    if (!closeOnEscape) return
    if (event.key === 'Escape') {
      isOpen.value = false
    }
  }

  onMounted(() => {
    document.addEventListener('click', handleClickOutside)
    if (closeOnEscape) {
      document.addEventListener('keydown', handleEscKey)
    }
  })

  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
    if (closeOnEscape) {
      document.removeEventListener('keydown', handleEscKey)
    }
  })

  return { isOpen, rootRef, toggle, close }
}


