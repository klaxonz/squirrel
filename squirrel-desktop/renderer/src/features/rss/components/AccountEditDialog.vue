<template>
  <Dialog :open="open" @update:open="open = $event">
    <DialogContent class="account-dialog app-dialog-surface">
      <DialogHeader class="app-dialog-form-header">
        <DialogTitle class="app-dialog-form-title">
          {{ form.id ? '编辑 RSS 账号' : '添加 RSS 账号' }}
        </DialogTitle>
        <DialogDescription class="app-dialog-form-description">
          连接第三方 RSS 服务账号，支持 Google Reader API, Miniflux, Fever 等规范。
        </DialogDescription>
      </DialogHeader>

      <div class="app-dialog-form-body app-dialog-form-body--scroll custom-scrollbar">
        <div class="app-dialog-form-field">
          <label id="rss-account-provider-label" class="app-dialog-form-label">服务提供商</label>
          <div
            class="account-dialog__providers"
            role="group"
            aria-labelledby="rss-account-provider-label"
          >
            <Button
              v-for="prov in providers"
              :key="prov.value"
              type="button"
              variant="secondary"
              size="sm"
              @click="form.provider = prov.value"
              class="account-dialog__provider"
              :class="{ 'is-selected': form.provider === prov.value }"
              :aria-pressed="form.provider === prov.value"
            >
              <AppIcon :name="prov.icon" class="h-3.5 w-3.5 shrink-0" />
              <span>{{ prov.name }}</span>
            </Button>
          </div>
        </div>

        <div class="app-dialog-form-field">
          <label class="app-dialog-form-label" for="rss-account-name">账号名称</label>
          <div class="app-icon-field">
            <AppIcon name="pencil" class="app-icon-field__icon" />
            <Input fluid
              id="rss-account-name"
              v-model="form.name"
              class="app-form-input app-form-input--with-icon"
              placeholder="例如: 我的 Miniflux"
            />
          </div>
        </div>

        <div class="app-dialog-form-field">
          <label class="app-dialog-form-label" for="rss-account-base-url">
            服务接口地址 (URL)
            <span class="account-dialog__required-marker" aria-hidden="true">*</span>
          </label>
          <div class="app-icon-field">
            <AppIcon name="link" class="app-icon-field__icon" />
            <Input fluid
              id="rss-account-base-url"
              v-model="form.base_url"
              class="app-form-input app-form-input--with-icon"
              :placeholder="baseUrlPlaceholder"
              required
              aria-required="true"
            />
          </div>
        </div>

        <div class="app-dialog-form-field">
          <label class="app-dialog-form-label" for="rss-account-username">
            用户名
            <span
              v-if="requiresUsername"
              class="account-dialog__required-marker"
              aria-hidden="true"
            >
              *
            </span>
          </label>
          <div class="app-icon-field">
            <AppIcon name="user" class="app-icon-field__icon" />
            <Input fluid
              id="rss-account-username"
              v-model="form.username"
              class="app-form-input app-form-input--with-icon"
              placeholder="用户名"
              :required="requiresUsername"
              :aria-required="requiresUsername"
            />
          </div>
        </div>

        <div class="app-dialog-form-field">
          <label class="app-dialog-form-label" for="rss-account-credential">
            {{ credentialPlaceholder }}
            <span
              v-if="!form.id"
              class="account-dialog__required-marker"
              aria-hidden="true"
            >
              *
            </span>
          </label>
          <div class="app-icon-field">
            <AppIcon name="security" class="app-icon-field__icon" />
            <Input fluid
              id="rss-account-credential"
              v-model="form.credential"
              type="password"
              class="app-form-input app-form-input--with-icon"
              :placeholder="form.id ? '留空表示不修改密码或 Token' : '密码或 API Token'"
              :required="!form.id"
              :aria-required="!form.id"
            />
          </div>
        </div>

        <div v-if="form.provider !== 'greader'" class="app-dialog-form-field">
          <label class="app-dialog-form-label" for="rss-account-sync-limit">
            每个订阅源同步文章数
            <span class="account-dialog__required-marker" aria-hidden="true">*</span>
          </label>
          <div class="app-icon-field">
            <AppIcon name="list" class="app-icon-field__icon" />
            <Input fluid
              id="rss-account-sync-limit"
              v-model.number="form.sync_entry_limit"
              type="number"
              min="1"
              :max="maxSyncEntryLimit"
              step="1"
              class="app-form-input app-form-input--with-icon tabular-nums"
              required
              aria-required="true"
            />
          </div>
        </div>

        <div class="app-dialog-separator"></div>

        <div class="account-dialog__sync-row">
          <div class="account-dialog__sync-copy">
            <span id="rss-account-enabled-label" class="account-dialog__sync-title">启用此账号同步</span>
            <span id="rss-account-enabled-description" class="account-dialog__sync-description">开启后系统将自动定期在后台同步此账号的订阅内容</span>
          </div>
          <Switch
            v-model="form.enabled"
            aria-labelledby="rss-account-enabled-label"
            aria-describedby="rss-account-enabled-description"
          />
        </div>

        <Transition name="fade">
          <div
            v-if="formMessage"
            class="app-dialog-message"
            :class="formError ? 'is-error' : 'is-success'"
          >
            <AppIcon
              :name="formError ? 'error' : 'check'"
              class="app-dialog-message__icon"
            />
            <span>{{ formMessage }}</span>
          </div>
        </Transition>
      </div>

      <DialogFooter class="app-dialog-form-footer app-dialog-form-footer--between">
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="!canTestForm"
          :loading="testing"
          @click="$emit('test')"
        >
          <AppIcon v-if="!testing" name="diagnostics" class="h-3.5 w-3.5 mr-1.5 opacity-70" />
          测试连接
        </Button>
        <div class="app-dialog-actions">
          <Button
            type="button"
            variant="outline"
            size="sm"
            @click="open = false"
          >
            取消
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            class="account-dialog__confirm"
            :disabled="!canSaveForm"
            :loading="saving"
            @click="$emit('save')"
          >
            {{ form.id ? '保存修改' : '确认添加' }}
          </Button>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Switch } from '@/shared/ui/switch'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/dialog'
import type { AppIconName } from '@/shared/icons/app-icons'
import type { RssAccountForm, RssProvider } from '@/features/rss/types/rss'

interface Provider {
  value: RssProvider
  name: string
  desc: string
  icon: AppIconName
}

// These models intentionally share the parent's form object so field edits and
// dialog dismissal do not need duplicated per-field events.
const open = defineModel<boolean>('open', { required: true })
const form = defineModel<RssAccountForm>('form', { required: true })

interface Props {
  providers: Provider[]
  baseUrlPlaceholder: string
  credentialPlaceholder: string
  formMessage: string
  formError: boolean
  requiresUsername: boolean
  canSaveForm: boolean
  canTestForm: boolean
  saving: boolean
  testing: boolean
  maxSyncEntryLimit: number
}

defineProps<Props>()
defineEmits<{
  save: []
  test: []
}>()
</script>

<style scoped>
.account-dialog {
  max-width: 28rem;
}

.account-dialog__providers {
  display: flex;
  gap: 0.25rem;
  padding: 0.25rem;
  border: 1px solid hsl(var(--border) / 0.16);
  border-radius: var(--radius-md);
  background: var(--app-filter-track-bg);
}

.account-dialog__provider {
  flex: 1 1 0;
  gap: 0.375rem;
  min-height: 2rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  font-weight: 650;
  user-select: none;
}

.account-dialog__provider:hover {
  color: hsl(var(--foreground));
}

.account-dialog__provider.is-selected {
  border-color: var(--app-selection-border);
  background: var(--app-selection-bg);
  color: hsl(var(--foreground));
}

.account-dialog__sync-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  user-select: none;
}

.account-dialog__sync-copy {
  display: flex;
  flex-direction: column;
  gap: 0.1875rem;
  min-width: 0;
  text-align: left;
}

.account-dialog__sync-title {
  color: hsl(var(--foreground) / 0.86);
  font-size: var(--app-text-sm);
  font-weight: 650;
}

.account-dialog__sync-description {
  color: hsl(var(--muted-foreground) / 0.74);
  font-size: var(--app-text-sm);
  line-height: 1.45;
}

.account-dialog__required-marker {
  margin-left: 0.1875rem;
  color: hsl(var(--destructive) / 0.78);
  font-weight: 500;
}

.account-dialog__button--test {
  flex: 0 0 auto;
}

.account-dialog__confirm {
  border-color: var(--app-selection-border);
  background: var(--app-selection-bg);
  color: hsl(var(--foreground) / 0.82);
}

.account-dialog__confirm:hover {
  border-color: var(--app-selection-border-hover);
  background: var(--app-selection-bg-hover);
  color: hsl(var(--foreground));
}

@media (prefers-reduced-motion: reduce) {
  .account-dialog__provider {
    transition: none;
  }
}
</style>
