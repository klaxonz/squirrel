import { onMounted, onUnmounted, ref } from 'vue';

export function useRefreshTriggers({ onRefresh, visibilityThresholdMs = 5 * 60 * 1000 }) {
  const lastRefreshedAt = ref(Date.now());

  const handleKeyDown = (e) => {
    const target = e.target;
    if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if ((e.key === 'r' || e.key === 'R') && !e.repeat) {
      e.preventDefault();
      onRefresh?.();
      lastRefreshedAt.value = Date.now();
    }
  };

  const handleVisibilityChange = () => {
    if (!document.hidden) {
      if (Date.now() - lastRefreshedAt.value > visibilityThresholdMs) {
        onRefresh?.();
        lastRefreshedAt.value = Date.now();
      }
    }
  };

  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown);
    document.addEventListener('visibilitychange', handleVisibilityChange);
  });

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown);
    document.removeEventListener('visibilitychange', handleVisibilityChange);
  });

  return {
    lastRefreshedAt,
  };
}


