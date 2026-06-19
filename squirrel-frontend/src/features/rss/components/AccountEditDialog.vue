<template>
  <Dialog :open="open">
    <DialogContent class="max-w-md overflow-hidden rounded-xl p-0 border border-border/30 bg-background/95 backdrop-blur-xl shadow-xl transition-all duration-200">
      <DialogHeader class="border-b border-border/10 p-5 text-left">
        <DialogTitle class="text-base font-bold text-foreground">
          {{ form.id ? '编辑 RSS 账号' : '添加 RSS 账号' }}
        </DialogTitle>
        <DialogDescription class="text-xs text-muted-foreground mt-1 leading-normal">
          连接第三方 RSS 服务账号，支持 Google Reader API, Miniflux, Fever 等规范。
        </DialogDescription>
      </DialogHeader>

      <div class="p-5 space-y-4 max-h-[60vh] overflow-y-auto custom-scrollbar">
        <!-- Provider Select (Segmented Switcher) -->
        <div class="space-y-1.5">
          <label class="text-xs font-semibold text-foreground/80">服务提供商</label>
          <div class="flex p-0.5 bg-muted/40 dark:bg-muted/10 rounded-lg border border-border/10">
            <button
              v-for="prov in providers"
              :key="prov.value"
              type="button"
              @click="form.provider = prov.value"
              class="flex-1 py-1.5 text-xs font-semibold rounded-md transition-all duration-200 text-center cursor-pointer flex items-center justify-center gap-1.5 select-none"
              :class="form.provider === prov.value
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'"
            >
              <AppIcon :name="prov.icon" class="h-3.5 w-3.5 shrink-0" />
              <span>{{ prov.name }}</span>
            </button>
          </div>
        </div>

        <!-- Account Name -->
        <div class="space-y-1.5">
          <label class="text-xs font-semibold text-foreground/80">账号名称</label>
          <div class="relative group">
            <AppIcon name="pencil" class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50 group-focus-within:text-foreground transition-colors duration-200" />
            <Input
              v-model="form.name"
              class="h-9 rounded-lg pl-9 pr-3.5 border border-border/40 bg-accent/10 hover:bg-accent/15 focus-visible:bg-background focus-visible:border-primary/40 focus-visible:ring-1 focus-visible:ring-primary/20 text-xs font-medium shadow-none transition-all duration-200"
              placeholder="例如: 我的 Miniflux"
            />
          </div>
        </div>

        <!-- Base URL -->
        <div class="space-y-1.5">
          <label class="text-xs font-semibold text-foreground/80">服务接口地址 (URL)</label>
          <div class="relative group">
            <AppIcon name="link" class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50 group-focus-within:text-foreground transition-colors duration-200" />
            <Input
              v-model="form.base_url"
              class="h-9 rounded-lg pl-9 pr-3.5 border border-border/40 bg-accent/10 hover:bg-accent/15 focus-visible:bg-background focus-visible:border-primary/40 focus-visible:ring-1 focus-visible:ring-primary/20 text-xs font-medium shadow-none transition-all duration-200"
              :placeholder="baseUrlPlaceholder"
            />
          </div>
        </div>

        <!-- Username -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <label class="text-xs font-semibold text-foreground/80">用户名</label>
            <span
              v-if="form.provider === 'greader' || form.provider === 'fever'"
              class="text-[10px] text-destructive/80 font-bold animate-fade-in"
            >
              * 必填
            </span>
          </div>
          <div class="relative group">
            <AppIcon name="user" class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50 group-focus-within:text-foreground transition-colors duration-200" />
            <Input
              v-model="form.username"
              class="h-9 rounded-lg pl-9 pr-3.5 border border-border/40 bg-accent/10 hover:bg-accent/15 focus-visible:bg-background focus-visible:border-primary/40 focus-visible:ring-1 focus-visible:ring-primary/20 text-xs font-medium shadow-none transition-all duration-200"
              placeholder="用户名 (Google Reader 与 Fever 需要)"
            />
          </div>
        </div>

        <!-- Credential -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <label class="text-xs font-semibold text-foreground/80">{{ credentialPlaceholder }}</label>
            <span
              v-if="!form.id"
              class="text-[10px] text-destructive/80 font-bold animate-fade-in"
            >
              * 必填
            </span>
          </div>
          <div class="relative group">
            <AppIcon name="security" class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50 group-focus-within:text-foreground transition-colors duration-200" />
            <Input
              v-model="form.credential"
              type="password"
              class="h-9 rounded-lg pl-9 pr-3.5 border border-border/40 bg-accent/10 hover:bg-accent/15 focus-visible:bg-background focus-visible:border-primary/40 focus-visible:ring-1 focus-visible:ring-primary/20 text-xs font-medium shadow-none transition-all duration-200"
              :placeholder="form.id ? '留空表示不修改密码或 Token' : '密码或 API Token'"
            />
          </div>
        </div>

        <div class="h-px bg-border/10 my-2"></div>

        <!-- Enabled Switch -->
        <div class="flex items-center justify-between py-1.5 select-none">
          <div class="flex flex-col text-left pr-4">
            <span class="text-xs font-semibold text-foreground/90">启用此账号同步</span>
            <span class="text-[10px] text-muted-foreground/60 mt-0.5 leading-normal">开启后系统将自动定期在后台同步此账号的订阅内容</span>
          </div>
          <button
            type="button"
            @click="form.enabled = !form.enabled"
            class="relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
            :class="form.enabled ? 'bg-foreground' : 'bg-muted/80'"
          >
            <span
              class="pointer-events-none inline-block h-4 w-4 transform rounded-full bg-background shadow-sm transition duration-200 ease-in-out"
              :class="form.enabled ? 'translate-x-4' : 'translate-x-0'"
            />
          </button>
        </div>

        <!-- Error / Success Message -->
        <Transition name="fade">
          <div
            v-if="formMessage"
            class="flex items-start gap-2 p-2.5 rounded-lg border text-xs leading-relaxed animate-fade-in"
            :class="formError ? 'border-destructive/20 bg-destructive/5 text-destructive' : 'border-emerald-500/20 bg-emerald-500/5 text-emerald-500'"
          >
            <AppIcon
              :name="formError ? 'error' : 'check'"
              class="h-3.5 w-3.5 shrink-0 mt-0.5"
              :class="formError ? 'text-destructive' : 'text-emerald-500'"
            />
            <span class="font-medium">{{ formMessage }}</span>
          </div>
        </Transition>
      </div>

      <DialogFooter class="gap-2 bg-muted/20 dark:bg-muted/5 p-4 border-t border-border/10 flex flex-row items-center justify-between">
        <Button
          type="button"
          variant="outline"
          class="h-9 rounded-lg text-xs font-semibold px-3 border border-border/40 hover:bg-accent/40 transition-colors cursor-pointer shrink-0"
          :disabled="testing || !canTestForm"
          @click="$emit('test')"
        >
          <AppIcon v-if="testing" name="refresh" class="h-3.5 w-3.5 mr-1.5 animate-spin text-foreground" />
          <AppIcon v-else name="sync" class="h-3.5 w-3.5 mr-1.5 opacity-70" />
          测试连接
        </Button>
        <div class="flex gap-2 justify-end">
          <Button
            type="button"
            variant="outline"
            class="h-9 rounded-lg text-xs font-semibold px-3 border border-border/40 hover:bg-accent/40 transition-colors cursor-pointer"
            @click="open = false"
          >
            取消
          </Button>
          <Button
            type="button"
            class="h-9 rounded-lg text-xs font-semibold px-4 transition-all duration-150 cursor-pointer bg-foreground text-background hover:opacity-90 active:scale-[0.98]"
            :disabled="saving || !canSaveForm"
            @click="$emit('save')"
          >
            <AppIcon v-if="saving" name="refresh" class="h-3.5 w-3.5 mr-1.5 animate-spin" />
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
