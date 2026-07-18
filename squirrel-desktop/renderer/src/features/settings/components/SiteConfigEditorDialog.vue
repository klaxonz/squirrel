<template>
  <Dialog :open="visible" @update:open="!$event && $emit('close')">
    <DialogContent class="app-dialog-surface site-editor-dialog max-w-xl">
      <DialogHeader class="app-dialog-form-header site-editor-header">
        <div class="site-editor-title-row">
          <SiteIcon
            :icon-url="siteEditorForm.iconUrl"
            :label="siteEditorForm.label || siteEditorForm.slug"
            size="sm"
            rounded="sm"
          />
          <div>
            <DialogTitle class="app-dialog-form-title">站点配置</DialogTitle>
            <DialogDescription class="app-dialog-form-description">{{ siteEditorForm.slug }}</DialogDescription>
          </div>
        </div>
        <Button text severity="secondary" size="sm" icon-only class="text-muted-foreground" aria-label="关闭" @click="$emit('close')">
          <AppIcon name="close" class="h-3.5 w-3.5" />
        </Button>
      </DialogHeader>

      <div class="app-dialog-form-body app-dialog-form-body--scroll site-editor-scroll">
        <section class="site-editor-section">
          <div class="app-settings-section-title">
            <h3>基本参数</h3>
          </div>
          <div class="site-editor-fields">
            <div class="site-editor-field">
              <label class="app-dialog-form-label" for="site-editor-label">显示名称</label>
              <Input fluid id="site-editor-label" v-model="siteEditorForm.label" placeholder="展示给用户的名称" class="app-form-input" />
            </div>
            <div class="site-editor-field">
              <label class="app-dialog-form-label" for="site-editor-aliases">站点别名</label>
              <Textarea fluid id="site-editor-aliases" v-model="siteEditorForm.aliasesText" :rows="2" placeholder="每行一个别名" class="app-form-input site-editor-textarea" />
            </div>
            <div class="site-editor-field">
              <label class="app-dialog-form-label" for="site-editor-domains">域名</label>
              <Textarea fluid
                id="site-editor-domains"
                :model-value="siteEditorForm.domainsText"
                :rows="2"
                readonly
                class="app-form-input site-editor-textarea text-muted-foreground/70"
              />
            </div>
            <div class="site-editor-switch-row">
              <span>启用站点</span>
              <Switch :model-value="!!siteEditorForm.enabled" @update:model-value="(v) => setSiteEditorBooleanField('enabled', v)" />
            </div>
          </div>
        </section>

        <section class="site-editor-section">
          <div class="app-settings-section-title">
            <h3>采集策略</h3>
          </div>
          <div class="site-editor-fields">
            <div class="site-editor-field">
              <label class="app-dialog-form-label" for="site-editor-test-url">测试地址</label>
              <Input fluid id="site-editor-test-url" v-model="siteEditorForm.testUrl" placeholder="用于连通性检测的地址" class="app-form-input" />
            </div>
            <div class="site-editor-rate-row">
              <label class="app-dialog-form-label">频率限制</label>
              <div class="site-editor-rate-controls">
                <Switch :model-value="!!siteEditorForm.rateLimitEnabled" @update:model-value="(v) => setSiteEditorBooleanField('rateLimitEnabled', v)" />
                <span v-if="siteEditorForm.rateLimitEnabled" class="site-editor-rate-inputs">
                  <Input fluid v-model="siteEditorForm.rateLimitMin" type="number" step="0.1" class="app-form-input site-editor-number-input" placeholder="最小" />
                  <span>~</span>
                  <Input fluid v-model="siteEditorForm.rateLimitMax" type="number" step="0.1" class="app-form-input site-editor-number-input" placeholder="最大" />
                  <span>秒</span>
                </span>
              </div>
            </div>
          </div>
        </section>

        <section class="site-editor-section">
          <div class="app-settings-section-title">
            <h3>内容标记</h3>
          </div>
          <div class="site-editor-flags">
            <label
              v-for="meta in [
                { key: 'metadataNsfw', label: '默认标记为敏感内容' },
                { key: 'metadataRequiresCookies', label: '需要登录凭据才可抓取' },
                { key: 'metadataRequiresLogin', label: '需要登录状态' },
                { key: 'metadataOfflineThumbnailsDownload', label: '解析时下载封面到本地' },
                { key: 'metadataOfflineThumbnailsDisplay', label: '优先使用本地封面显示' }
              ]"
              :key="meta.key"
              class="site-editor-flag-row"
            >
              <span>{{ meta.label }}</span>
              <Switch :model-value="!!siteEditorForm[meta.key]" @update:model-value="(v) => setSiteEditorBooleanField(meta.key, v)" />
            </label>
          </div>
        </section>

        <Transition name="fade">
          <div v-if="resolvedError" class="app-dialog-message is-error">
            <AppIcon name="warning" class="h-3.5 w-3.5 shrink-0" />
            {{ resolvedError }}
          </div>
        </Transition>
      </div>

      <DialogFooter class="app-dialog-form-footer app-dialog-form-footer--end">
        <Button
          size="sm"
          text severity="secondary"
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

:deep(.site-editor-dialog) {
  display: flex;
  max-height: 80vh;
  flex-direction: column;
}

.site-editor-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.site-editor-title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-3);
}

.site-editor-section,
.site-editor-fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.site-editor-section + .site-editor-section {
  padding-top: var(--space-2);
}

.site-editor-field {
  display: grid;
  grid-template-columns: 4.5rem minmax(0, 1fr);
  align-items: start;
  gap: var(--space-2);
}

.site-editor-textarea {
  min-height: 3.5rem;
  resize: none;
}

.site-editor-switch-row,
.site-editor-rate-row,
.site-editor-flag-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.site-editor-switch-row,
.site-editor-flag-row {
  min-height: 2rem;
  color: hsl(var(--foreground) / 0.86);
  font-size: 0.75rem;
  font-weight: 500;
}

.site-editor-flag-row {
  padding: 0.25rem 0;
  cursor: pointer;
}

.site-editor-rate-controls,
.site-editor-rate-inputs {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  align-items: center;
  gap: var(--space-2);
}

.site-editor-rate-inputs {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.site-editor-number-input {
  width: 4rem;
  height: 1.875rem;
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
