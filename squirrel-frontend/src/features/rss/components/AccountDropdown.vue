<template>
  <div ref="dropdownRef" class="account-dropdown">
    <Button
      variant="ghost"
      size="sm"
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
          @keydown.enter.prevent="$emit('select', acc.id)"
          @keydown.space.prevent="$emit('select', acc.id)"
        >
          <AppIcon name="rss" class="h-3.5 w-3.5 shrink-0 opacity-70" />
          <span class="account-dropdown__item-text">
            {{ acc.name }}
            <span class="account-dropdown__provider">({{ acc.provider }})</span>
          </span>
          <div class="app-selectable-list-item__actions account-dropdown__actions">
            <Button
              variant="ghost"
              size="mini-icon"
              @click.stop="$emit('edit', acc)"
              class="account-dropdown__icon-button"
              title="编辑账号"
            >
              <AppIcon name="pencil" class="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="mini-icon"
              @click.stop="$emit('delete', acc)"
              class="account-dropdown__icon-button account-dropdown__icon-button--danger"
              title="删除账号"
            >
              <AppIcon name="trash" class="h-3.5 w-3.5" />
            </Button>
          </div>
        </AppSelectableListItem>
        <AppListEmpty v-if="!accounts.length">暂无账号</AppListEmpty>
        <AppListSeparator />
        <Button
          variant="ghost"
          size="sm"
          @click="$emit('add')"
          class="account-dropdown__add"
        >
          <AppIcon name="plus" class="h-4 w-4" />
          添加服务账号
        </Button>
    </AppFloatingList>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppFloatingList from '@/shared/components/layout/AppFloatingList.vue'
import AppListEmpty from '@/shared/components/layout/AppListEmpty.vue'
import AppSelectableListItem from '@/shared/components/layout/AppSelectableListItem.vue'
import AppListSeparator from '@/shared/components/layout/AppListSeparator.vue'
import { Button } from '@/shared/ui/button'
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
  justify-content: space-between;
  width: 100%;
  min-height: 2rem;
  padding: 0 0.625rem;
  background: hsl(var(--accent) / 0.4);
  font-size: 0.75rem;
  font-weight: 650;
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

.account-dropdown__icon-button {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.375rem;
}

.account-dropdown__icon-button:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.account-dropdown__icon-button--danger:hover {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
}

.account-dropdown__add {
  gap: 0.5rem;
  width: 100%;
  min-height: 2.25rem;
  padding: 0 0.75rem;
  color: hsl(var(--primary));
  font-size: 0.8125rem;
  font-weight: 650;
}

.account-dropdown__add:hover {
  background: hsl(var(--primary) / 0.07);
}

@media (prefers-reduced-motion: reduce) {
  .account-dropdown__chevron {
    transition: none;
  }
}
</style>
