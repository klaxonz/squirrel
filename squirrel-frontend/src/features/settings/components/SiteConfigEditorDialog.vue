<template>
  <Dialog :open="visible" @update:open="!$event && $emit('close')">
    <DialogContent class="flex max-h-[80vh] w-full max-w-xl flex-col gap-0 overflow-hidden rounded-lg p-0">
      <!-- Header -->
      <DialogHeader class="flex flex-row items-center justify-between space-y-0 border-b border-border/50 px-4 py-3 text-left">
        <div class="flex items-center gap-3">
          <SiteIcon
            :icon-url="siteEditorForm.iconUrl"
            :label="siteEditorForm.label || siteEditorForm.slug"
            size="sm"
            rounded="sm"
          />
          <div>
            <DialogTitle class="text-sm font-medium text-foreground">站点配置</DialogTitle>
            <DialogDescription class="text-[11px] text-muted-foreground">{{ siteEditorForm.slug }}</DialogDescription>
          </div>
        </div>
        <DialogClose as-child>
          <Button variant="ghost" size="icon" class="h-7 w-7 rounded text-muted-foreground hover:bg-muted/60" aria-label="关闭">
            <AppIcon name="close" class="h-3.5 w-3.5" />
          </Button>
        </DialogClose>
      </DialogHeader>

      <!-- Content -->
      <div class="site-editor-scroll flex-1 px-4 py-4 overflow-y-auto">

        <!-- 基本参数 -->
        <section class="mb-5">
          <h4 class="text-[11px] font-medium text-muted-foreground uppercase mb-3">基本参数</h4>
          <div class="space-y-2.5">
            <div class="flex items-center gap-2">
              <label class="text-[11px] text-muted-foreground w-16 shrink-0" for="site-editor-label">显示名称</label>
              <Input id="site-editor-label" v-model="siteEditorForm.label" placeholder="展示给用户的名称" class="flex-1 h-7 text-xs" />
            </div>
            <div class="flex items-center gap-2">
              <label class="text-[11px] text-muted-foreground w-16 shrink-0" for="site-editor-aliases">站点别名</label>
              <Textarea id="site-editor-aliases" v-model="siteEditorForm.aliasesText" :rows="2" placeholder="每行一个别名" class="flex-1 text-xs resize-none" />
            </div>
            <div class="flex items-center gap-2">
              <label class="text-[11px] text-muted-foreground w-16 shrink-0" for="site-editor-domains">域名</label>
              <Textarea
                id="site-editor-domains"
                :model-value="siteEditorForm.domainsText"
                :rows="2"
                readonly
                class="flex-1 text-xs resize-none text-muted-foreground/70"
              />
            </div>
            <div class="flex items-center justify-between py-1">
              <span class="text-xs text-foreground">启用站点</span>
              <Switch :checked="!!siteEditorForm.enabled" @update:checked="(v) => setSiteEditorBooleanField('enabled', v)" />
            </div>
          </div>
        </section>

        <!-- 采集策略 -->
        <section class="mb-5">
          <h4 class="text-[11px] font-medium text-muted-foreground uppercase mb-3">采集策略</h4>
          <div class="space-y-2.5">
            <div class="flex items-center gap-2">
              <label class="text-[11px] text-muted-foreground w-16 shrink-0" for="site-editor-test-url">测试地址</label>
              <Input id="site-editor-test-url" v-model="siteEditorForm.testUrl" placeholder="用于连通性检测的地址" class="flex-1 h-7 text-xs" />
            </div>
            <div class="flex items-center gap-2">
              <label class="text-[11px] text-muted-foreground w-16 shrink-0">频率限制</label>
              <div class="flex items-center gap-2 flex-1">
                <Switch :checked="!!siteEditorForm.rateLimitEnabled" @update:checked="(v) => setSiteEditorBooleanField('rateLimitEnabled', v)" />
                <span v-if="siteEditorForm.rateLimitEnabled" class="flex items-center gap-1.5 text-[11px]">
                  <Input v-model="siteEditorForm.rateLimitMin" type="number" step="0.1" class="w-16 h-6 text-xs" placeholder="最小" />
                  <span class="text-muted-foreground/60">~</span>
                  <Input v-model="siteEditorForm.rateLimitMax" type="number" step="0.1" class="w-16 h-6 text-xs" placeholder="最大" />
                  <span class="text-muted-foreground/60">秒</span>
                </span>
              </div>
            </div>
          </div>
        </section>

        <!-- 内容标记 -->
        <section>
          <h4 class="text-[11px] font-medium text-muted-foreground uppercase mb-3">内容标记</h4>
          <div class="space-y-0.5">
            <label
              v-for="meta in [
                { key: 'metadataNsfw', label: '默认标记为敏感内容' },
                { key: 'metadataRequiresCookies', label: '需要登录凭据才可抓取' },
                { key: 'metadataRequiresLogin', label: '需要登录状态' },
                { key: 'metadataOfflineThumbnailsDownload', label: '解析时下载封面到本地' },
                { key: 'metadataOfflineThumbnailsDisplay', label: '优先使用本地封面显示' }
              ]"
              :key="meta.key"
              class="flex items-center justify-between py-1.5 px-1 rounded hover:bg-muted/40 transition-colors cursor-pointer"
            >
              <span class="text-xs text-foreground/80">{{ meta.label }}</span>
              <Switch :checked="!!siteEditorForm[meta.key]" @update:checked="(v) => setSiteEditorBooleanField(meta.key, v)" />
            </label>
          </div>
        </section>

        <Transition name="fade">
          <div v-if="resolvedError" class="mt-4 p-2.5 rounded text-destructive text-xs flex items-center gap-2">
            <AppIcon name="warning" class="h-3.5 w-3.5 shrink-0" />
            {{ resolvedError }}
          </div>
        </Transition>
      </div>

      <!-- Footer -->
      <DialogFooter class="border-t border-border/50 px-4 py-3 sm:justify-end">
        <Button
          size="sm"
          variant="ghost"
          @click="$emit('close')"
        >
          取消
        </Button>
        <Button
          size="sm"
          :loading="saving"
          @click="handleSave"
        >
          {{ saving ? '保存中...' : '保存' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { computed } from 'vue';

import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import { Switch } from '@/shared/ui/switch'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'
import { useSiteConfigEditorForm } from '@/features/settings/composables/useSiteConfigEditorForm'

const props = defineProps({
  visible: { type: Boolean, default: false },
  site: { type: Object, default: null },
  catalog: { type: Object, default: () => ({}) },
  saving: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' }
})

const emit = defineEmits(['close', 'save']);

// ponytail: the form model + hydrate/validate/serialize state machine + the
// open/close + site/catalog hydration watchers live in useSiteConfigEditorForm.
// The converters (headers<->text, list parse, number-or-undefined) live in the
// shared siteConfigFormConverters lib. This view is now a thin shell that binds
// the form to the template and forwards the serialised payload to its API call.
const {
  siteEditorForm,
  resolvedError,
  setSiteEditorBooleanField,
  handleSave,
} = useSiteConfigEditorForm({
  visible: computed(() => props.visible),
  site: computed(() => props.site),
  catalog: computed(() => props.catalog),
  errorMessage: computed(() => props.errorMessage),
  onSave: (payload) => emit('save', payload),
})
</script>

<style scoped>
.site-editor-scroll {
  scrollbar-width: thin;
  scrollbar-color: hsl(var(--muted)) transparent;
}

.site-editor-scroll::-webkit-scrollbar {
  width: 6px;
}

.site-editor-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.site-editor-scroll::-webkit-scrollbar-thumb {
  background-color: hsl(var(--muted));
  border-radius: 9999px;
}

.site-editor-scroll::-webkit-scrollbar-thumb:hover {
  background-color: hsl(var(--accent));
}

.site-editor-scroll input[type='number'] {
  -moz-appearance: textfield;
}

.site-editor-scroll input[type='number']::-webkit-outer-spin-button,
.site-editor-scroll input[type='number']::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity var(--duration-normal) var(--ease-default);
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
