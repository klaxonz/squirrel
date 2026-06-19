<template>
  <span class="music-playing-indicator">
    <i></i>
    <i></i>
    <i></i>
  </span>
</template>

<style scoped>
.music-playing-indicator {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 2px;
  height: 1rem;
}

.music-playing-indicator i {
  width: 3px;
  height: 100%;
  background: hsl(var(--primary));
  border-radius: 1px;
  animation: playing-bounce 0.6s ease-in-out infinite;
}

.music-playing-indicator i:nth-child(2) {
  animation-delay: 0.15s;
}

.music-playing-indicator i:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes playing-bounce {
  0%, 100% {
    transform: scaleY(0.4);
  }
  50% {
    transform: scaleY(1);
  }
}
</style>
