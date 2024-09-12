import { ref } from 'vue';

export default function usePullToRefresh(refreshContent, refreshHeight, showRefreshIndicator) {
  const MAX_PULL_DISTANCE = 80;
  const REFRESH_THRESHOLD = 60;
  const RESISTANCE_FACTOR = 0.5;

  let initialTouchY = 0;
  let lastTouchY = 0;
  let pullStarted = false;
  const isAtTopStart = ref(true);

  const handleTouchStart = (event) => {
    initialTouchY = event.touches[0].clientY;
    lastTouchY = initialTouchY;
    pullStarted = false;
    isAtTopStart.value = event.target.scrollTop <= 1;
  };

  const handleTouchMove = (event) => {
    if (!isAtTopStart.value) return;

    const currentY = event.touches[0].clientY;
    const diffY = currentY - initialTouchY;

    if (diffY > 5 && !pullStarted) {
      pullStarted = true;
      event.preventDefault();
    }

    if (pullStarted) {
      const deltaY = currentY - lastTouchY;
      lastTouchY = currentY;

      if (refreshHeight.value + deltaY * RESISTANCE_FACTOR > 0) {
        refreshHeight.value = Math.max(0, Math.min(
          refreshHeight.value + deltaY * RESISTANCE_FACTOR,
          MAX_PULL_DISTANCE
        ));

        showRefreshIndicator.value = true;
        event.preventDefault();
      } else {
        resetPullToRefreshState();
      }
    }
  };

  const handleTouchEnd = () => {
    if (pullStarted) {
      if (refreshHeight.value >= REFRESH_THRESHOLD) {
        refreshContent(true);
      } else {
        resetPullToRefreshState();
      }
    }
  };

  const resetPullToRefreshState = () => {
    pullStarted = false;
    refreshHeight.value = 0;
    showRefreshIndicator.value = false;
  };

  return {
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
  };
}