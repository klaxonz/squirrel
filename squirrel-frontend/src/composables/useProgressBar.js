// 进度条与拖拽交互封装
import { ref } from 'vue';
import { debounce } from '../utils/debounce';

export default function useProgressBar(playerState, getters, setters) {
  const { getDuration } = getters;
  const { setVideoTime } = setters;

  const handleProgressHover = (e) => {
    try {
      if (!e || !e.currentTarget) return;
      playerState.ui.hoveringProgress = true;
      const rect = e.currentTarget.getBoundingClientRect();
      const position = ((e.clientX - rect.left) / rect.width) * 100;
      playerState.ui.hoverPosition = Math.min(Math.max(position, 0), 100);

      const duration = playerState.media.duration || getDuration() || 0;
      if (duration > 0) {
        if (playerState.ui.isDragging) {
          playerState.ui.previewTime = playerState.ui.previewSeekTime || 0;
        } else {
          playerState.ui.previewTime = (duration * position) / 100;
        }
      }
    } catch (err) {
      // 静默
    }
  };

  const debouncedProgressHover = debounce(handleProgressHover, 5);

  const handleProgressLeave = () => {
    playerState.ui.hoveringProgress = false;
  };

  const handleProgressMouseDown = (e) => {
    e.preventDefault();
    playerState.ui.isDragging = true;
    const rect = e.currentTarget.getBoundingClientRect();

    const updatePreview = (clientX) => {
      const position = (clientX - rect.left) / rect.width;
      playerState.ui.previewSeekTime = playerState.media.duration * Math.min(Math.max(position, 0), 1);
      playerState.ui.hoverPosition = position * 100;
    };

    updatePreview(e.clientX);

    const handleMouseMove = (ev) => {
      if (!playerState.ui.isDragging) return;
      updatePreview(ev.clientX);
    };

    const handleMouseUp = () => {
      playerState.ui.isDragging = false;
      setVideoTime(playerState.ui.previewSeekTime);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  const handleProgressTouchStart = (e) => {
    e.preventDefault();
    playerState.ui.isDragging = true;
    const rect = e.currentTarget.getBoundingClientRect();
    const position = (e.touches[0].clientX - rect.left) / rect.width;
    playerState.ui.previewSeekTime = playerState.media.duration * Math.min(Math.max(position, 0), 1);
    playerState.ui.hoverPosition = position * 100;
    playerState.ui.hoveringProgress = true;
  };

  const handleProgressTouchMove = (e) => {
    e.preventDefault();
    if (!playerState.ui.isDragging) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const position = (e.touches[0].clientX - rect.left) / rect.width;
    const boundedPosition = Math.min(Math.max(position, 0), 1);
    playerState.ui.previewSeekTime = playerState.media.duration * boundedPosition;
    playerState.ui.hoverPosition = boundedPosition * 100;
  };

  const handleProgressTouchEnd = () => {
    if (playerState.ui.isDragging) setVideoTime(playerState.ui.previewSeekTime);
    playerState.ui.isDragging = false;
    playerState.ui.hoveringProgress = false;
  };

  const cleanup = () => {
    if (typeof debouncedProgressHover?.cancel === 'function') {
      debouncedProgressHover.cancel();
    }
  };

  return {
    debouncedProgressHover,
    handleProgressLeave,
    handleProgressMouseDown,
    handleProgressTouchStart,
    handleProgressTouchMove,
    handleProgressTouchEnd,
    cleanup
  };
}


