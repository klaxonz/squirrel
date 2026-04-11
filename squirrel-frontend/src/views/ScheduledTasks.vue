<template>
  <div class="scheduled-page tactical-terminal min-h-full selection:bg-primary/10">
    <div class="matrix-bg"></div>
    <!-- Header Area -->
    <div class="px-8 pt-8 pb-6 border-b border-border/50 relative z-10">
      <div class="max-w-[1440px] mx-auto w-full space-y-8">
        <div class="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div class="space-y-1">
            <h1 class="text-xl font-bold tracking-tighter text-foreground uppercase font-mono">任务调度</h1>
            <p class="text-[10px] font-medium text-primary/60 uppercase tracking-[0.2em] font-mono">全局自动化执行流水线与任务负载监控</p>
          </div>
          
          <div class="flex items-center gap-4">
            <!-- Scheduler Toggle -->
            <div class="flex items-center gap-3 px-3 py-1 rounded border border-border/50 bg-secondary/40">
              <div :class="['h-1.5 w-1.5 rounded-full', schedulerStatus?.running ? 'bg-emerald-500 dark:bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.4)] animate-pulse' : 'bg-rose-500 dark:bg-rose-400 shadow-[0_0_8px_rgba(244,63,94,0.4)]']"></div>
              <span class="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 font-mono">调度器: {{ schedulerStatus?.running ? '就绪' : '暂停' }}</span>
              <div class="mx-1 h-3 w-px bg-border/50"></div>
              <Switch 
                :checked="schedulerStatus?.running" 
                @update:checked="toggleScheduler"
                :disabled="loading"
              />
            </div>

            <div class="flex items-center gap-2">
              <button 
                class="tactical-btn" 
                :disabled="loading" 
                @click="refreshData"
              >
                [ {{ loading ? '刷新中...' : '刷新数据' }} ]
              </button>

              <button 
                class="tactical-btn" 
                @click="showCreateDialog = true"
              >
                [ 新建任务 ]
              </button>
            </div>
          </div>
        </div>

        <!-- Signal Matrix (Stats) -->
        <div class="flex flex-wrap items-center gap-8 px-1">
          <div v-for="stat in signals" :key="stat.key" class="flex items-center gap-3 group">
            <div :class="[stat.bg, 'flex h-9 w-9 items-center justify-center rounded-lg transition-colors group-hover:bg-opacity-80']">
              <component :is="stat.icon" :class="[stat.color, 'h-4 w-4']" />
            </div>
            <div class="flex flex-col">
              <span class="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">{{ stat.label }}</span>
              <span class="text-sm font-semibold tabular-nums text-foreground/80">{{ stat.value }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="flex-1 overflow-hidden flex flex-col max-w-[1440px] mx-auto w-full px-8 py-6 gap-6 relative z-10">
      <!-- Search & Filters -->
      <div class="flex flex-wrap items-center gap-1.5 rounded-xl border border-border/40 bg-muted/10 p-1">
        <div class="relative flex-1 min-w-[200px] group">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/30 transition-colors group-focus-within:text-primary/60" />
          <Input 
            v-model="searchQuery" 
            @input="debouncedSearch"
            placeholder="搜索任务、描述或异常细节..." 
            class="pl-9 bg-transparent border-none h-8 text-[11px] focus-visible:ring-0"
          />
        </div>
        
        <div class="mx-0.5 h-3.5 w-px bg-border/40"></div>

        <div class="w-full sm:w-[8rem]">
          <Select v-model="statusFilter" @update:model-value="loadTasks">
            <SelectTrigger class="h-8 border-none bg-transparent text-[11px] font-semibold text-muted-foreground/80 focus:ring-0">
              <SelectValue placeholder="状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="mx-0.5 h-3.5 w-px bg-border/40"></div>

        <div class="w-full sm:w-[8rem]">
          <Select v-model="typeFilter" @update:model-value="loadTasks">
            <SelectTrigger class="h-8 border-none bg-transparent text-[11px] font-semibold text-muted-foreground/80 focus:ring-0">
              <SelectValue placeholder="类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="opt in typeOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="ml-auto flex items-center pr-1">
          <Button variant="ghost" size="xs" class="h-7 w-7 p-0 text-muted-foreground/70 dark:text-muted-foreground/80 hover:text-foreground hover:bg-muted/30" :disabled="loading" @click="loadTasks">
            <Search class="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      <!-- Table Container -->
      <div class="flex-1 overflow-hidden flex flex-col">
        <div class="flex-1 overflow-auto custom-scrollbar">
          <table class="w-full text-left border-collapse min-w-[1000px] text-[12px]">
            <thead>
              <tr class="sticky top-0 z-10 bg-secondary/80 backdrop-blur-md border-b border-border/50">
                <th class="pl-6 py-4 text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground/60">任务详情</th>
                <th class="px-4 py-4 text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground/60 w-32">当前状态</th>
                <th class="px-4 py-4 text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground/60 w-32">调度配置</th>
                <th class="px-4 py-4 text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground/60">最后一次执行</th>
                <th class="px-4 py-4 text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground/60">下一次计划</th>
                <th class="px-4 py-4 text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground/60 w-44">负载与健康</th>
                <th class="pr-6 py-4 text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground/60 text-right w-16">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border/10">
              <tr v-for="task in tasks" :key="task.id" class="group hover:bg-muted/50 transition-all cursor-pointer">
                <td class="pl-6 py-4 align-middle">
                  <div class="flex flex-col gap-0.5">
                    <div class="flex items-center gap-2">
                      <span class="font-bold text-foreground/80 tracking-tight">{{ task.name }}</span>
                      <span class="px-1.5 py-0.5 rounded bg-muted/40 text-[9px] font-bold uppercase tracking-widest text-muted-foreground/40">{{ getTypeText(task.task_type) }}</span>
                    </div>
                    <p class="text-[10px] font-medium text-muted-foreground/30 line-clamp-1 max-w-[280px]">{{ task.description || '无详细描述' }}</p>
                    <div v-if="task.last_error" class="mt-1 flex items-center gap-1.5 text-[9px] text-rose-500/50 dark:text-rose-400/50 font-semibold uppercase tracking-tight" :title="task.last_error">
                      <AlertCircle class="h-2.5 w-2.5 shrink-0" />
                      <span class="truncate">{{ task.last_error }}</span>
                    </div>
                  </div>
                </td>

                <td class="px-4 py-4 align-middle">
                  <div class="flex items-center gap-2">
                    <div :class="['h-2 w-2 rounded-full', getStatusDotColor(task.status)]"></div>
                    <span class="text-[11px] font-bold text-foreground/70 tracking-tight uppercase">{{ getStatusText(task.status) }}</span>
                  </div>
                </td>

                <td class="px-4 py-4 align-middle">
                  <div class="flex flex-col">
                    <span class="text-xs font-bold tabular-nums text-foreground/60 leading-none">{{ task.interval }}</span>
                    <span class="text-[9px] font-bold text-muted-foreground/20 uppercase tracking-widest mt-1">{{ getUnitLabel(task.unit) }}</span>
                  </div>
                </td>

                <td class="px-4 py-4 align-middle">
                  <span class="text-[11px] font-semibold text-foreground/50 tabular-nums">{{ formatDateTime(task.last_run_at) || '-' }}</span>
                </td>

                <td class="px-4 py-4 align-middle">
                  <span class="text-[11px] font-semibold tabular-nums text-primary/50">{{ formatDateTime(task.next_run_at) || '-' }}</span>
                </td>

                <td class="px-4 py-4 align-middle">
                  <div class="flex flex-col gap-1.5">
                    <div class="flex items-center justify-between text-[9px] font-bold tracking-widest">
                      <span class="text-muted-foreground/20 uppercase">{{ calculateSuccessRate(task) }}%</span>
                      <span class="text-foreground/30 tabular-nums">{{ task.success_count }} / {{ task.run_count }}</span>
                    </div>
                    <div class="h-0.5 w-full bg-muted/10 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-primary/30 dark:bg-primary/40 transition-all duration-700 ease-out"
                        :style="{ width: `${calculateSuccessRate(task)}%` }"
                      ></div>
                    </div>
                  </div>
                </td>

                <td class="pr-6 py-4 text-right align-middle">
                  <DropdownMenu>
                    <DropdownMenuTrigger as-child>
                      <Button variant="ghost" size="sm" class="h-8 w-8 p-0 text-muted-foreground/30 dark:text-muted-foreground/40 hover:text-foreground hover:bg-muted/50 rounded-lg transition-all">
                        <MoreVertical class="h-3.5 w-3.5" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" class="w-40 border-border/40 bg-card/95 backdrop-blur-xl">
                      <DropdownMenuLabel class="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/50 dark:text-muted-foreground/60 px-3 py-2">配置选项</DropdownMenuLabel>
                      <DropdownMenuItem @click="executeTaskNow(task.id)" :disabled="loading" class="gap-2 px-3 py-1.5 cursor-pointer">
                        <Play class="h-3 w-3 text-emerald-500/60 dark:text-emerald-400/60" />
                        <span class="text-[11px] font-bold uppercase tracking-tight">立即触发</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem @click="editTask(task)" class="gap-2 px-3 py-1.5 cursor-pointer">
                        <Pencil class="h-3 w-3" />
                        <span class="text-[11px] font-bold uppercase tracking-tight">编辑配置</span>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator class="bg-border/20" />
                      <DropdownMenuItem v-if="task.is_active" @click="disableTask(task.id)" class="gap-2 px-3 py-1.5 cursor-pointer">
                        <Pause class="h-3 w-3 text-amber-500/60 dark:text-amber-400/60" />
                        <span class="text-[11px] font-bold uppercase tracking-tight">禁用调度</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem v-else @click="enableTask(task.id)" class="gap-2 px-3 py-1.5 cursor-pointer">
                        <Zap class="h-3 w-3 text-primary/60 dark:text-primary/50" />
                        <span class="text-[11px] font-bold uppercase tracking-tight">恢复调度</span>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator class="bg-border/20" />
                      <DropdownMenuItem
                        @click="deleteTask(task.id)"
                        :disabled="task.task_type === 'system'"
                        class="gap-2 px-3 py-1.5 text-rose-500/70 dark:text-rose-400/70 focus:text-rose-600 dark:focus:text-rose-300 focus:bg-rose-500/5 dark:focus:bg-rose-400/5 cursor-pointer"
                      >
                        <Trash2 class="h-3 w-3" />
                        <span class="text-[11px] font-bold uppercase tracking-tight">移除任务</span>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Footer / Pagination -->
        <div class="px-8 py-6 border-t border-border/10 flex items-center justify-between">
          <p class="text-[11px] font-bold uppercase tracking-[0.1em] text-muted-foreground/20">
            共 {{ statistics.total_tasks }} 个任务实例
          </p>
          <div class="flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="xs"
              class="h-8 px-4 text-[11px] font-bold rounded-lg border border-border/40 text-muted-foreground/60 dark:text-muted-foreground/70 hover:text-foreground hover:bg-muted/30 disabled:opacity-40"
              :disabled="currentPage <= 1 || loading"
              @click="goToPage(currentPage - 1)"
            >
              上一页
            </Button>
            <span class="text-[11px] font-bold text-muted-foreground/30 dark:text-muted-foreground/40 mx-4 uppercase tracking-[0.1em]">
              第 {{ currentPage }} / {{ totalPages }} 页
            </span>
            <Button
              variant="ghost"
              size="xs"
              class="h-8 px-4 text-[11px] font-bold rounded-lg border border-border/40 text-muted-foreground/60 dark:text-muted-foreground/70 hover:text-foreground hover:bg-muted/30 disabled:opacity-40"
              :disabled="currentPage >= totalPages || loading"
              @click="goToPage(currentPage + 1)"
            >
              下一页
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <TaskDialog
      v-if="showCreateDialog"
      :task-classes="taskClasses"
      @close="showCreateDialog = false"
      @save="handleCreateTask"
    />

    <TaskDialog
      v-if="editingTask"
      :task="editingTask"
      :task-classes="taskClasses"
      @close="editingTask = null"
      @save="handleUpdateTask"
    />
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { 
  Activity, RefreshCw, Plus, Search, Clock, Zap, AlertCircle, 
  CheckCircle2, Play, Pause, Pencil, Trash2, MoreVertical, 
  ChevronLeft, ChevronRight, Layers, PlayCircle, Timer
} from 'lucide-vue-next'
import TaskDialog from '@/components/dialogs/TaskDialog.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { debounce } from '../utils/debounce'
import { Logger } from '@/utils/logger'
import {
  createTask as apiCreateTask,
  deleteTask as apiDeleteTask,
  disableScheduler as apiDisableScheduler,
  disableTask as apiDisableTask,
  enableScheduler as apiEnableScheduler,
  enableTask as apiEnableTask,
  executeTaskNow as apiExecuteTaskNow,
  getAvailableTaskClasses,
  getSchedulerStatus,
  getScheduledTasks,
  getTaskStatistics,
  updateTask as apiUpdateTask,
} from '@/api'

// Data
const schedulerStatus = ref(null)
const statistics = ref({
  total_tasks: 0,
  active_tasks: 0,
  running_tasks: 0,
  error_tasks: 0,
  today_executions: 0
})
const tasks = ref([])
const taskClasses = ref({})
const loading = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)
const searchQuery = ref('')
const statusFilter = ref('all')
const typeFilter = ref('all')
const showCreateDialog = ref(false)
const editingTask = ref(null)

// Signal Matrix Configuration
const signals = computed(() => [
  {
    key: 'total',
    label: '任务总数',
    value: statistics.value.total_tasks,
    icon: Layers,
    bg: 'bg-slate-500/10 dark:bg-slate-400/10',
    color: 'text-slate-500 dark:text-slate-600'
  },
  {
    key: 'active',
    label: '活跃实例',
    value: statistics.value.active_tasks,
    icon: Zap,
    bg: 'bg-emerald-500/10 dark:bg-emerald-400/10',
    color: 'text-emerald-600 dark:text-emerald-500'
  },
  {
    key: 'running',
    label: '正在运行',
    value: statistics.value.running_tasks,
    icon: Timer,
    bg: 'bg-blue-500/10 dark:bg-blue-400/10',
    color: 'text-blue-600 dark:text-blue-500'
  },
  {
    key: 'error',
    label: '异常告警',
    value: statistics.value.error_tasks,
    icon: AlertCircle,
    bg: 'bg-rose-500/10 dark:bg-rose-400/10',
    color: 'text-rose-600 dark:text-rose-500'
  },
  {
    key: 'today',
    label: '今日完成',
    value: statistics.value.today_executions,
    icon: CheckCircle2,
    bg: 'bg-emerald-500/10 dark:bg-emerald-400/10',
    color: 'text-emerald-600 dark:text-emerald-500'
  },
])

const statusOptions = [
  { value: 'all', label: '全部状态' },
  { value: 'enabled', label: '就绪' },
  { value: 'disabled', label: '已暂停' },
  { value: 'running', label: '运行中' },
  { value: 'error', label: '异常' }
]

const typeOptions = [
  { value: 'all', label: '全部类型' },
  { value: 'system', label: '核心' },
  { value: 'user', label: '用户' },
  { value: 'plugin', label: '插件' }
]

// Methods
const debouncedSearch = debounce(() => {
  currentPage.value = 1
  loadTasks()
}, 300)

const loadData = async () => {
  loading.value = true
  try {
    const [statusResult, statsResult, classesResult] = await Promise.all([
      getSchedulerStatus(),
      getTaskStatistics(),
      getAvailableTaskClasses()
    ])

    if (!statusResult.error) schedulerStatus.value = statusResult.data
    if (!statsResult.error) statistics.value = statsResult.data
    if (!classesResult.error) taskClasses.value = classesResult.data
    
    await loadTasks()
  } catch (error) {
    Logger.error('ScheduledTasks: Initial load failed', error)
  } finally {
    loading.value = false
  }
}

const loadTasks = async () => {
  try {
    const result = await getScheduledTasks({
      page: currentPage.value,
      page_size: 15,
      search: searchQuery.value || undefined,
      status: statusFilter.value === 'all' ? undefined : statusFilter.value,
      task_type: typeFilter.value === 'all' ? undefined : typeFilter.value
    })

    if (!result.error && result.data) {
      tasks.value = result.data.data
      totalPages.value = Math.ceil(result.data.total / 15)
    }
  } catch (error) {
    Logger.error('ScheduledTasks: Task query failed', error)
  }
}

const refreshData = async () => {
  await loadData()
}

const toggleScheduler = async (val) => {
  const api = val ? apiEnableScheduler : apiDisableScheduler
  const result = await api()
  if (!result.error) {
    schedulerStatus.value.running = val
  }
}

const executeTaskNow = async (taskId) => {
  loading.value = true
  const result = await apiExecuteTaskNow(taskId)
  if (!result.error) {
    setTimeout(() => refreshData(), 600)
  } else {
    loading.value = false
  }
}

const editTask = (task) => {
  editingTask.value = task
}

const handleCreateTask = async (taskData) => {
  const result = await apiCreateTask(taskData)
  if (!result.error) {
    showCreateDialog.value = false
    await refreshData()
  }
}

const handleUpdateTask = async (taskData) => {
  const result = await apiUpdateTask(editingTask.value.id, taskData)
  if (!result.error) {
    editingTask.value = null
    await refreshData()
  }
}

const deleteTask = async (id) => {
  if (confirm('确定要移除此定时任务吗？')) {
    const result = await apiDeleteTask(id)
    if (!result.error) await refreshData()
  }
}

const enableTask = async (id) => {
  const result = await apiEnableTask(id)
  if (!result.error) await refreshData()
}

const disableTask = async (id) => {
  const result = await apiDisableTask(id)
  if (!result.error) await refreshData()
}

const goToPage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadTasks()
  }
}

const calculateSuccessRate = (task) => {
  if (!task.run_count) return 0
  return Math.round((task.success_count / task.run_count) * 100)
}

const getUnitLabel = (unit) => {
  return { seconds: '秒/次', minutes: '分/次', hours: '时/次', days: '天/次' }[unit] || unit
}

const getStatusDotColor = (status) => {
  switch (status) {
    case 'enabled': return 'bg-emerald-400 dark:bg-emerald-500 shadow-[0_0_8px_rgba(52,211,153,0.4)]'
    case 'running': return 'bg-primary shadow-[0_0_8px_rgba(59,130,246,0.4)] animate-pulse'
    case 'disabled': return 'bg-slate-500/20 dark:bg-slate-400/20 shadow-none'
    case 'error': return 'bg-rose-500 dark:bg-rose-400 shadow-[0_0_8px_rgba(244,63,94,0.4)]'
    default: return 'bg-slate-500/10 dark:bg-slate-400/10'
  }
}

const getStatusText = (status) => {
  return { enabled: '就绪', disabled: '暂停', running: '运行中', error: '异常' }[status] || status
}

const getTypeText = (type) => {
  return { system: '核心', user: '用户', plugin: '插件' }[type] || type
}

const formatDateTime = (val) => {
  if (!val) return null
  const date = new Date(val)
  return date.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}

onMounted(loadData)
</script>

<style scoped>
.tactical-terminal {
  background-color: hsl(var(--background));
  position: relative;
  overflow: hidden;
}

.matrix-bg {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(hsl(var(--foreground) / 0.03) 1px, transparent 1px);
  background-size: 20px 20px;
  pointer-events: none;
}

.tactical-btn {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  color: hsl(var(--muted-foreground) / 0.6);
  padding: 0.5rem 0.75rem;
  transition: all 0.2s ease;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.tactical-btn:hover:not(:disabled) {
  color: hsl(var(--primary));
  text-shadow: 0 0 10px hsl(var(--primary) / 0.5);
}

.tactical-btn:disabled {
  opacity: 0.2;
  cursor: not-allowed;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: hsl(var(--border) / 0.1);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--border) / 0.3);
}

/* Typography refinement */
.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
