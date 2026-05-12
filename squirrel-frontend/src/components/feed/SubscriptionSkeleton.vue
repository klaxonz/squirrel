<template>
  <div class="skeleton-card" :style="{ animationDelay: `${delay}ms`, '--skeleton-delay': `${delay}ms` }">
    <div class="skeleton-header">
      <div class="skeleton-avatar skeleton-surface"></div>

      <div class="skeleton-main">
        <div class="skeleton-name-row">
          <div class="skeleton-name skeleton-surface"></div>
          <div class="skeleton-badge skeleton-surface"></div>
        </div>
        <div class="skeleton-meta">
          <div class="skeleton-status skeleton-surface"></div>
          <div class="skeleton-dot"></div>
          <div class="skeleton-date skeleton-surface"></div>
        </div>
      </div>

      <div class="skeleton-stats">
        <div class="skeleton-stat skeleton-surface"></div>
        <div class="skeleton-stat-sep"></div>
        <div class="skeleton-stat skeleton-surface"></div>
      </div>

      <div class="skeleton-actions">
        <div class="skeleton-action skeleton-surface"></div>
        <div class="skeleton-action skeleton-surface"></div>
      </div>
    </div>

    <div class="skeleton-recent-grid">
      <div v-for="i in 10" :key="i" class="skeleton-recent-card">
        <div class="skeleton-recent-thumb skeleton-surface"></div>
        <div class="skeleton-recent-title skeleton-surface"></div>
        <div class="skeleton-recent-meta skeleton-surface"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  delay: {
    type: Number,
    default: 0,
  },
})
</script>

<style scoped>
.skeleton-card {
  background: hsl(var(--background));
  overflow: hidden;
  animation: skeleton-appear var(--duration-slower) var(--ease-default) forwards;
  opacity: 0;
}

.skeleton-header {
  display: grid;
  grid-template-columns: 3rem 1fr auto auto;
  align-items: center;
  gap: 0 1.25rem;
  padding: 0.875rem 1rem;
}

@keyframes skeleton-appear {
  from { opacity: 0; }
  to { opacity: 1; }
}

.skeleton-surface {
  position: relative;
  overflow: hidden;
}

.skeleton-surface::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, hsl(var(--primary) / 0.03), transparent);
  transform: translateX(-100%);
  animation: shimmer 1.6s ease-in-out infinite;
  animation-delay: var(--skeleton-delay, 0ms);
}

.skeleton-avatar {
  width: 2.75rem;
  height: 2.75rem;
  background: hsl(var(--secondary) / 0.25);
  border: 1px solid hsl(var(--border) / 0.3);
  border-radius: 9999px;
}

.skeleton-main {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}

.skeleton-name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.skeleton-name {
  height: 0.9rem;
  width: 8rem;
  background: hsl(var(--secondary) / 0.2);
  border-radius: 3px;
}

.skeleton-badge {
  height: 0.75rem;
  width: 3rem;
  background: hsl(var(--secondary) / 0.18);
  border-radius: 3px;
}

.skeleton-meta {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.skeleton-status {
  height: 0.65rem;
  width: 3.5rem;
  background: hsl(var(--secondary) / 0.18);
  border-radius: 999px;
}

.skeleton-dot {
  width: 3px;
  height: 3px;
  background: hsl(var(--border) / 0.5);
  border-radius: 50%;
}

.skeleton-date {
  height: 0.6rem;
  width: 4rem;
  background: hsl(var(--secondary) / 0.18);
  border-radius: 2px;
}

.skeleton-stats {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 0 0.5rem;
}

.skeleton-stat {
  width: 2.5rem;
  height: 1.4rem;
  background: hsl(var(--secondary) / 0.2);
  border-radius: 3px;
}

.skeleton-stat-sep {
  width: 1px;
  height: 1.5rem;
  background: hsl(var(--border) / 0.3);
}

.skeleton-actions {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  opacity: 0.35;
}

.skeleton-action {
  width: 1.75rem;
  height: 1.75rem;
  background: hsl(var(--secondary) / 0.15);
  border-radius: calc(var(--radius-sm) - 1px);
}

.skeleton-recent-grid {
  display: flex;
  gap: 0.45rem;
  padding: 0.1rem 1rem 0.75rem;
  overflow-x: hidden;
}

.skeleton-recent-card {
  width: 10rem;
  min-width: 10rem;
  max-width: 10rem;
  box-sizing: border-box;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  padding: 0.2rem;
}

.skeleton-recent-thumb {
  width: 100%;
  height: 5.4rem;
  border-radius: calc(var(--radius-sm) - 1px);
  background: hsl(var(--secondary) / 0.5);
}

.skeleton-recent-title {
  margin-top: 0.28rem;
  height: 0.64rem;
  width: 82%;
  border-radius: 3px;
  background: hsl(var(--secondary) / 0.22);
}

.skeleton-recent-meta {
  margin-top: 0.12rem;
  height: 0.52rem;
  width: 46%;
  border-radius: 3px;
  background: hsl(var(--secondary) / 0.18);
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@media (max-width: 960px) {
  .skeleton-header {
    grid-template-columns: 2.5rem 1fr auto;
    grid-template-rows: auto auto;
    gap: 0 0.75rem;
    padding: 0.75rem;
  }

  .skeleton-avatar {
    width: 2.25rem;
    height: 2.25rem;
  }

  .skeleton-stats {
    gap: 0.75rem;
    padding: 0;
  }

  .skeleton-stat {
    width: 2rem;
  }

  .skeleton-actions {
    grid-column: 2 / 4;
    opacity: 1;
    padding-top: 0.25rem;
    justify-content: flex-start;
  }

  .skeleton-recent-grid {
    padding: 0 0.75rem 0.75rem;
  }
}
</style>
