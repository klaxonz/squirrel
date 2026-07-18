<template>
  <Dialog :open="true" @update:open="!$event && $emit('close')">
    <DialogContent
      class="max-h-[90vh] min-h-0 w-full max-w-xl overflow-hidden rounded-lg p-0"
      content-class="flex min-h-0 flex-1 flex-col overflow-hidden"
    >
      <DialogHeader class="app-divider-bottom flex shrink-0 flex-row items-center justify-between space-y-0 p-5 text-left">
        <div class="min-w-0">
          <DialogTitle class="text-base font-semibold text-foreground">
            {{ isEditing ? '编辑任务' : '新建任务' }}
          </DialogTitle>
        </div>
        <Button text severity="secondary" size="sm" icon-only aria-label="关闭任务对话框" @click="$emit('close')">
          <AppIcon name="close" class="h-4 w-4" />
        </Button>
      </DialogHeader>

      <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar">
        <form class="space-y-6 p-5" @submit.prevent="handleSubmit">
          <section class="space-y-4">
            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground" for="task-dialog-name">任务名称</label>
              <Input fluid
                id="task-dialog-name"
                v-model="formData.name"
                required
                placeholder="输入任务名称"
              />
            </div>

            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground">逻辑类</label>
              <PrimeSelect
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
              </PrimeSelect>
            </div>

            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground" for="task-dialog-desc">描述</label>
              <Textarea fluid
                id="task-dialog-desc"
                v-model="formData.description"
                placeholder="简要说明任务用途"
                class="min-h-20"
              />
            </div>
          </section>

          <section class="app-divider-top space-y-4 pt-5">
            <div class="grid gap-4 md:grid-cols-3">
            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground" for="task-dialog-interval">执行间隔</label>
              <Input fluid
                id="task-dialog-interval"
                v-model.number="formData.interval"
                type="number"
                min="1"
                class="tabular-nums"
              />
            </div>
            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground">单位</label>
              <PrimeSelect
                v-model="formData.unit"
                :options="intervalUnitOptions"
                option-label="label"
                option-value="value"
                fluid
              />
            </div>
            <div class="space-y-2">
              <label class="text-xs font-medium text-muted-foreground" for="task-dialog-retries">最大重试</label>
              <Input fluid
                id="task-dialog-retries"
                v-model.number="formData.max_retries"
                type="number"
                min="0"
                class="tabular-nums"
              />
            </div>
            </div>

            <div class="grid gap-2">
              <label class="app-surface app-surface--subtle flex h-10 items-center justify-between px-3">
                <span class="text-sm font-medium text-foreground">启用调度</span>
                <Switch v-model="formData.is_active" />
              </label>
              <label class="app-surface app-surface--subtle flex h-10 items-center justify-between px-3">
                <span class="text-sm font-medium text-foreground">立即执行一次</span>
                <Switch v-model="formData.start_immediately" />
              </label>
            </div>
          </section>

          <section class="app-divider-top space-y-2 pt-5">
            <label class="text-xs font-medium text-muted-foreground" for="task-dialog-params">任务参数</label>
            <div class="relative">
              <Textarea fluid
                id="task-dialog-params"
                v-model="taskParamsJson"
                rows="5"
                class="font-mono bg-muted/30 px-4 py-3 text-xs text-foreground"
                placeholder='{ "名称": "内容" }'
              />
              <div v-if="jsonError" class="absolute bottom-3 right-3 inline-flex items-center gap-1.5 rounded-md border border-destructive/20 bg-background px-2 py-1 text-xs font-medium text-destructive">
                <AppIcon name="alert" class="h-3 w-3" />
                格式错误
              </div>
            </div>
          </section>
        </form>
      </div>

      <DialogFooter class="app-divider-top flex shrink-0 items-center justify-end gap-2 bg-muted/30 p-4 sm:justify-end">
        <Button severity="secondary" outlined @click="$emit('close')">取消</Button>
        <Button severity="contrast" :loading="loading" :disabled="!!jsonError" @click="handleSubmit">
          {{ isEditing ? '保存' : '创建' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import { Switch } from '@/shared/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'
import PrimeSelect from 'primevue/select'
import { Logger } from '@/shared/lib/logger'

const props = defineProps({
  task: { type: Object, default: null },
  taskClasses: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['close', 'save'])

const isEditing = computed(() => !!props.task)
const loading = ref(false)
const jsonError = ref('')

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
    if (typeof parsed !== 'object' || parsed === null) throw new Error()
    formData.value.task_params = parsed
    jsonError.value = ''
  } catch {
    jsonError.value = 'ERR_JSON_FORMAT'
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
  if (props.task) {
    Object.assign(formData.value, {
      name: props.task.name || '',
      description: props.task.description || '',
      task_class: props.task.task_class || '',
      interval: props.task.interval || 60,
      unit: props.task.unit || 'seconds',
      start_immediately: props.task.start_immediately !== false,
      max_retries: props.task.max_retries || 3,
      task_params: props.task.task_params || {},
      is_active: props.task.is_active !== false
    })
    taskParamsJson.value = JSON.stringify(formData.value.task_params, null, 2)
  }
}

const handleSubmit = async () => {
  if (jsonError.value) return
  loading.value = true
  try {
    emit('save', { ...formData.value })
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
.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
