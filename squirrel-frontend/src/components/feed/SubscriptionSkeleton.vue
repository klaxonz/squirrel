<template>
  <div class="subscription-skeleton-row" :style="{ animationDelay: `${delay}ms` }">
    <div class="subscription-row__media">
      <div class="skeleton-avatar"></div>
    </div>
    
    <div class="subscription-row__main">
      <div class="subscription-row__identity">
        <div class="skeleton-name w-32"></div>
        <div class="skeleton-tag w-12"></div>
      </div>
      <div class="subscription-row__meta">
        <div class="skeleton-text w-16"></div>
        <div class="skeleton-dot"></div>
        <div class="skeleton-text w-20"></div>
      </div>
    </div>

    <div class="subscription-row__stats">
      <div class="subscription-row__stat">
        <div class="skeleton-stat-value w-12"></div>
        <div class="skeleton-stat-label w-8"></div>
      </div>
      <div class="subscription-row__stat">
        <div class="skeleton-stat-value w-12"></div>
        <div class="skeleton-stat-label w-10"></div>
      </div>
    </div>

    <div class="subscription-row__actions">
      <div class="skeleton-action"></div>
    </div>
    
    <div class="shimmer"></div>
  </div>
</template>

<script setup>
defineProps({
  delay: {
    type: Number,
    default: 0
  }
})
</script>

<style scoped>
.subscription-skeleton-row {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1rem 0;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  position: relative;
  overflow: hidden;
  animation: skeleton-appear 0.5s ease-out forwards;
  opacity: 0;
}

@keyframes skeleton-appear {
  from { opacity: 0; transform: translateX(-10px); }
  to { opacity: 1; transform: translateX(0); }
}

.skeleton-avatar {
  width: 2.75rem;
  height: 2.75rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-sm);
}

.subscription-row__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.subscription-row__identity {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.skeleton-name {
  height: 1rem;
  background: rgba(255, 255, 255, 0.07);
  border-radius: 2px;
}

.skeleton-tag {
  height: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

.subscription-row__meta {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.skeleton-text {
  height: 0.6rem;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 2px;
}

.skeleton-dot {
  width: 3px;
  height: 3px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 50%;
}

.subscription-row__stats {
  display: none;
  gap: 3rem;
  margin: 0 2rem;
}

.subscription-row__stat {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
}

.skeleton-stat-value {
  height: 0.875rem;
  background: rgba(255, 255, 255, 0.07);
  border-radius: 2px;
}

.skeleton-stat-label {
  height: 0.55rem;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 2px;
}

.skeleton-action {
  width: 2rem;
  height: 2rem;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 50%;
}

.shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.03),
    transparent
  );
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@media (min-width: 768px) {
  .subscription-row__stats {
    display: flex;
  }
}
</style>
