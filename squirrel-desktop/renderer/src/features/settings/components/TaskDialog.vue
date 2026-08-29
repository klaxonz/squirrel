<template>
  <Dialog :open="true" @update:open="!$event && $emit('close')">
    <DialogContent
      class="app-dialog-surface task-dialog"
      content-class="flex min-h-0 flex-1 flex-col overflow-hidden"
    >
      <DialogHeader class="app-dialog-form-header task-dialog__header">
        <div class="min-w-0">
          <DialogTitle class="app-dialog-form-title">
            {{ isEditing ? '编辑任务' : '新建任务' }}
          </DialogTitle>
          <DialogDescription class="app-dialog-form-description">
            {{ isEditing ? '更新调度频率、运行选项和任务参数。' : '选择执行逻辑并配置任务的调度规则。' }}
          </DialogDescription>
        </div>
        <Button variant="secondary" size="sm" icon-only aria-label="关闭任务对话框" @click="$emit('close')">
          <AppIcon name="close" class="h-4 w-4" />
        </Button>
      </DialogHeader>

      <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar">
        <form id="task-dialog-form" class="space-y-4 p-4" novalidate @submit.prevent="handleSubmit">
          <section class="space-y-4">
            <AppFormField
              id="task-dialog-name"
              label="任务名称"
              description="用于在任务列表中识别此调度任务。"
              :error="fieldErrors.name"
              required
            >
              <template #default="{ control }">
                <Input v-bind="control" v-model="formData.name" fluid placeholder="输入任务名称" />
              </template>
            </AppFormField>

            <AppFormField
              id="task-dialog-class"
              label="逻辑类"
              :description="isEditing ? '编辑任务时不可更改执行逻辑。' : '选择任务运行时使用的执行逻辑。'"
              :error="fieldErrors.task_class"
              required
            >
              <template #default="{ control }">
                <Select
                  v-bind="control"
                  v-model="formData.task_class"
                  :options="taskClassOptions"
                  option-label="label"
                  option-value="value"
                  option-group-label="label"
                  option-group-children="items"
                  placeholder="选择任务执行逻辑"
                  :disabled="isEditing"
                  fluid
                >
                  <template #option="{ option }">
                    <div class="flex min-w-0 flex-col">
                      <span class="font-medium">{{ option.label }}</span>
                      <span v-if="option.description" class="max-w-[300px] truncate text-xs text-muted-foreground">{{ option.description }}</span>
                    </div>
                  </template>
                </Select>
              </template>
            </AppFormField>

            <AppFormField
              id="task-dialog-desc"
              label="描述"
              description="可选，简要说明此任务的用途。"
            >
              <template #default="{ control }">
                <Textarea
                  v-bind="control"
                  v-model="formData.description"
                  fluid
                  placeholder="简要说明任务用途"
                  class="min-h-20"
                />
              </template>
            </AppFormField>
          </section>

          <section class="app-divider-top space-y-4 pt-5">
            <div class="task-dialog__schedule-grid">
              <AppFormField
                id="task-dialog-interval"
                label="执行间隔"
                description="必须是至少为 1 的整数。"
                :error="fieldErrors.interval"
                required
              >
                <template #default="{ control }">
                  <Input
                    v-bind="control"
                    v-model.number="formData.interval"
                    fluid
                    type="number"
                    min="1"
                    step="1"
                    class="tabular-nums"
                  />
                </template>
              </AppFormField>
              <AppFormField
                id="task-dialog-unit"
                label="单位"
                description="执行间隔所使用的时间单位。"
                :error="fieldErrors.unit"
                required
              >
                <template #default="{ control }">
                  <Select
                    v-bind="control"
                    v-model="formData.unit"
                    :options="intervalUnitOptions"
                    option-label="label"
                    option-value="value"
                    fluid
                  />
                </template>
              </AppFormField>
              <AppFormField
                id="task-dialog-retries"
                label="最大重试"
                description="必须是 0 或更大的整数。"
                :error="fieldErrors.max_retries"
                required
              >
                <template #default="{ control }">
                  <Input
                    v-bind="control"
                    v-model.number="formData.max_retries"
                    fluid
                    type="number"
                    min="0"
                    step="1"
                    class="tabular-nums"
                  />
                </template>
              </AppFormField>
            </div>

            <fieldset class="grid gap-2">
              <legend class="text-xs font-medium text-muted-foreground">运行选项</legend>
              <label class="app-surface app-surface--subtle flex h-10 items-center justify-between px-3" for="task-dialog-active">
                <span id="task-dialog-active-label" class="text-sm font-medium text-foreground">启用调度</span>
                <Switch id="task-dialog-active" v-model="formData.is_active" aria-labelledby="task-dialog-active-label" />
              </label>
              <label class="app-surface app-surface--subtle flex h-10 items-center justify-between px-3" for="task-dialog-start-immediately">
                <span id="task-dialog-start-immediately-label" class="text-sm font-medium text-foreground">立即执行一次</span>
                <Switch id="task-dialog-start-immediately" v-model="formData.start_immediately" aria-labelledby="task-dialog-start-immediately-label" />
              </label>
            </fieldset>
          </section>

          <section class="app-divider-top pt-5">
            <AppFormField
              id="task-dialog-params"
              label="任务参数"
              description="输入一个 JSON 对象；数组和其他 JSON 值不受支持。"
              :error="jsonError"
            >
              <template #default="{ control }">
                <Textarea
                  v-bind="control"
                  v-model="taskParamsJson"
                  fluid
                  rows="5"
                  class="font-mono bg-muted/30 px-4 py-3 text-xs text-foreground"
                  placeholder='{ "名称": "内容" }'
                />
              </template>
            </AppFormField>
          </section>
        </form>
      </div>

      <DialogFooter class="app-dialog-form-footer app-dialog-form-footer--end task-dialog__footer">
        <Button variant="outline" @click="$emit('close')">取消</Button>
        <Button type="submit" form="task-dialog-form" variant="contrast" :loading="loading">
          {{ isEditing ? '保存' : '创建' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import AppFormField from '@/shared/components/layout/AppFormField.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import { Switch } from '@/shared/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'
import { Select } from '@/shared/ui/select'
import { Logger } from '@/shared/lib/logger'

const props = defineProps({
  task: { type: Object, default: null },
  taskClasses: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['close', 'save'])

const isEditing = computed(() => !!props.task)
const loading = ref(false)
const jsonError = ref('')
const fieldErrors = ref({ name: '', task_class: '', interval: '', unit: '', max_retries: '' })

const intervalUnitOptions = [
  { value: 'seconds', label: '秒' },
  { value: 'minutes', label: '分钟' },
  { value: 'hours', label: '小时' },
  { value: 'days', label: '天' },
]

const taskClassOptions = computed(() => Object.entries(groupedTaskClasses.value).map(([label, group]) => ({
  label,
  items: Object.entries(group).map(([value, taskClass]) => ({
    value,
    label: taskClass.name,
    description: taskClass.description,
  })),
})))

const formData = ref({
  name: '',
  description: '',
  task_class: '',
  interval: 60,
  unit: 'seconds',
  start_immediately: true,
  max_retries: 3,
  task_params: {},
  is_active: true
})

const taskParamsJson = ref('{}')

const groupedTaskClasses = computed(() => {
  const groups = {}
  Object.entries(props.taskClasses).forEach(([className, taskClass]) => {
    const module = taskClass.module || '默认'
    if (!groups[module]) groups[module] = {}
    groups[module][className] = taskClass
  })
  return groups
})

watch(taskParamsJson, (newValue) => {
  try {
    const parsed = JSON.parse(newValue)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      jsonError.value = '任务参数必须是 JSON 对象'
      return
    }
    formData.value.task_params = parsed
    jsonError.value = ''
  } catch {
    jsonError.value = '任务参数不是有效的 JSON'
  }
})

watch(() => formData.value.task_params, (newValue) => {
  try {
    const currentJson = JSON.stringify(newValue, null, 2)
    if (JSON.stringify(JSON.parse(taskParamsJson.value)) !== JSON.stringify(newValue)) {
      taskParamsJson.value = currentJson
    }
  } catch { /* ponytail: user-typed task params may be invalid JSON; ignore */ }
}, { deep: true })

const initializeForm = () => {
  fieldErrors.value = { name: '', task_class: '', interval: '', unit: '', max_retries: '' }
  if (props.task) {
    Object.assign(formData.value, {
      name: props.task.name || '',
      description: props.task.description || '',
      task_class: props.task.task_class || '',
      interval: props.task.interval ?? 60,
      unit: props.task.unit || 'seconds',
      start_immediately: props.task.start_immediately !== false,
      max_retries: props.task.max_retries ?? 3,
      task_params: props.task.task_params || {},
      is_active: props.task.is_active !== false
    })
    taskParamsJson.value = JSON.stringify(formData.value.task_params, null, 2)
  }
}

const handleSubmit = async () => {
  const validUnits = intervalUnitOptions.map(({ value }) => value)
  fieldErrors.value = {
    name: formData.value.name.trim() ? '' : '请输入任务名称',
    task_class: formData.value.task_class ? '' : '请选择任务执行逻辑',
    interval: Number.isInteger(Number(formData.value.interval)) && Number(formData.value.interval) >= 1
      ? ''
      : '执行间隔必须是至少为 1 的整数',
    unit: validUnits.includes(formData.value.unit) ? '' : '请选择有效的时间单位',
    max_retries: Number.isInteger(Number(formData.value.max_retries)) && Number(formData.value.max_retries) >= 0
      ? ''
      : '最大重试必须是 0 或更大的整数',
  }
  if (jsonError.value || Object.values(fieldErrors.value).some(Boolean)) return

  loading.value = true
  try {
    emit('save', {
      ...formData.value,
      name: formData.value.name.trim(),
      interval: Number(formData.value.interval),
      max_retries: Number(formData.value.max_retries),
    })
  } catch (error) {
    Logger.error('TaskDialog: Submission failed', error)
  } finally {
    loading.value = false
  }
}

onMounted(initializeForm)
watch(() => props.task, initializeForm, { deep: true })
</script>

<style scoped>
.task-dialog {
  width: min(100%, 36rem);
  max-height: 90vh;
  min-height: 0;
}

.task-dialog__header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.task-dialog__schedule-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
}

.task-dialog__footer {
  flex-shrink: 0;
}
</style>

<style scoped>
.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
