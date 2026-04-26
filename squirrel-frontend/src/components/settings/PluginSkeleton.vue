<template>
  <tr class="plugin-skeleton-item" :style="{ animationDelay: `${delay}ms` }" aria-hidden="true">
    <td class="col-icon skeleton-cell">
      <div class="skeleton-surface skeleton-icon"></div>
    </td>
    <td class="col-name skeleton-cell">
      <div class="skeleton-name-stack">
        <div class="skeleton-surface skeleton-text skeleton-text--primary" :style="{ width: nameWidth }"></div>
        <div class="skeleton-surface skeleton-text skeleton-text--secondary" :style="{ width: metaWidth }"></div>
      </div>
    </td>
    <td class="col-status skeleton-cell">
      <div class="skeleton-surface skeleton-badge" :style="{ width: statusWidth }"></div>
    </td>
    <td class="col-caps skeleton-cell">
      <div class="skeleton-caps">
        <div
          v-for="(capWidth, index) in caps"
          :key="`${capWidth}-${index}`"
          class="skeleton-surface skeleton-tag"
          :style="{ width: capWidth }"
        ></div>
      </div>
    </td>
    <td class="col-endpoint skeleton-cell">
      <div class="skeleton-surface skeleton-text skeleton-text--mono" :style="{ width: endpointWidth }"></div>
    </td>
    <td class="col-site-access skeleton-cell">
      <div class="skeleton-status-inline">
        <div class="skeleton-surface skeleton-status-dot"></div>
        <div class="skeleton-surface skeleton-text skeleton-text--compact" :style="{ width: networkWidth }"></div>
      </div>
    </td>
    <td class="col-site-login skeleton-cell">
      <div class="skeleton-status-inline">
        <div class="skeleton-surface skeleton-status-dot"></div>
        <div class="skeleton-surface skeleton-text skeleton-text--compact" :style="{ width: loginWidth }"></div>
      </div>
    </td>
    <td class="col-actions skeleton-cell">
      <div class="skeleton-actions">
        <div
          v-for="index in actionCount"
          :key="index"
          class="skeleton-surface skeleton-action-btn"
        ></div>
      </div>
    </td>
  </tr>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  delay: {
    type: Number,
    default: 0,
  },
  nameWidth: {
    type: String,
    default: '8.25rem',
  },
  metaWidth: {
    type: String,
    default: '5.5rem',
  },
  statusWidth: {
    type: String,
    default: '3.25rem',
  },
  caps: {
    type: Array,
    default: () => ['2.75rem', '3.5rem'],
  },
  endpointWidth: {
    type: String,
    default: '8rem',
  },
  networkWidth: {
    type: String,
    default: '2.75rem',
  },
  loginWidth: {
    type: String,
    default: '3rem',
  },
  actions: {
    type: Number,
    default: 6,
  },
})

const actionCount = computed(() => Math.max(1, props.actions))
</script>

<style scoped>
.plugin-skeleton-item {
  animation: skeleton-appear var(--duration-slower) var(--ease-default) forwards;
  opacity: 0;
  background: hsl(var(--card) / 0.1);
}

@keyframes skeleton-appear {
  from { opacity: 0; }
  to { opacity: 1; }
}

.plugin-skeleton-item > td {
  vertical-align: middle;
}

.skeleton-cell {
  padding: 0.75rem 0.75rem;
  border-bottom: 1px solid hsl(var(--border) / 0.15);
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.skeleton-surface {
  position: relative;
  overflow: hidden;
  border-radius: 0.5rem;
  background: linear-gradient(
    180deg,
    hsl(var(--foreground) / 0.06),
    hsl(var(--foreground) / 0.03)
  );
  border: 1px solid hsl(var(--border) / 0.12);
}

.skeleton-surface::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    hsl(var(--foreground) / 0.05),
    transparent
  );
  animation: shimmer 1.8s infinite;
}

.skeleton-icon {
  width: 2rem;
  height: 2rem;
}

.skeleton-name-stack {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.skeleton-text {
  height: 0.72rem;
  border-radius: 3px;
}

.skeleton-text--primary {
  height: 0.8rem;
}

.skeleton-text--secondary {
  height: 0.62rem;
  opacity: 0.8;
}

.skeleton-text--mono,
.skeleton-text--compact,
.skeleton-badge,
.skeleton-tag,
.skeleton-status-dot {
  border-radius: 999px;
}

.skeleton-text--mono {
  height: 0.68rem;
}

.skeleton-text--compact {
  height: 0.7rem;
}

.skeleton-badge {
  height: 1.25rem;
}

.skeleton-caps {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.skeleton-tag {
  height: 1rem;
}

.skeleton-status-inline {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.skeleton-status-dot {
  width: 0.75rem;
  height: 0.75rem;
}

.skeleton-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.25rem;
}

.skeleton-action-btn {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: calc(var(--radius-sm) - 1px);
}

.col-icon { width: 2.5rem; text-align: center; }
.col-name { min-width: 160px; }
.col-status { min-width: 70px; }
.col-caps { min-width: 120px; }
.col-endpoint { min-width: 180px; }
.col-site-access { min-width: 90px; }
.col-site-login { min-width: 80px; }
.col-actions { width: 120px; text-align: right; }

@media (max-width: 768px) {
  .skeleton-cell {
    padding-top: 0.625rem;
    padding-bottom: 0.625rem;
  }

  .col-endpoint,
  .col-caps {
    display: none;
  }
}
</style>
