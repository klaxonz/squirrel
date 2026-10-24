<template>
  <div ref="dropdownRef" class="account-dropdown">
    <Button
      variant="secondary"
      size="sm"
      @click="$emit('toggle')"
      class="account-dropdown__trigger"
      :class="{ 'is-selected': selectedId }"
    >
      <div class="account-dropdown__identity">
        <span class="account-dropdown__mark">
          <AppIcon name="rss" class="h-3.5 w-3.5" />
        </span>
        <span class="account-dropdown__copy">
          <span class="account-dropdown__name">{{ selectedName || '选择服务账号' }}</span>
          <span class="account-dropdown__provider">
            {{ selectedProvider || '连接 RSS 服务' }}
          </span>
        </span>
      </div>
      <AppIcon
        name="chevronDown"
        class="account-dropdown__chevron"
        :class="{ 'rotate-180': open }"
      />
    </Button>

    <AppFloatingList
      v-if="open"
      max-height="13.75rem"
    >
        <AppSelectableListItem
          v-for="acc in accounts"
          :key="acc.id"
          :selected="selectedId === acc.id"
          @click="$emit('select', acc.id)"
          @keydown.enter.self.prevent="$emit('select', acc.id)"
          @keydown.space.self.prevent="$emit('select', acc.id)"
        >
          <AppIcon name="rss" class="h-3.5 w-3.5 shrink-0 opacity-70" />
          <span class="account-dropdown__item-text">
            {{ acc.name }}
            <span class="account-dropdown__provider">({{ acc.provider }})</span>
          </span>
          <div class="app-selectable-list-item__actions account-dropdown__actions">
            <Button
              variant="secondary"
              size="sm" icon-only
              @click.stop="$emit('edit', acc)"
              class="account-dropdown__icon-button"
              title="编辑账号"
            >
              <AppIcon name="pencil" class="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="secondary"
              size="sm" icon-only
              @click.stop="$emit('delete', acc)"
              class="account-dropdown__icon-button account-dropdown__icon-button--danger"
              title="删除账号"
            >
              <AppIcon name="trash" class="h-3.5 w-3.5" />
            </Button>
          </div>
        </AppSelectableListItem>
        <AppListEmpty v-if="!accounts.length">暂无账号</AppListEmpty>
    </AppFloatingList>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppFloatingList from '@/shared/components/layout/AppFloatingList.vue'
import AppListEmpty from '@/shared/components/layout/AppListEmpty.vue'
import AppSelectableListItem from '@/shared/components/layout/AppSelectableListItem.vue'
import { Button } from '@/shared/ui/button'
import type { RssAccount } from '@/features/rss/types/rss'

defineProps<{
  accounts: RssAccount[]
  selectedId: number | null
  selectedName: string
  selectedProvider: string
  open: boolean
}>()

defineEmits<{
  toggle: []
  select: [id: number]
  edit: [acc: RssAccount]
  delete: [acc: RssAccount]
}>()
</script>

<style scoped>
.account-dropdown {
  position: relative;
  width: 100%;
}

.account-dropdown__trigger {
  justify-content: space-between;
  width: 100%;
  height: auto;
  min-height: 3rem;
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--app-field-border);
  background: var(--app-field-bg);
  text-align: left;
}

.account-dropdown__trigger:hover {
  border-color: var(--app-field-border-hover);
  background: var(--app-selection-bg-hover);
  color: hsl(var(--foreground));
}

.account-dropdown__trigger.is-selected {
  border-color: var(--app-selection-border);
  background: var(--app-selection-bg);
  color: hsl(var(--foreground));
}

.account-dropdown__identity {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.account-dropdown__mark {
  display: inline-flex;
  width: 1.75rem;
  height: 1.75rem;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--app-muted-surface);
  color: hsl(var(--foreground) / 0.72);
}

.account-dropdown__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  line-height: 1.2;
}

.account-dropdown__name {
  overflow: hidden;
  color: hsl(var(--foreground) / 0.82);
  font-size: var(--app-text-sm);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-dropdown__chevron {
  flex: 0 0 auto;
  width: 0.875rem;
  height: 0.875rem;
  color: hsl(var(--muted-foreground));
  transition: transform 0.16s ease;
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
  overflow: hidden;
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: var(--app-text-badge-size);
  font-weight: 500;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-dropdown__icon-button {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: var(--radius-sm);
}

.account-dropdown__icon-button:hover {
  background: var(--app-selection-bg-hover);
  color: hsl(var(--foreground));
}

.account-dropdown__icon-button--danger:hover {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
}

.account-dropdown :deep(.app-selectable-list-item.is-selected) {
  border-color: var(--app-selection-border);
  background: var(--app-selection-bg);
  color: hsl(var(--foreground));
}

@media (prefers-reduced-motion: reduce) {
  .account-dropdown__chevron {
    transition: none;
  }
}
</style>
