// 进度条与拖拽交互封装

export default function useProgressBar(playerState, getters, setters) {
  const { setVideoTime } = setters;

  const handleProgressMouseDown = (e) => {
    e.preventDefault();
    playerState.ui.isDragging = true;
    const rect = e.currentTarget.getBoundingClientRect();

    const calculateSeekTime = (clientX) => {
      const position = (clientX - rect.left) / rect.width;
      return playerState.media.duration * Math.min(Math.max(position, 0), 1);
    };

    const seekTime = calculateSeekTime(e.clientX);
    setVideoTime(seekTime);

    const handleMouseMove = (ev) => {
      if (!playerState.ui.isDragging) return;
      const newSeekTime = calculateSeekTime(ev.clientX);
      setVideoTime(newSeekTime);
    };

    const handleMouseUp = () => {
      playerState.ui.isDragging = false;
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
    const seekTime = playerState.media.duration * Math.min(Math.max(position, 0), 1);
    setVideoTime(seekTime);
  };

  const handleProgressTouchMove = (e) => {
    e.preventDefault();
    if (!playerState.ui.isDragging) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const position = (e.touches[0].clientX - rect.left) / rect.width;
    const seekTime = playerState.media.duration * Math.min(Math.max(position, 0), 1);
    setVideoTime(seekTime);
  };

  const handleProgressTouchEnd = () => {
    playerState.ui.isDragging = false;
  };

  return {
    handleProgressMouseDown,
    handleProgressTouchStart,
    handleProgressTouchMove,
    handleProgressTouchEnd
  };
}


