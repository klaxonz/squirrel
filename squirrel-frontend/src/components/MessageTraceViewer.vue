<template>
  <div class="message-trace-viewer px-4">
    <!-- 筛选条件 - 紧凑版 -->
    <div class="bg-[#1a1a1a] rounded-lg p-3 mb-3">
      <div class="flex flex-wrap gap-2 items-center mb-2">
        <!-- 搜索框 -->
        <input
          v-model="filters.traceId"
          type="text"
          placeholder="Trace ID"
          class="flex-1 min-w-[150px] bg-[#2a2a2a] border border-gray-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
        />
        
        <input
          v-model="filters.queueName"
          type="text"
          placeholder="队列名称"
          class="w-32 bg-[#2a2a2a] border border-gray-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
        />
        
        <input
          v-model="filters.messageType"
          type="text"
          placeholder="消息类型"
          class="w-32 bg-[#2a2a2a] border border-gray-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
        />
        
        <select v-model="filters.status" class="w-24 bg-[#2a2a2a] border border-gray-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500">
          <option value="">全部</option>
          <option value="PENDING">待处理</option>
          <option value="SUCCESS">成功</option>
          <option value="FAILED">失败</option>
        </select>
        
        <div class="flex gap-2">
          <button @click="handleSearch" class="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 rounded transition-colors">
            查询
          </button>
          <button @click="handleReset" class="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded transition-colors">
            重置
          </button>
          <button @click="handleRefresh" class="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded transition-colors">
            刷新
          </button>
        </div>
      </div>

      <!-- 统计信息 - 紧凑单行显示 -->
      <div v-if="statistics" class="flex items-center gap-4 text-xs text-gray-400 pt-2 border-t border-gray-700">
        <span>总数: <span class="text-white font-medium">{{ totalMessages }}</span></span>
        <span class="text-green-400">成功: {{ statistics.status_stats.SUCCESS || 0 }}</span>
        <span class="text-red-400">失败: {{ statistics.status_stats.FAILED || 0 }}</span>
        <span class="text-yellow-400">待处理: {{ statistics.status_stats.PENDING || 0 }}</span>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="bg-[#1a1a1a] rounded-lg overflow-hidden">
      <div v-if="loading" class="text-center py-8 text-sm text-gray-400">
        加载中...
      </div>
      
      <div v-else-if="messages.length === 0" class="text-center py-8 text-sm text-gray-400">
        暂无消息记录
      </div>
      
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-[#2a2a2a] text-gray-400">
            <tr>
              <th class="px-3 py-2 text-left font-medium">ID</th>
              <th class="px-3 py-2 text-left font-medium">Trace ID</th>
              <th class="px-3 py-2 text-left font-medium">队列</th>
              <th class="px-3 py-2 text-left font-medium">类型</th>
              <th class="px-3 py-2 text-left font-medium">状态</th>
              <th class="px-3 py-2 text-left font-medium">重试</th>
              <th class="px-3 py-2 text-left font-medium">创建时间</th>
              <th class="px-3 py-2 text-left font-medium">处理时间</th>
              <th class="px-3 py-2 text-left font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="message in messages" :key="message.id">
              <tr class="border-b border-gray-800 hover:bg-[#252525] transition-colors">
                <td class="px-3 py-2">{{ message.id }}</td>
                <td class="px-3 py-2">
                  <code 
                    class="text-[10px] font-mono bg-blue-950 text-blue-400 px-1.5 py-0.5 rounded cursor-pointer hover:bg-blue-900" 
                    @click="copyToClipboard(message.trace_id)"
                    :title="'点击复制: ' + message.trace_id"
                  >
                    {{ formatTraceId(message.trace_id) }}
                  </code>
                </td>
                <td class="px-3 py-2 text-xs">{{ message.queue_name }}</td>
                <td class="px-3 py-2 text-xs">{{ message.message_type || '-' }}</td>
                <td class="px-3 py-2">
                  <span class="text-[10px] px-2 py-0.5 rounded-full" :class="getStatusClass(message.status)">
                    {{ getStatusText(message.status) }}
                  </span>
                </td>
                <td class="px-3 py-2">{{ message.retry_count }}</td>
                <td class="px-3 py-2 text-xs text-gray-400">{{ formatTime(message.created_at) }}</td>
                <td class="px-3 py-2 text-xs text-gray-400">{{ formatTime(message.processed_at) }}</td>
                <td class="px-3 py-2">
                  <button
                    @click="toggleExpand(message.id)"
                    class="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
                  >
                    {{ expandedId === message.id ? '收起' : '详情' }}
                  </button>
                </td>
              </tr>
              <tr v-if="expandedId === message.id" class="bg-[#0f0f0f] border-b border-gray-800">
                <td colspan="9" class="px-3 py-3">
                  <div class="space-y-3">
                    <div>
                      <h4 class="text-xs font-semibold text-gray-400 mb-1">消息内容</h4>
                      <pre class="text-xs bg-[#1a1a1a] text-gray-300 p-3 rounded overflow-x-auto font-mono">{{ formatJson(message.body) }}</pre>
                    </div>
                    <div v-if="message.error_msg">
                      <h4 class="text-xs font-semibold text-red-400 mb-1">错误信息</h4>
                      <pre class="text-xs bg-red-950 text-red-300 p-3 rounded overflow-x-auto font-mono">{{ message.error_msg }}</pre>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div v-if="totalCount > 0" class="flex items-center justify-between px-3 py-2 border-t border-gray-800 text-sm">
        <span class="text-gray-400 text-xs">
          第 {{ currentPage }} / {{ totalPages }} 页，共 {{ totalCount }} 条
        </span>
        <div class="flex gap-2">
          <button
            @click="handlePrevPage"
            :disabled="currentPage === 1"
            class="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            上一页
          </button>
          <button
            @click="handleNextPage"
            :disabled="currentPage >= totalPages"
            class="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from '../utils/axios'
import { formatDate } from '../utils/dateFormat'

const route = useRoute()

const messages = ref([])
const statistics = ref(null)
const loading = ref(false)
const expandedId = ref(null)

const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)

const filters = ref({
  traceId: '',
  queueName: '',
  messageType: '',
  status: '',
  startTime: '',
  endTime: ''
})

const totalPages = computed(() => {
  return Math.ceil(totalCount.value / pageSize.value)
})

const totalMessages = computed(() => {
  if (!statistics.value) return 0
  return Object.values(statistics.value.status_stats).reduce((sum, count) => sum + count, 0)
})

const fetchMessages = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      pageSize: pageSize.value
    }
    
    if (filters.value.traceId) params.trace_id = filters.value.traceId
    if (filters.value.queueName) params.queueName = filters.value.queueName
    if (filters.value.messageType) params.messageType = filters.value.messageType
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.startTime) params.startTime = new Date(filters.value.startTime).toISOString()
    if (filters.value.endTime) params.endTime = new Date(filters.value.endTime).toISOString()
    
    const response = await axios.get('/api/message/trace/query', { params })
    
    if (response.data.code === 0) {
      messages.value = response.data.data.messages
      totalCount.value = response.data.data.total
    }
  } catch (error) {
    console.error('获取消息列表失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchStatistics = async () => {
  try {
    const params = {}
    if (filters.value.startTime) params.startTime = new Date(filters.value.startTime).toISOString()
    if (filters.value.endTime) params.endTime = new Date(filters.value.endTime).toISOString()
    
    const response = await axios.get('/api/message/trace/statistics', { params })
    
    if (response.data.code === 0) {
      statistics.value = response.data.data
    }
  } catch (error) {
    console.error('获取统计信息失败:', error)
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchMessages()
  fetchStatistics()
}

const handleReset = () => {
  filters.value = {
    traceId: '',
    queueName: '',
    messageType: '',
    status: '',
    startTime: '',
    endTime: ''
  }
  currentPage.value = 1
  fetchMessages()
  fetchStatistics()
}

const handleRefresh = () => {
  fetchMessages()
  fetchStatistics()
}

const handlePrevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    fetchMessages()
  }
}

const handleNextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    fetchMessages()
  }
}

const toggleExpand = (id) => {
  expandedId.value = expandedId.value === id ? null : id
}

const getStatusClass = (status) => {
  const statusMap = {
    'PENDING': 'bg-yellow-900 text-yellow-300',
    'SUCCESS': 'bg-green-900 text-green-300',
    'FAILED': 'bg-red-900 text-red-300'
  }
  return statusMap[status] || 'bg-gray-700 text-gray-300'
}

const getStatusText = (status) => {
  const textMap = {
    'PENDING': '待处理',
    'SUCCESS': '成功',
    'FAILED': '失败'
  }
  return textMap[status] || status
}

const formatTraceId = (traceId) => {
  if (!traceId) return '-'
  return traceId.length > 16 ? `${traceId.substring(0, 8)}...${traceId.substring(traceId.length - 8)}` : traceId
}

const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  try {
    return formatDate(timeStr)
  } catch {
    return timeStr
  }
}

const formatJson = (obj) => {
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return obj
  }
}

const copyToClipboard = (text) => {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    // 可以添加一个提示，但这里保持简洁
  })
}

onMounted(() => {
  // 如果 URL 中有 traceId 参数，自动填充到筛选条件
  if (route.query.traceId) {
    filters.value.traceId = route.query.traceId
  }
  
  fetchMessages()
  fetchStatistics()
})
</script>

<style scoped>
/* 滚动条样式 */
::-webkit-scrollbar {
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #1a1a1a;
}

::-webkit-scrollbar-thumb {
  background: #4a4a4a;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #5a5a5a;
}
</style>
