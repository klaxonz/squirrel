<template>
  <AppPageShell variant="default" scrollable>
    <div class="profile-page">
      <div class="profile-header">
        <div 
          class="profile-avatar-control"
          @click="focusAvatarInput"
        >
          <img
            v-if="form.avatar && !avatarError"
            :src="form.avatar"
            :alt="form.nickname ? `${form.nickname}的头像` : '用户头像'"
            class="profile-avatar-image"
          />
          <div 
            v-else 
            class="profile-avatar-fallback"
          >
            <template v-if="userInitial">{{ userInitial }}</template>
            <AppIcon v-else name="user" class="h-6 w-6 text-primary/75" />
          </div>
          <div class="profile-avatar-mask">
            <AppIcon name="camera" class="h-3.5 w-3.5 text-white" />
          </div>
        </div>

        <div class="profile-identity">
          <h2 class="app-h2">
            {{ userStore.currentUser?.nickname || '未设置昵称' }}
          </h2>
          <div v-if="createdAt" class="profile-created-at">
            <AppIcon name="time" class="h-3 w-3" />
            <span>注册于 {{ createdAt }}</span>
          </div>
        </div>
      </div>

      <div class="profile-sections">
        <div class="profile-section">
          <div class="profile-section-title">
            <h3>基本资料</h3>
          </div>
          
          <div class="profile-section-body">
            <div class="profile-form-grid">
              <div class="profile-field">
                <div class="profile-label-row">
                  <label>昵称</label>
                  <span>{{ form.nickname.length }}/50</span>
                </div>
                <div class="profile-input-wrap">
                  <AppIcon name="user" class="profile-input-icon" />
                  <Input
                    v-model="form.nickname"
                    placeholder="请输入昵称"
                    class="profile-input"
                    maxlength="50"
                  />
                </div>
              </div>
            </div>

            <div class="profile-field">
              <label>头像图片链接 (URL)</label>
              <div class="profile-input-wrap">
                <AppIcon name="link" class="profile-input-icon" />
                <Input
                  ref="avatarInput"
                  v-model="form.avatar"
                  placeholder="输入图片链接 (HTTPS)"
                  class="profile-input"
                />
              </div>
            </div>

            <div v-if="form.avatar" class="profile-avatar-preview">
              <div class="profile-avatar-preview-image">
                  <img
                    :src="form.avatar"
                    :alt="form.nickname ? `${form.nickname}的头像` : '用户头像'"
                    class="h-full w-full object-cover"
                    @error="avatarError = true"
                    @load="avatarError = false"
                  />
              </div>
              <div class="profile-avatar-preview-copy">
                  <p>头像实时预览</p>
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
              </div>
            </div>

            <div v-if="saveError" class="profile-error">
              <AppIcon name="warning" class="h-3.5 w-3.5 shrink-0" />
              <span>{{ saveError }}</span>
            </div>

            <div class="profile-actions">
              <Button
                class="profile-save-button"
                :class="{ 'is-disabled': !hasChanges }"
                :loading="saving"
                :disabled="!hasChanges"
                @click="handleSave"
              >
                保存修改
              </Button>
              
              <span 
                v-if="saved" 
                class="profile-saved"
              >
                <AppIcon name="check" class="h-3.5 w-3.5" />
                所有更改已保存
              </span>
            </div>

          </div>
        </div>

        <div class="profile-section">
          <div class="profile-section-title">
            <h3>会话管理</h3>
          </div>
          
          <div class="profile-section-body">
            <Button
              variant="outline"
              class="profile-logout-button"
              @click="handleLogout"
            >
              <AppIcon name="logout" class="h-3.5 w-3.5" />
              退出当前账号
            </Button>
          </div>
        </div>

      </div>

    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Logger } from '@/shared/lib/logger'
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
// ponytail: shadcn Input wrapper exposes its inner <input> via $el.querySelector;
// minimal structural type avoids importing the generated ui component type.
const avatarInput = ref<{ $el?: HTMLElement } | null>(null)

const userInitial = computed(() => {
  const name = userStore.currentUser?.nickname || ''
  return name ? name.charAt(0).toUpperCase() : ''
})

const createdAt = computed(() => {
  const date = userStore.currentUser?.created_at
  if (!date) return ''
  try {
    return new Date(date).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch (err) {
    Logger.warn('[Profile] Failed to format date', err)
    return String(date).slice(0, 10)
  }
})

onMounted(() => {
  hydrate()
})

const focusAvatarInput = () => {
  if (avatarInput.value) {
    const inputEl = (avatarInput.value.$el?.querySelector?.('input') as HTMLElement | null) ?? avatarInput.value.$el;
    inputEl?.focus?.();
  }
}

const handleLogout = async () => {
  await userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.profile-page {
  width: 100%;
  max-width: 45rem;
  margin: 0 auto;
  padding: 2rem 0;
  color: hsl(var(--foreground));
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid hsl(var(--border) / 0.4);
}

.profile-avatar-control {
  position: relative;
  width: 4rem;
  height: 4rem;
  flex: 0 0 auto;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.75rem;
  background: hsl(var(--muted));
  cursor: pointer;
  transition:
    border-color 0.16s ease,
    background-color 0.16s ease;
}

.profile-avatar-control:hover {
  border-color: hsl(var(--primary) / 0.28);
  background: hsl(var(--primary) / 0.06);
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
  font-size: 1.25rem;
  font-weight: 700;
}

.profile-avatar-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(0 0% 0% / 0.44);
  opacity: 0;
  transition: opacity 0.16s ease;
}

.profile-avatar-control:hover .profile-avatar-mask {
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
  color: hsl(var(--muted-foreground) / 0.68);
  font-size: 0.75rem;
}

.profile-sections {
  display: flex;
  flex-direction: column;
}

.profile-section {
  display: grid;
  grid-template-columns: minmax(0, 9rem) minmax(0, 1fr);
  gap: 1.5rem;
  padding: 1.5rem 0;
  border-bottom: 1px solid hsl(var(--border) / 0.4);
}

.profile-section:last-child {
  border-bottom: 0;
}

.profile-section-title h3 {
  margin: 0;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 650;
}

.profile-section-body,
.profile-field {
  display: flex;
  flex-direction: column;
}

.profile-section-body {
  gap: 1rem;
}

.profile-form-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
}

.profile-field {
  gap: 0.375rem;
}

.profile-field label,
.profile-label-row label {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.profile-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.profile-label-row span {
  color: hsl(var(--muted-foreground) / 0.58);
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
}

.profile-input-wrap {
  position: relative;
}

.profile-input-icon {
  position: absolute;
  top: 50%;
  left: 0.75rem;
  width: 0.875rem;
  height: 0.875rem;
  color: hsl(var(--muted-foreground) / 0.55);
  transform: translateY(-50%);
  pointer-events: none;
}

.profile-input {
  height: 2.25rem;
  padding-left: 2.25rem;
  border-color: hsl(var(--border) / 0.6);
  border-radius: 0.5rem;
  font-size: 0.875rem;
  box-shadow: none;
}

.profile-avatar-preview {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.625rem;
  background: hsl(var(--muted) / 0.08);
}

.profile-avatar-preview-image {
  width: 3rem;
  height: 3rem;
  flex: 0 0 auto;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.3);
  border-radius: 0.5rem;
  background: hsl(var(--muted));
}

.profile-avatar-preview-copy {
  min-width: 0;
}

.profile-avatar-preview-copy p {
  margin: 0 0 0.25rem;
  color: hsl(var(--foreground));
  font-size: 0.75rem;
  font-weight: 650;
}

.profile-status {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.375rem;
  border: 1px solid;
  border-radius: 0.375rem;
  font-size: 0.6875rem;
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

.profile-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border: 1px solid hsl(var(--destructive) / 0.2);
  border-radius: 0.5rem;
  background: hsl(var(--destructive) / 0.05);
  color: hsl(var(--destructive));
  font-size: 0.75rem;
}

.profile-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-top: 0.25rem;
}

.profile-save-button,
.profile-logout-button {
  height: 2.25rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    border-color 0.16s ease,
    opacity 0.16s ease;
}

.profile-save-button.is-disabled {
  border: 1px solid hsl(var(--border) / 0.3);
  background: hsl(var(--muted));
  color: hsl(var(--muted-foreground) / 0.6);
  cursor: not-allowed;
}

.profile-saved {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: hsl(var(--success));
  font-size: 0.75rem;
  font-weight: 500;
}

.profile-logout-button {
  border-color: hsl(var(--border) / 0.8);
  color: hsl(var(--muted-foreground));
}

.profile-logout-button:hover {
  border-color: hsl(var(--destructive));
  background: hsl(var(--destructive));
  color: hsl(var(--destructive-foreground));
}

@media (max-width: 760px) {
  .profile-section {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .profile-avatar-control,
  .profile-avatar-mask,
  .profile-save-button,
  .profile-logout-button {
    transition: none;
  }
}
</style>
