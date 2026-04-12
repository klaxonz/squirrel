<template>
  <div class="plugin-skeleton-item" :style="{ animationDelay: `${delay}ms` }">
    <div class="skeleton-row">
      <div class="col-icon">
        <div class="skeleton-icon"></div>
      </div>
      <div class="col-name">
        <div class="skeleton-text w-32"></div>
      </div>
      <div class="col-status">
        <div class="skeleton-badge"></div>
      </div>
      <div class="col-caps">
        <div class="skeleton-tag"></div>
        <div class="skeleton-tag ml-1"></div>
      </div>
      <div class="col-endpoint">
        <div class="skeleton-text w-24"></div>
      </div>
      <div class="col-site-access">
        <div class="skeleton-text w-12"></div>
      </div>
      <div class="col-site-login">
        <div class="skeleton-text w-10"></div>
      </div>
      <div class="col-actions">
        <div class="skeleton-action-btn"></div>
        <div class="skeleton-action-btn"></div>
        <div class="skeleton-action-btn"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  delay: {
    type: Number,
    default: 0,
  },
})
</script>

<style scoped>
.plugin-skeleton-item {
  animation: skeleton-appear 0.4s ease-out forwards;
  opacity: 0;
}

@keyframes skeleton-appear {
  from { opacity: 0; }
  to { opacity: 1; }
}

.skeleton-row {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.625rem 0.75rem;
  box-sizing: border-box;
  border-bottom: 1px solid hsl(var(--border) / 0.15);
}

.shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    hsl(var(--foreground) / 0.04),
    transparent
  );
  animation: shimmer 1.8s infinite;
  border-radius: inherit;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.skeleton-icon {
  width: 2rem;
  height: 2rem;
  background: hsl(var(--foreground) / 0.05);
  border-radius: 0.5rem;
  position: relative;
  overflow: hidden;
}

.skeleton-icon::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    hsl(var(--foreground) / 0.04),
    transparent
  );
  animation: shimmer 1.8s infinite;
}

.skeleton-text {
  height: 12px;
  background: hsl(var(--foreground) / 0.06);
  border-radius: 3px;
  position: relative;
  overflow: hidden;
}

.skeleton-text::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    hsl(var(--foreground) / 0.04),
    transparent
  );
  animation: shimmer 1.8s infinite;
}

.skeleton-badge {
  width: 40px;
  height: 18px;
  background: hsl(var(--foreground) / 0.05);
  border-radius: 3px;
  position: relative;
  overflow: hidden;
}

.skeleton-badge::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    hsl(var(--foreground) / 0.04),
    transparent
  );
  animation: shimmer 1.8s infinite;
}

.skeleton-tag {
  display: inline-block;
  width: 36px;
  height: 16px;
  background: hsl(var(--foreground) / 0.04);
  border-radius: 3px;
  position: relative;
  overflow: hidden;
}

.skeleton-tag::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    hsl(var(--foreground) / 0.04),
    transparent
  );
  animation: shimmer 1.8s infinite;
}

.skeleton-action-btn {
  width: 1.75rem;
  height: 1.75rem;
  background: hsl(var(--foreground) / 0.04);
  border-radius: calc(var(--radius-sm) - 1px);
  position: relative;
  overflow: hidden;
}

.skeleton-action-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    hsl(var(--foreground) / 0.04),
    transparent
  );
  animation: shimmer 1.8s infinite;
}

/* Column widths matching table */
.col-icon { width: 2.5rem; text-align: center; }
.col-name {
  min-width: 160px;
  flex: 1 1 0;
}
.col-status { min-width: 70px; }
.col-caps {
  min-width: 120px;
  flex: 1 1 0;
}
.col-endpoint {
  min-width: 180px;
  flex: 1 1 0;
}
.col-site-access { min-width: 90px; }
.col-site-login { min-width: 80px; }
.col-actions { width: 120px; text-align: right; }

.w-32 { width: 8rem; }
.w-24 { width: 6rem; }
.w-20 { width: 5rem; }
.w-12 { width: 3rem; }
.w-10 { width: 2.5rem; }
.mt-2 { margin-top: 0.5rem; }
.ml-1 { margin-left: 0.25rem; }
</style>
