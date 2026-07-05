<template>
  <Dialog :open="open">
    <DialogContent class="account-dialog">
      <DialogHeader class="account-dialog__header">
        <DialogTitle class="account-dialog__title">
          {{ form.id ? '编辑 RSS 账号' : '添加 RSS 账号' }}
        </DialogTitle>
        <DialogDescription class="account-dialog__description">
          连接第三方 RSS 服务账号，支持 Google Reader API, Miniflux, Fever 等规范。
        </DialogDescription>
      </DialogHeader>

      <div class="account-dialog__body custom-scrollbar">
        <div class="account-dialog__field">
          <label class="account-dialog__label">服务提供商</label>
          <div class="account-dialog__providers">
            <button
              v-for="prov in providers"
              :key="prov.value"
              type="button"
              @click="form.provider = prov.value"
              class="account-dialog__provider"
              :class="{ 'is-selected': form.provider === prov.value }"
            >
              <AppIcon :name="prov.icon" class="h-3.5 w-3.5 shrink-0" />
              <span>{{ prov.name }}</span>
            </button>
          </div>
        </div>

        <div class="account-dialog__field">
          <label class="account-dialog__label">账号名称</label>
          <div class="account-dialog__input-wrap">
            <AppIcon name="pencil" class="account-dialog__input-icon" />
            <Input
              v-model="form.name"
              class="account-dialog__input"
              placeholder="例如: 我的 Miniflux"
            />
          </div>
        </div>

        <div class="account-dialog__field">
          <label class="account-dialog__label">服务接口地址 (URL)</label>
          <div class="account-dialog__input-wrap">
            <AppIcon name="link" class="account-dialog__input-icon" />
            <Input
              v-model="form.base_url"
              class="account-dialog__input"
              :placeholder="baseUrlPlaceholder"
            />
          </div>
        </div>

        <div class="account-dialog__field">
          <div class="account-dialog__label-row">
            <label class="account-dialog__label">用户名</label>
            <span
              v-if="form.provider === 'greader' || form.provider === 'fever'"
              class="account-dialog__required"
            >
              * 必填
            </span>
          </div>
          <div class="account-dialog__input-wrap">
            <AppIcon name="user" class="account-dialog__input-icon" />
            <Input
              v-model="form.username"
              class="account-dialog__input"
              placeholder="用户名 (Google Reader 与 Fever 需要)"
            />
          </div>
        </div>

        <div class="account-dialog__field">
          <div class="account-dialog__label-row">
            <label class="account-dialog__label">{{ credentialPlaceholder }}</label>
            <span
              v-if="!form.id"
              class="account-dialog__required"
            >
              * 必填
            </span>
          </div>
          <div class="account-dialog__input-wrap">
            <AppIcon name="security" class="account-dialog__input-icon" />
            <Input
              v-model="form.credential"
              type="password"
              class="account-dialog__input"
              :placeholder="form.id ? '留空表示不修改密码或 Token' : '密码或 API Token'"
            />
          </div>
        </div>

        <div class="account-dialog__separator"></div>

        <div class="account-dialog__sync-row">
          <div class="account-dialog__sync-copy">
            <span class="account-dialog__sync-title">启用此账号同步</span>
            <span class="account-dialog__sync-description">开启后系统将自动定期在后台同步此账号的订阅内容</span>
          </div>
          <button
            type="button"
            @click="form.enabled = !form.enabled"
            class="account-dialog__switch"
            :class="{ 'is-enabled': form.enabled }"
          >
            <span
              class="account-dialog__switch-knob"
              :class="{ 'is-enabled': form.enabled }"
            />
          </button>
        </div>

        <Transition name="fade">
          <div
            v-if="formMessage"
            class="account-dialog__message"
            :class="formError ? 'is-error' : 'is-success'"
          >
            <AppIcon
              :name="formError ? 'error' : 'check'"
              class="account-dialog__message-icon"
            />
            <span>{{ formMessage }}</span>
          </div>
        </Transition>
      </div>

      <DialogFooter class="account-dialog__footer">
        <Button
          type="button"
          variant="outline"
          class="account-dialog__button account-dialog__button--test"
          :disabled="!canTestForm"
          :loading="testing"
          @click="$emit('test')"
        >
          <AppIcon v-if="!testing" name="sync" class="h-3.5 w-3.5 mr-1.5 opacity-70" />
          测试连接
        </Button>
        <div class="account-dialog__actions">
          <Button
            type="button"
            variant="outline"
            class="account-dialog__button"
            @click="open = false"
          >
            取消
          </Button>
          <Button
            type="button"
            class="account-dialog__button account-dialog__button--primary"
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
  overflow: hidden;
  padding: 0;
  border: 1px solid hsl(var(--border) / 0.36);
  border-radius: 0.625rem;
  background: hsl(var(--background));
  box-shadow: none;
}

.account-dialog__header {
  padding: 1.25rem;
  border-bottom: 1px solid hsl(var(--border) / 0.14);
  text-align: left;
}

.account-dialog__title {
  color: hsl(var(--foreground));
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.3;
}

.account-dialog__description {
  margin-top: 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.5;
}

.account-dialog__body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-height: 60vh;
  overflow-y: auto;
  padding: 1.25rem;
}

.account-dialog__field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.account-dialog__label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.account-dialog__label,
.account-dialog__sync-title {
  color: hsl(var(--foreground) / 0.86);
  font-size: 0.75rem;
  font-weight: 650;
}

.account-dialog__required {
  color: hsl(var(--destructive));
  font-size: 0.6875rem;
  font-weight: 650;
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
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1 1 0;
  gap: 0.375rem;
  min-height: 2rem;
  border: 1px solid transparent;
  border-radius: 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 650;
  cursor: pointer;
  user-select: none;
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    border-color 0.16s ease;
}

.account-dialog__provider:hover {
  color: hsl(var(--foreground));
}

.account-dialog__provider.is-selected {
  border-color: hsl(var(--primary) / 0.24);
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--foreground));
}

.account-dialog__input-wrap {
  position: relative;
}

.account-dialog__input-icon {
  position: absolute;
  top: 50%;
  left: 0.75rem;
  width: 0.875rem;
  height: 0.875rem;
  color: hsl(var(--muted-foreground) / 0.58);
  transform: translateY(-50%);
  transition: color 0.16s ease;
  pointer-events: none;
}

.account-dialog__input-wrap:focus-within .account-dialog__input-icon {
  color: hsl(var(--foreground));
}

.account-dialog__input {
  height: 2.25rem;
  padding-right: 0.875rem;
  padding-left: 2.25rem;
  border: 1px solid hsl(var(--border) / 0.42);
  border-radius: 0.5rem;
  background: hsl(var(--accent) / 0.1);
  color: hsl(var(--foreground));
  font-size: 0.75rem;
  font-weight: 500;
  box-shadow: none;
  transition:
    background-color 0.16s ease,
    border-color 0.16s ease,
    color 0.16s ease;
}

.account-dialog__input:hover {
  background: hsl(var(--accent) / 0.15);
}

.account-dialog__input:focus-visible {
  border-color: hsl(var(--primary) / 0.42);
  background: hsl(var(--background));
  outline: 1px solid hsl(var(--primary) / 0.2);
}

.account-dialog__separator {
  height: 1px;
  background: hsl(var(--border) / 0.14);
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

.account-dialog__sync-description {
  color: hsl(var(--muted-foreground) / 0.74);
  font-size: 0.75rem;
  line-height: 1.45;
}

.account-dialog__switch {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
  width: 2.25rem;
  height: 1.25rem;
  padding: 0.125rem;
  border: 1px solid hsl(var(--border) / 0.38);
  border-radius: 999px;
  background: hsl(var(--muted) / 0.82);
  cursor: pointer;
  transition:
    background-color 0.16s ease,
    border-color 0.16s ease;
}

.account-dialog__switch.is-enabled {
  border-color: hsl(var(--foreground) / 0.18);
  background: hsl(var(--foreground));
}

.account-dialog__switch-knob {
  width: 0.875rem;
  height: 0.875rem;
  border-radius: 999px;
  background: hsl(var(--background));
  transform: translateX(0);
  transition: transform 0.16s ease;
}

.account-dialog__switch-knob.is-enabled {
  transform: translateX(1rem);
}

.account-dialog__message {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  border: 1px solid;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1.5;
}

.account-dialog__message.is-error {
  border-color: hsl(var(--destructive) / 0.24);
  background: hsl(var(--destructive) / 0.06);
  color: hsl(var(--destructive));
}

.account-dialog__message.is-success {
  border-color: hsl(var(--success) / 0.24);
  background: hsl(var(--success) / 0.06);
  color: hsl(var(--success));
}

.account-dialog__message-icon {
  flex: 0 0 auto;
  width: 0.875rem;
  height: 0.875rem;
  margin-top: 0.125rem;
}

.account-dialog__footer {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1rem;
  border-top: 1px solid hsl(var(--border) / 0.14);
  background: hsl(var(--muted) / 0.18);
}

.account-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.account-dialog__button {
  height: 2.25rem;
  padding: 0 0.75rem;
  border: 1px solid hsl(var(--border) / 0.42);
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 650;
  cursor: pointer;
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    border-color 0.16s ease,
    opacity 0.16s ease;
}

.account-dialog__button:hover {
  background: hsl(var(--accent) / 0.4);
}

.account-dialog__button--test {
  flex: 0 0 auto;
}

.account-dialog__button--primary {
  padding-right: 1rem;
  padding-left: 1rem;
  border-color: hsl(var(--primary) / 0.42);
}

@media (prefers-reduced-motion: reduce) {
  .account-dialog__provider,
  .account-dialog__input,
  .account-dialog__input-icon,
  .account-dialog__switch,
  .account-dialog__switch-knob,
  .account-dialog__button {
    transition: none;
  }
}
</style>
