import { ref, onMounted, onUnmounted } from 'vue';

export function useDropdown() {
  const isOpen = ref(false);
  const rootRef = ref(null);

  const toggle = () => {
    isOpen.value = !isOpen.value;
  };

  const close = () => {
    isOpen.value = false;
  };

  const handleClickOutside = (event) => {
    const root = rootRef.value;
    if (!root) return;
    if (!root.contains(event.target)) {
      isOpen.value = false;
    }
  };

  onMounted(() => {
    document.addEventListener('click', handleClickOutside);
  });

  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside);
  });

  return { isOpen, rootRef, toggle, close };
}


