<template>
  <Dialog :open="open">
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
          <label class="app-dialog-form-label">服务提供商</label>
          <div class="account-dialog__providers">
            <Button
              v-for="prov in providers"
              :key="prov.value"
              type="button"
              variant="ghost"
              size="sm"
              @click="form.provider = prov.value"
              class="account-dialog__provider"
              :class="{ 'is-selected': form.provider === prov.value }"
            >
              <AppIcon :name="prov.icon" class="h-3.5 w-3.5 shrink-0" />
              <span>{{ prov.name }}</span>
            </Button>
          </div>
        </div>

        <div class="app-dialog-form-field">
          <label class="app-dialog-form-label">账号名称</label>
          <div class="app-icon-field">
            <AppIcon name="pencil" class="app-icon-field__icon" />
            <Input
              v-model="form.name"
              class="app-form-input app-form-input--with-icon"
              placeholder="例如: 我的 Miniflux"
            />
          </div>
        </div>

        <div class="app-dialog-form-field">
          <label class="app-dialog-form-label">服务接口地址 (URL)</label>
          <div class="app-icon-field">
            <AppIcon name="link" class="app-icon-field__icon" />
            <Input
              v-model="form.base_url"
              class="app-form-input app-form-input--with-icon"
              :placeholder="baseUrlPlaceholder"
            />
          </div>
        </div>

        <div class="app-dialog-form-field">
          <div class="app-dialog-form-label-row">
            <label class="app-dialog-form-label">用户名</label>
            <span
              v-if="form.provider === 'greader' || form.provider === 'fever'"
              class="app-dialog-form-required"
            >
              * 必填
            </span>
          </div>
          <div class="app-icon-field">
            <AppIcon name="user" class="app-icon-field__icon" />
            <Input
              v-model="form.username"
              class="app-form-input app-form-input--with-icon"
              placeholder="用户名 (Google Reader 与 Fever 需要)"
            />
          </div>
        </div>

        <div class="app-dialog-form-field">
          <div class="app-dialog-form-label-row">
            <label class="app-dialog-form-label">{{ credentialPlaceholder }}</label>
            <span
              v-if="!form.id"
              class="app-dialog-form-required"
            >
              * 必填
            </span>
          </div>
          <div class="app-icon-field">
            <AppIcon name="security" class="app-icon-field__icon" />
            <Input
              v-model="form.credential"
              type="password"
              class="app-form-input app-form-input--with-icon"
              :placeholder="form.id ? '留空表示不修改密码或 Token' : '密码或 API Token'"
            />
          </div>
        </div>

        <div class="app-dialog-separator"></div>

        <div class="account-dialog__sync-row">
          <div class="account-dialog__sync-copy">
            <span class="account-dialog__sync-title">启用此账号同步</span>
            <span class="account-dialog__sync-description">开启后系统将自动定期在后台同步此账号的订阅内容</span>
          </div>
          <Switch v-model="form.enabled" />
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
          <AppIcon v-if="!testing" name="sync" class="h-3.5 w-3.5 mr-1.5 opacity-70" />
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
            size="sm"
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

type RssProvider = 'greader' | 'miniflux' | 'fever'

interface AccountForm {
  id: number | null
  // ponytail: widened to string to match the parent ref's inferred type (the
  // composable's ref({...}) widens the provider literal to string); the
  // template only reads/equalities it, never constructs a value.
  provider: string
  name: string
  base_url: string
  username: string
  credential: string
  enabled: boolean
}

interface Provider {
  value: RssProvider
  name: string
  desc: string
  icon: AppIconName
}

// ponytail: open + form are defineModel refs (not props), so mutating their
// fields (form.name = …, open = false) is lint-clean and Vue's reactivity
// propagates back to the parent composable state — no per-field emit wiring.
// Read-only computeds + the two handlers (save/test) come in as plain props.
const open = defineModel<boolean>('open', { required: true })
const form = defineModel<AccountForm>('form', { required: true })

interface Props {
  providers: Provider[]
  baseUrlPlaceholder: string
  credentialPlaceholder: string
  formMessage: string
  formError: boolean
  canSaveForm: boolean
  canTestForm: boolean
  saving: boolean
  testing: boolean
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
  border-radius: 0.5rem;
  background: hsl(var(--muted) / 0.26);
}

.account-dialog__provider {
  flex: 1 1 0;
  gap: 0.375rem;
  min-height: 2rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 650;
  user-select: none;
}

.account-dialog__provider:hover {
  color: hsl(var(--foreground));
}

.account-dialog__provider.is-selected {
  border-color: hsl(var(--border) / 0.68);
  background: hsl(var(--accent) / 0.72);
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
  font-size: 0.75rem;
  font-weight: 650;
}

.account-dialog__sync-description {
  color: hsl(var(--muted-foreground) / 0.74);
  font-size: 0.75rem;
  line-height: 1.45;
}

.account-dialog__button--test {
  flex: 0 0 auto;
}

@media (prefers-reduced-motion: reduce) {
  .account-dialog__provider {
    transition: none;
  }
}
</style>
