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
        <Button variant="secondary" size="sm" icon-only class="text-muted-foreground" aria-label="关闭" @click="$emit('close')">
          <AppIcon name="close" class="h-3.5 w-3.5" />
        </Button>
      </DialogHeader>

      <form id="site-editor-form" class="app-dialog-form-body app-dialog-form-body--scroll site-editor-scroll" novalidate @submit.prevent="handleSave">
        <section class="site-editor-section">
          <div class="app-settings-section-title">
            <h3>基本参数</h3>
          </div>
          <div class="site-editor-fields">
            <AppFormField
              id="site-editor-label"
              label="显示名称"
              description="展示给用户的站点名称。"
              :error="fieldErrors.label"
              required
              class="site-editor-field"
            >
              <template #default="{ control }">
                <Input v-bind="control" v-model="siteEditorForm.label" fluid placeholder="展示给用户的名称" class="app-form-input" />
              </template>
            </AppFormField>
            <AppFormField
              id="site-editor-aliases"
              label="站点别名"
              description="每行输入一个可用于识别站点的别名。"
              class="site-editor-field"
            >
              <template #default="{ control }">
                <Textarea v-bind="control" v-model="siteEditorForm.aliasesText" fluid :rows="2" placeholder="每行一个别名" class="app-form-input site-editor-textarea" />
              </template>
            </AppFormField>
            <AppFormField
              id="site-editor-domains"
              label="域名"
              description="域名由站点运行时提供，无法在此修改。"
              class="site-editor-field"
            >
              <template #default="{ control }">
                <Textarea
                  v-bind="control"
                  :model-value="siteEditorForm.domainsText"
                  fluid
                  :rows="2"
                  readonly
                  class="app-form-input site-editor-textarea text-muted-foreground/70"
                />
              </template>
            </AppFormField>
            <div class="site-editor-switch-row">
              <label id="site-editor-enabled-label" for="site-editor-enabled">启用站点</label>
              <Switch
                id="site-editor-enabled"
                :model-value="!!siteEditorForm.enabled"
                aria-labelledby="site-editor-enabled-label"
                @update:model-value="(v) => setSiteEditorBooleanField('enabled', v)"
              />
            </div>
          </div>
        </section>

        <section class="site-editor-section">
          <div class="app-settings-section-title">
            <h3>采集策略</h3>
          </div>
          <div class="site-editor-fields">
            <AppFormField
              id="site-editor-test-url"
              label="测试地址"
              description="可选，用于站点连通性检测的 HTTP 或 HTTPS 地址。"
              :error="fieldErrors.testUrl"
              class="site-editor-field"
            >
              <template #default="{ control }">
                <Input v-bind="control" v-model="siteEditorForm.testUrl" fluid type="url" placeholder="用于连通性检测的地址" class="app-form-input" />
              </template>
            </AppFormField>
            <fieldset class="site-editor-rate-fieldset">
              <legend>频率限制</legend>
              <div class="site-editor-rate-controls">
                <label id="site-editor-rate-enabled-label" class="sr-only" for="site-editor-rate-enabled">启用频率限制</label>
                <Switch
                  id="site-editor-rate-enabled"
                  :model-value="!!siteEditorForm.rateLimitEnabled"
                  aria-labelledby="site-editor-rate-enabled-label"
                  @update:model-value="(v) => setSiteEditorBooleanField('rateLimitEnabled', v)"
                />
                <div v-if="siteEditorForm.rateLimitEnabled" class="site-editor-rate-inputs">
                  <AppFormField
                    id="site-editor-rate-min"
                    label="最小间隔"
                    description="秒"
                    :error="fieldErrors.rateLimitMin"
                    required
                    class="site-editor-rate-number-field"
                  >
                    <template #default="{ control }">
                      <Input v-bind="control" v-model="siteEditorForm.rateLimitMin" fluid type="number" min="0" step="0.1" class="app-form-input site-editor-number-input" />
                    </template>
                  </AppFormField>
                  <AppFormField
                    id="site-editor-rate-max"
                    label="最大间隔"
                    description="秒"
                    :error="fieldErrors.rateLimitMax"
                    required
                    class="site-editor-rate-number-field"
                  >
                    <template #default="{ control }">
                      <Input v-bind="control" v-model="siteEditorForm.rateLimitMax" fluid type="number" min="0" step="0.1" class="app-form-input site-editor-number-input" />
                    </template>
                  </AppFormField>
                </div>
              </div>
            </fieldset>
          </div>
        </section>

        <section class="site-editor-section">
          <div class="app-settings-section-title">
            <h3>内容标记</h3>
          </div>
          <fieldset class="site-editor-flags">
            <legend class="sr-only">站点内容和抓取选项</legend>
            <div
              v-for="meta in metadataSwitches"
              :key="meta.key"
              class="site-editor-flag-row"
            >
              <label :id="`site-editor-${meta.key}-label`" :for="`site-editor-${meta.key}`">{{ meta.label }}</label>
              <Switch
                :id="`site-editor-${meta.key}`"
                :model-value="!!siteEditorForm[meta.key]"
                :aria-labelledby="`site-editor-${meta.key}-label`"
                @update:model-value="(v) => setSiteEditorBooleanField(meta.key, v)"
              />
            </div>
          </fieldset>
        </section>

        <Transition name="fade">
          <div v-if="resolvedError" class="app-dialog-message is-error" role="alert">
            <AppIcon name="warning" class="h-3.5 w-3.5 shrink-0" />
            {{ resolvedError }}
          </div>
        </Transition>
      </form>

      <DialogFooter class="app-dialog-form-footer app-dialog-form-footer--end">
        <Button size="sm" variant="secondary" @click="$emit('close')">
          取消
        </Button>
        <Button type="submit" form="site-editor-form" size="sm" :loading="saving">
          {{ saving ? '保存中...' : '保存' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { computed } from 'vue'

import AppFormField from '@/shared/components/layout/AppFormField.vue'
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

const emit = defineEmits(['close', 'save'])

const metadataSwitches = [
  { key: 'metadataNsfw', label: '默认标记为敏感内容' },
  { key: 'metadataRequiresCookies', label: '需要登录凭据才可抓取' },
  { key: 'metadataRequiresLogin', label: '需要登录状态' },
  { key: 'metadataOfflineThumbnailsDownload', label: '解析时下载封面到本地' },
  { key: 'metadataOfflineThumbnailsDisplay', label: '优先使用本地封面显示' },
]

const {
  siteEditorForm,
  resolvedError,
  fieldErrors,
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

:deep(.site-editor-field) {
  display: grid;
  grid-template-columns: 4.5rem minmax(0, 1fr);
  align-items: start;
  gap: var(--space-2);
}

:deep(.site-editor-field > .app-form-field__control),
:deep(.site-editor-field > .app-form-field__description),
:deep(.site-editor-field > .app-form-field__error) {
  grid-column: 2;
}

.site-editor-textarea {
  min-height: 3.5rem;
  resize: none;
}

.site-editor-switch-row,
.site-editor-flag-row {
  display: flex;
  min-height: 2rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  color: hsl(var(--foreground) / 0.86);
  font-size: var(--app-text-sm);
  font-weight: 500;
}

.site-editor-rate-fieldset {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  border: 0;
}

.site-editor-rate-fieldset > legend {
  color: hsl(var(--foreground));
  font-size: var(--app-text-md);
  font-weight: 600;
}

.site-editor-rate-controls,
.site-editor-rate-inputs {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: var(--space-3);
}

.site-editor-rate-inputs {
  flex: 1 1 auto;
}

:deep(.site-editor-rate-number-field) {
  flex: 1 1 0;
}

.site-editor-number-input {
  min-width: 0;
  height: 1.875rem;
}

.site-editor-flags {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  border: 0;
}

.site-editor-flag-row {
  padding: 0.25rem 0;
}

.site-editor-flag-row label,
.site-editor-switch-row label {
  cursor: pointer;
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
