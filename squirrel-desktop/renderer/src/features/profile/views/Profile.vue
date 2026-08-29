<template>
  <AppPageShell variant="default" surface="operate" width="form" scrollable>
    <div class="app-page-content profile-page">
      <header class="profile-header">
        <button
          type="button"
          class="profile-avatar-control"
          :aria-label="form.nickname ? `编辑 ${form.nickname} 的头像` : '编辑头像'"
          @click="focusAvatarInput"
        >
          <img
            v-if="form.avatar && !avatarError"
            :src="form.avatar"
            :alt="form.nickname ? `${form.nickname}的头像` : '用户头像'"
            class="profile-avatar-image"
          />
          <div v-else class="profile-avatar-fallback">
            <template v-if="userInitial">{{ userInitial }}</template>
            <AppIcon v-else name="user" class="h-6 w-6 text-primary/75" />
          </div>
          <span class="profile-avatar-mask" aria-hidden="true">
            <AppIcon name="camera" class="h-3.5 w-3.5 app-media-on-image" />
          </span>
        </button>

        <div class="profile-identity">
          <h1 class="app-h2">
            {{ userStore.currentUser?.nickname || '未设置昵称' }}
          </h1>
          <div v-if="createdAt" class="profile-created-at">
            <AppIcon name="time" class="h-3 w-3" />
            <span>注册于 {{ createdAt }}</span>
          </div>
        </div>
      </header>

      <div class="app-settings-stack">
        <section class="app-settings-section">
          <div class="app-settings-section-title">
            <h3>基本资料</h3>
            <p>更新昵称与头像，保存后同步到所有设备。</p>
          </div>

          <div class="app-settings-panel profile-form-panel">
            <AppFormField id="profile-nickname" class="profile-field profile-field--counted">
              <template #label>
                <span>昵称</span>
                <span class="profile-field__counter">{{ form.nickname.length }}/50</span>
              </template>
              <template #default="{ control }">
                <div class="app-icon-field">
                  <AppIcon name="user" class="app-icon-field__icon" />
                  <Input
                    v-bind="control"
                    fluid
                    v-model="form.nickname"
                    placeholder="请输入昵称"
                    class="app-form-input app-form-input--with-icon"
                    maxlength="50"
                  />
                </div>
              </template>
            </AppFormField>

            <AppFormField
              id="profile-avatar"
              label="头像图片链接"
              :class="['profile-field', { 'profile-field--with-preview': form.avatar }]"
            >
              <template #default="{ control }">
                <div class="app-icon-field">
                  <AppIcon name="link" class="app-icon-field__icon" />
                  <Input
                    v-bind="control"
                    fluid
                    v-model="form.avatar"
                    type="url"
                    autocomplete="url"
                    placeholder="输入图片链接 (HTTPS)"
                    class="app-form-input app-form-input--with-icon"
                  />
                </div>
              </template>

              <template v-if="form.avatar" #description>
                <span class="profile-avatar-preview-image">
                  <img
                    :src="form.avatar"
                    :alt="form.nickname ? `${form.nickname}的头像` : '用户头像'"
                    class="h-full w-full object-cover"
                    @error="avatarError = true"
                    @load="avatarError = false"
                  />
                </span>
                <span class="profile-avatar-preview-copy">
                  <span class="profile-avatar-preview-title">头像实时预览</span>
                  <span
                    v-if="avatarError"
                    class="profile-status profile-status--error"
                  >
                    <AppIcon name="warning" class="h-2.5 w-2.5" />
                    图片加载失败，请检查链接
                  </span>
                  <span
                    v-else
                    class="profile-status profile-status--success"
                  >
                    <AppIcon name="check" class="h-2.5 w-2.5" />
                    图片加载成功
                  </span>
                </span>
              </template>
            </AppFormField>

            <div v-if="saveError" class="app-dialog-message is-error">
              <AppIcon name="warning" class="app-dialog-message__icon" />
              <span>{{ saveError }}</span>
            </div>

            <div class="profile-actions">
              <Button
                :loading="saving"
                :disabled="!hasChanges"
                @click="handleSave"
              >
                保存修改
              </Button>

              <span v-if="saved" class="profile-saved">
                <AppIcon name="check" class="h-3.5 w-3.5" />
                所有更改已保存
              </span>
            </div>
          </div>
        </section>

        <section class="app-settings-section">
          <div class="app-settings-section-title">
            <h3>会话管理</h3>
            <p>退出后需要重新登录才能访问媒体库。</p>
          </div>

          <div class="app-settings-panel">
            <div class="app-settings-row">
              <div class="min-w-0">
                <div class="app-settings-row__title">退出当前账号</div>
                <div class="app-settings-row__desc">清除本机会话并返回登录页。</div>
              </div>
              <Button variant="outline" class="profile-logout-button" @click="handleLogout">
                <AppIcon name="logout" class="h-3.5 w-3.5" />
                退出登录
              </Button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Logger } from '@/shared/lib/logger'
import AppFormField from '@/shared/components/layout/AppFormField.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { useUserStore } from '@/shared/stores/user'
import { useProfileEditForm } from '@/features/profile/composables/useProfileEditForm'

const router = useRouter()
const userStore = useUserStore()

// ponytail: profile-edit form (save state machine + diff-only payload + the
// 3s "saved" banner auto-dismiss) lives in useProfileEditForm.
const { form, saving, saved, saveError, hasChanges, hydrate, handleSave } = useProfileEditForm({ userStore })

const avatarError = ref(false)

const userInitial = computed(() => {
  const name = userStore.currentUser?.nickname || ''
  return name ? name.slice(0, 1).toUpperCase() : ''
})

const createdAt = computed(() => {
  const raw = userStore.currentUser?.created_at
  if (!raw) return ''
  try {
    return new Date(raw).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch (err) {
    Logger.warn('[Profile] Failed to format created_at', err)
    return ''
  }
})

onMounted(() => {
  hydrate()
})

const focusAvatarInput = () => {
  document.getElementById('profile-avatar')?.focus()
}

const handleLogout = async () => {
  await userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.profile-page {
  --app-page-max-width: var(--app-content-form-max);
  max-width: var(--app-content-feed-max);
  margin-inline: auto;
  padding-top: var(--space-5);
  padding-bottom: var(--space-8);
}

.profile-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  padding: var(--space-4);
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  background: hsl(var(--card));
}

.profile-avatar-control {
  position: relative;
  width: 4rem;
  height: 4rem;
  flex: 0 0 auto;
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  border-radius: 999px;
  background: hsl(var(--muted));
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.profile-avatar-control:hover,
.profile-avatar-control:focus-visible {
  border-color: var(--app-selection-border-hover);
  background: var(--app-selection-bg-hover);
}

.profile-avatar-image,
.profile-avatar-fallback {
  width: 100%;
  height: 100%;
}

.profile-avatar-image {
  object-fit: cover;
}

.profile-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--primary));
  font-size: var(--app-text-2xl);
  font-weight: 700;
}

.profile-avatar-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--app-media-scrim-mid);
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-default);
}

.profile-avatar-control:hover .profile-avatar-mask,
.profile-avatar-control:focus-visible .profile-avatar-mask {
  opacity: 1;
}

.profile-identity {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
}

.profile-created-at {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
}

.profile-form-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  background: hsl(var(--card));
}

.profile-field :deep(.app-form-field__label) {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  font-weight: 500;
}

.profile-field--counted :deep(.app-form-field__label) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.profile-field__counter {
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: var(--app-text-xs);
  font-variant-numeric: tabular-nums;
}

.profile-field--with-preview :deep(.app-form-field__description) {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.12);
}

.profile-avatar-preview-image {
  width: 3rem;
  height: 3rem;
  flex: 0 0 auto;
  overflow: hidden;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-md);
  background: hsl(var(--muted));
}

.profile-avatar-preview-copy {
  min-width: 0;
}

.profile-avatar-preview-title {
  display: block;
  margin-bottom: 0.25rem;
  color: hsl(var(--foreground));
  font-size: var(--app-text-sm);
  font-weight: 650;
}

.profile-status {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.375rem;
  border: 1px solid;
  border-radius: var(--radius-sm);
  font-size: var(--app-text-xs);
  font-weight: 500;
}

.profile-status--error {
  border-color: hsl(var(--destructive) / 0.16);
  background: hsl(var(--destructive) / 0.05);
  color: hsl(var(--destructive));
}

.profile-status--success {
  border-color: hsl(var(--success) / 0.16);
  background: hsl(var(--success) / 0.05);
  color: hsl(var(--success));
}

.profile-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-top: 0.25rem;
}

.profile-saved {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: hsl(var(--success));
  font-size: var(--app-text-sm);
  font-weight: 500;
}

.profile-logout-button {
  flex-shrink: 0;
}

.profile-logout-button:hover {
  border-color: hsl(var(--destructive) / 0.4);
  background: hsl(var(--destructive) / 0.08);
  color: hsl(var(--destructive));
}

@media (hover: none), (prefers-reduced-motion: reduce) {
  .profile-avatar-mask {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .profile-avatar-control,
  .profile-avatar-mask {
    transition: none;
  }
}
</style>
