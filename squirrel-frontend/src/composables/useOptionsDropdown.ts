import { onMounted, onUnmounted, ref } from 'vue'

export default function useOptionsDropdown() {
  const showMoreOptions = ref(false)
  const menuRef = ref<HTMLElement | null>(null)

  const handleMoreOptionsClick = (event: MouseEvent) => {
    event.stopPropagation()
    showMoreOptions.value = !showMoreOptions.value
  }

  const handleClickOutside = (event: MouseEvent) => {
    const el = menuRef.value
    if (!el) return
    if (!(event.target instanceof Node)) return
    if (!el.contains(event.target)) {
      showMoreOptions.value = false
    }
  }

  const handleEscKey = (event: KeyboardEvent) => {
    if (event.key === 'Escape') {
      showMoreOptions.value = false
    }
  }

  onMounted(() => {
    document.addEventListener('click', handleClickOutside)
    document.addEventListener('keydown', handleEscKey)
  })

  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
    document.removeEventListener('keydown', handleEscKey)
  })

  return {
    showMoreOptions,
    menuRef,
    handleMoreOptionsClick,
  }
}


