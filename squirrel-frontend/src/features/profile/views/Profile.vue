<template>
  <AppPageShell variant="default" scrollable>
    <div class="mx-auto w-full max-w-[720px] py-8 space-y-8 bg-background text-foreground transition-all duration-300">
      
      <!-- Profile Header Area (Sleek & Minimalist) -->
      <div class="flex items-center gap-5 border-b border-border/40 pb-6">
        <!-- Avatar with smooth hover ring & camera icon -->
        <div 
          class="group relative h-16 w-16 shrink-0 overflow-hidden rounded-full border border-border/50 bg-muted shadow-sm cursor-pointer transition-all duration-300 hover:ring-4 hover:ring-primary/10 active:scale-95"
          @click="focusAvatarInput"
        >
          <img
            v-if="form.avatar && !avatarError"
            :src="form.avatar"
            :alt="form.nickname ? `${form.nickname}的头像` : '用户头像'"
            class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
          <div 
            v-else 
            class="flex h-full w-full items-center justify-center bg-gradient-to-br from-primary/10 to-violet-500/10 text-xl font-bold text-primary"
          >
            <template v-if="userInitial">{{ userInitial }}</template>
            <AppIcon v-else name="user" class="h-6 w-6 text-primary/75" />
          </div>
          <!-- Hover mask -->
          <div class="absolute inset-0 flex flex-col items-center justify-center bg-black/45 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
            <AppIcon name="camera" class="h-3.5 w-3.5 text-white" />
          </div>
        </div>

        <!-- User Details -->
        <div class="space-y-0.5">
          <h2 class="text-lg font-bold tracking-tight text-foreground">
            {{ userStore.currentUser?.nickname || '未设置昵称' }}
          </h2>
          <div v-if="createdAt" class="flex items-center gap-1 text-[10px] text-muted-foreground/60">
            <AppIcon name="time" class="h-3 w-3" />
            <span>注册于 {{ createdAt }}</span>
          </div>
        </div>
      </div>

      <!-- Settings Split Sections (Clean Minimalist Form) -->
      <div class="space-y-8 divide-y divide-border/40">
        
        <!-- Section 1: 基本资料 (Basic Info) -->
        <div class="grid gap-6 pt-6 md:grid-cols-4">
          <div class="md:col-span-1">
            <h3 class="text-sm font-semibold text-foreground">基本资料</h3>
          </div>
          
          <div class="md:col-span-3 space-y-4">
            <!-- Form Grid -->
            <div class="grid gap-4 sm:grid-cols-2">
              <!-- Nickname input -->
              <div class="space-y-1.5">
                <div class="flex items-center justify-between">
                  <label class="text-xs font-medium text-muted-foreground">昵称</label>
                  <span class="text-[10px] text-muted-foreground/40 font-mono">{{ form.nickname.length }}/50</span>
                </div>
                <div class="relative">
                  <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-muted-foreground/50">
                    <AppIcon name="user" class="h-3.5 w-3.5" />
                  </div>
                  <Input
                    v-model="form.nickname"
                    placeholder="请输入昵称"
                    class="h-9 pl-9 rounded-lg border-border/60 text-sm shadow-none focus-visible:ring-1 focus-visible:ring-primary focus-visible:border-primary/50"
                    maxlength="50"
                  />
                </div>
              </div>

            </div>

            <!-- Avatar URL -->
            <div class="space-y-1.5">
              <label class="text-xs font-medium text-muted-foreground">头像图片链接 (URL)</label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-muted-foreground/50">
                  <AppIcon name="link" class="h-3.5 w-3.5" />
                </div>
                <Input
                  ref="avatarInput"
                  v-model="form.avatar"
                  placeholder="输入图片链接 (HTTPS)"
                  class="h-9 pl-9 rounded-lg border-border/60 text-sm shadow-none focus-visible:ring-1 focus-visible:ring-primary focus-visible:border-primary/50"
                />
              </div>
            </div>

            <!-- Avatar Preview card (Only shown if avatar URL is present) -->
            <div v-if="form.avatar" class="transition-all duration-300">
              <div class="flex items-center gap-4 rounded-xl border border-border/50 bg-muted/5 p-3">
                <div class="relative h-12 w-12 shrink-0 overflow-hidden rounded-full border border-border/30 bg-muted shadow-inner">
                  <img
                    :src="form.avatar"
                    :alt="form.nickname ? `${form.nickname}的头像` : '用户头像'"
                    class="h-full w-full object-cover"
                    @error="avatarError = true"
                    @load="avatarError = false"
                  />
                </div>
                <div class="space-y-0.5 min-w-0">
                  <p class="text-xs font-semibold text-foreground">头像实时预览</p>
                  <span 
                    v-if="avatarError" 
                    class="inline-flex items-center gap-1 rounded bg-destructive/5 px-1.5 py-0.5 text-[9px] font-medium text-destructive border border-destructive/10"
                  >
                    <AppIcon name="warning" class="h-2.5 w-2.5" />
                    图片加载失败，请检查链接
                  </span>
                  <span 
                    v-else 
                    class="inline-flex items-center gap-1 rounded bg-emerald-500/5 px-1.5 py-0.5 text-[9px] font-medium text-emerald-600 border border-emerald-500/10"
                  >
                    <AppIcon name="check" class="h-2.5 w-2.5" />
                    图片加载成功
                  </span>
                </div>
              </div>
            </div>

            <!-- Error Feedback -->
            <div v-if="saveError" class="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 p-3 text-xs text-destructive">
              <AppIcon name="warning" class="h-3.5 w-3.5 shrink-0" />
              <span>{{ saveError }}</span>
            </div>

            <!-- Action buttons -->
            <div class="flex items-center gap-3 pt-1">
              <Button
                class="h-9 rounded-lg px-4 text-xs font-medium shadow-[0_1px_2px_rgba(0,0,0,0.05)] transition-all duration-200"
                :class="hasChanges ? 'bg-primary text-primary-foreground hover:opacity-90' : 'bg-muted text-muted-foreground/60 border border-border/30 cursor-not-allowed'"
                :loading="saving"
                :disabled="!hasChanges"
                @click="handleSave"
              >
                保存修改
              </Button>
              
              <span 
                v-if="saved" 
                class="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 animate-in fade-in duration-300"
              >
                <AppIcon name="check" class="h-3.5 w-3.5" />
                所有更改已保存
              </span>
            </div>

          </div>
        </div>

        <!-- Section 2: 退出登录 (Logout) -->
        <div class="grid gap-6 pt-6 md:grid-cols-4">
          <div class="md:col-span-1">
            <h3 class="text-sm font-semibold text-foreground">会话管理</h3>
          </div>
          
          <div class="md:col-span-3">
            <Button
              variant="outline"
              class="h-9 border-border/80 text-xs font-medium text-muted-foreground hover:bg-destructive hover:text-white hover:border-destructive transition-all duration-200"
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
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Logger } from '@/shared/lib/logger'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { useUserStore } from '@/shared/stores/user'

const router = useRouter()
const userStore = useUserStore()

const form = reactive({
  nickname: '',
  avatar: '',
})

const saving = ref(false)
const saved = ref(false)
const saveError = ref('')
let savedTimer: ReturnType<typeof setTimeout> | null = null
onUnmounted(() => {
  if (savedTimer) clearTimeout(savedTimer)
})
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

const hasChanges = computed(() => {
  if (!userStore.currentUser) return false
  return form.nickname !== (userStore.currentUser.nickname || '')
    || form.avatar !== (userStore.currentUser.avatar || '')
})

onMounted(() => {
  if (userStore.currentUser) {
    form.nickname = userStore.currentUser.nickname || ''
    form.avatar = userStore.currentUser.avatar || ''
  }
})

const focusAvatarInput = () => {
  if (avatarInput.value) {
    const inputEl = (avatarInput.value.$el?.querySelector?.('input') as HTMLElement | null) ?? avatarInput.value.$el;
    inputEl?.focus?.();
  }
}

const handleSave = async () => {
  saving.value = true
  saved.value = false
  saveError.value = ''

  const payload: Record<string, string> = {}
  if (form.nickname !== (userStore.currentUser?.nickname || '')) {
    payload.nickname = form.nickname
  }
  if (form.avatar !== (userStore.currentUser?.avatar || '')) {
    payload.avatar = form.avatar
  }

  if (!Object.keys(payload).length) {
    saving.value = false
    return
  }

  const result = await userStore.updateProfile(payload)
  saving.value = false
  if (result.error) {
    saveError.value = (result.error instanceof Error ? result.error.message : null) || '保存失败'
  } else {
    saved.value = true
    if (savedTimer) clearTimeout(savedTimer)
    savedTimer = setTimeout(() => { saved.value = false }, 3000)
  }
}

const handleLogout = async () => {
  await userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
</style>
