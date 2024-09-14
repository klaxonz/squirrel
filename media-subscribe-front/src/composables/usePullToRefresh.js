import { ref } from 'vue';

export default function usePullToRefresh(refreshContent, refreshHeight, showRefreshIndicator, activeScrollContent) {
  let startY = 0;
  let currentY = 0;
  const isRefreshing = ref(false);

  const handleTouchStart = (e) => {
    if (isRefreshing.value) return;
    startY = e.touches[0].clientY;
  };

  const handleTouchMove = (e) => {
    if (isRefreshing.value) return;
    if (!activeScrollContent.value || activeScrollContent.value.scrollTop > 0) {
      return;
    }

    currentY = e.touches[0].clientY;
    const diff = currentY - startY;

    if (diff > 0) {
      e.preventDefault();
      refreshHeight.value = Math.min(diff * 0.5, 60);
      showRefreshIndicator.value = true;
    }
  };

  const handleTouchEnd = () => {
    if (isRefreshing.value) return;
    if (refreshHeight.value >= 60) {
      isRefreshing.value = true;
      showRefreshIndicator.value = true;
      console.log('Starting refresh in usePullToRefresh');
      refreshContent().then(() => {
        console.log('Refresh completed in usePullToRefresh');
      }).catch(error => {
        console.error('Refresh error in usePullToRefresh:', error);
      }).finally(() => {
        console.log('Resetting refresh in usePullToRefresh');
        resetRefresh();
      });
    } else {
      resetRefresh();
    }
  };

  const resetRefresh = () => {
    console.log('Resetting refresh');
    const duration = 300; // 回弹动画持续时间（毫秒）
    const start = refreshHeight.value;
    const startTime = performance.now();

    function animate(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      refreshHeight.value = start * (1 - progress);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        refreshHeight.value = 0;
        showRefreshIndicator.value = false;
        isRefreshing.value = false;
        console.log('Reset completed');
      }
    }

    requestAnimationFrame(animate);
  };

  return {
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
    isRefreshing,
  };
}