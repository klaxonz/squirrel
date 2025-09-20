import { ref, onMounted, onUnmounted } from 'vue';

export default function useOptionsDropdown() {
  const showMoreOptions = ref(false);
  const menuRef = ref(null);

  const handleMoreOptionsClick = (event) => {
    event.stopPropagation();
    showMoreOptions.value = !showMoreOptions.value;
  };

  const handleClickOutside = (event) => {
    const el = menuRef.value;
    if (el && !el.contains(event.target)) {
      showMoreOptions.value = false;
    }
  };

  const handleEscKey = (event) => {
    if (event.key === 'Escape') {
      showMoreOptions.value = false;
    }
  };

  onMounted(() => {
    document.addEventListener('click', handleClickOutside);
    document.addEventListener('keydown', handleEscKey);
  });

  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside);
    document.removeEventListener('keydown', handleEscKey);
  });

  return {
    showMoreOptions,
    menuRef,
    handleMoreOptionsClick,
  };
}


