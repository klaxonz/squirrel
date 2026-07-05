<template>
  <div ref="dropdownRef" class="account-dropdown">
    <button
      @click="$emit('toggle')"
      class="account-dropdown__trigger"
      :class="{ 'is-selected': selectedId }"
    >
      <div class="account-dropdown__trigger-label">
        <AppIcon name="rss" class="h-3.5 w-3.5 shrink-0 text-primary" />
        <span class="truncate">{{ selectedName || '选择账号...' }}</span>
      </div>
      <AppIcon
        name="chevronDown"
        class="account-dropdown__chevron"
        :class="{ 'rotate-180': open }"
      />
    </button>

    <div
      v-if="open"
      class="account-dropdown__menu"
    >
      <div class="account-dropdown__list custom-scrollbar">
        <div
          v-for="acc in accounts"
          :key="acc.id"
          @click="$emit('select', acc.id)"
          class="account-dropdown__item"
          :class="{ 'is-selected': selectedId === acc.id }"
        >
          <AppIcon name="rss" class="h-3.5 w-3.5 shrink-0 opacity-70" />
          <span class="account-dropdown__item-text">
            {{ acc.name }}
            <span class="account-dropdown__provider">({{ acc.provider }})</span>
          </span>
          <div class="account-dropdown__actions">
            <button
              @click.stop="$emit('edit', acc)"
              class="account-dropdown__icon-button"
              title="编辑账号"
            >
              <AppIcon name="pencil" class="h-3.5 w-3.5" />
            </button>
            <button
              @click.stop="$emit('delete', acc)"
              class="account-dropdown__icon-button account-dropdown__icon-button--danger"
              title="删除账号"
            >
              <AppIcon name="trash" class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
        <div v-if="!accounts.length" class="account-dropdown__empty">暂无账号</div>
        <div class="account-dropdown__separator"></div>
        <button
          @click="$emit('add')"
          class="account-dropdown__add"
        >
          <AppIcon name="plus" class="h-4 w-4" />
          添加服务账号
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { RssAccount } from '@/features/rss/composables/rssTypes'

defineProps<{
  accounts: RssAccount[]
  selectedId: number | null
  selectedName: string
  open: boolean
}>()

defineEmits<{
  toggle: []
  select: [id: number]
  edit: [acc: RssAccount]
  delete: [acc: RssAccount]
  add: []
}>()
</script>

<style scoped>
.account-dropdown {
  position: relative;
  width: 100%;
}

.account-dropdown__trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 2rem;
  padding: 0 0.625rem;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  background: hsl(var(--accent) / 0.4);
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 650;
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    border-color 0.16s ease;
}

.account-dropdown__trigger:hover {
  background: hsl(var(--accent) / 0.58);
  color: hsl(var(--foreground));
}

.account-dropdown__trigger.is-selected {
  border-color: hsl(var(--primary) / 0.22);
  background: hsl(var(--primary) / 0.07);
  color: hsl(var(--foreground));
}

.account-dropdown__trigger-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.account-dropdown__chevron {
  flex: 0 0 auto;
  width: 0.875rem;
  height: 0.875rem;
  color: hsl(var(--muted-foreground));
  transition: transform 0.16s ease;
}

.account-dropdown__menu {
  position: absolute;
  top: 100%;
  right: 0;
  left: 0;
  z-index: 50;
  margin-top: 0.25rem;
  padding: 0.25rem;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.5rem;
  background: hsl(var(--background));
}

.account-dropdown__list {
  max-height: 13.75rem;
  padding-right: 0.25rem;
  overflow-y: auto;
}

.account-dropdown__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  min-height: 2.25rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    border-color 0.16s ease;
}

.account-dropdown__item:hover {
  background: hsl(var(--accent) / 0.48);
  color: hsl(var(--foreground));
}

.account-dropdown__item.is-selected {
  border-color: hsl(var(--primary) / 0.18);
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--foreground));
  font-weight: 650;
}

.account-dropdown__item-text {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-dropdown__provider {
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.6875rem;
  font-weight: 500;
  line-height: 1.2;
}

.account-dropdown__actions {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  opacity: 0;
  transition: opacity 0.16s ease;
}

.account-dropdown__item:hover .account-dropdown__actions,
.account-dropdown__item:focus-within .account-dropdown__actions {
  opacity: 1;
}

.account-dropdown__icon-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.375rem;
  color: hsl(var(--muted-foreground));
  transition:
    color 0.16s ease,
    background-color 0.16s ease;
}

.account-dropdown__icon-button:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.account-dropdown__icon-button--danger:hover {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
}

.account-dropdown__empty {
  padding: 1rem 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  text-align: center;
}

.account-dropdown__separator {
  height: 1px;
  margin: 0.25rem 0;
  background: hsl(var(--border) / 0.45);
}

.account-dropdown__add {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  min-height: 2.25rem;
  padding: 0 0.75rem;
  border-radius: 0.5rem;
  color: hsl(var(--primary));
  font-size: 0.8125rem;
  font-weight: 650;
  transition: background-color 0.16s ease;
}

.account-dropdown__add:hover {
  background: hsl(var(--primary) / 0.07);
}

@media (prefers-reduced-motion: reduce) {
  .account-dropdown__trigger,
  .account-dropdown__chevron,
  .account-dropdown__item,
  .account-dropdown__actions,
  .account-dropdown__icon-button,
  .account-dropdown__add {
    transition: none;
  }
}
</style>
