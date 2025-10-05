# 订阅导入 - 前端集成指南

## API 接口

### 1. 获取支持的站点列表

```http
GET /api/subscription/import/sites
Authorization: Bearer {token}
```

**响应示例：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "sites": ["bilibili", "youtube", "pornhub", "javdb"]
  }
}
```

---

### 2. 预览订阅列表

```http
GET /api/subscription/import/{site}/preview
Authorization: Bearer {token}
```

**响应示例：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "site": "bilibili",
    "total": 120,
    "subscriptions": [
      {
        "url": "https://space.bilibili.com/123456",
        "name": "某UP主",
        "avatar": "https://..."
      },
      ...
    ]
  }
}
```

**说明：**
- 预览最多返回前 50 个订阅
- `total` 表示实际找到的订阅总数
- 预览操作不会实际导入到数据库

---

### 3. 执行导入

```http
POST /api/subscription/import/{site}
Authorization: Bearer {token}
```

**响应示例：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "site": "bilibili",
    "total": 120,
    "success": 115,
    "failed": 2,
    "skipped": 3,
    "errors": ["错误信息1", "错误信息2"]
  }
}
```

---

## 前端界面设计

### 界面流程

```
订阅列表页面
    ↓
[导入订阅] 按钮
    ↓
打开导入对话框
    ↓
选择站点 (Bilibili / YouTube / Pornhub / JavDB)
    ↓
[预览订阅] 按钮
    ↓
显示订阅预览列表 (最多50个)
    ↓
[确认导入] 按钮
    ↓
显示导入进度和结果
```

---

## Vue3 代码示例

### 1. 导入对话框组件

```vue
<template>
  <el-dialog
    v-model="dialogVisible"
    title="导入订阅"
    width="800px"
    :close-on-click-modal="false"
  >
    <!-- 步骤1: 选择站点 -->
    <div v-if="step === 1" class="site-selection">
      <h3>选择要导入的站点</h3>
      <div class="site-grid">
        <div
          v-for="site in supportedSites"
          :key="site"
          :class="['site-card', { active: selectedSite === site }]"
          @click="selectedSite = site"
        >
          <img :src="getSiteIcon(site)" :alt="site" />
          <span>{{ getSiteName(site) }}</span>
        </div>
      </div>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="previewSubscriptions" :disabled="!selectedSite">
          预览订阅
        </el-button>
      </div>
    </div>

    <!-- 步骤2: 预览订阅 -->
    <div v-else-if="step === 2" class="preview-section">
      <div class="preview-header">
        <h3>预览订阅列表</h3>
        <p>找到 {{ previewData.total }} 个订阅，显示前 {{ previewData.subscriptions.length }} 个</p>
      </div>
      
      <el-scrollbar height="400px">
        <div class="subscription-list">
          <div
            v-for="(sub, index) in previewData.subscriptions"
            :key="index"
            class="subscription-item"
          >
            <img :src="sub.avatar || defaultAvatar" class="avatar" />
            <div class="info">
              <div class="name">{{ sub.name }}</div>
              <div class="url">{{ sub.url }}</div>
            </div>
          </div>
        </div>
      </el-scrollbar>

      <div class="dialog-footer">
        <el-button @click="step = 1">返回</el-button>
        <el-button type="primary" @click="confirmImport" :loading="importing">
          确认导入 ({{ previewData.total }} 个)
        </el-button>
      </div>
    </div>

    <!-- 步骤3: 导入结果 -->
    <div v-else-if="step === 3" class="result-section">
      <el-result
        :icon="importResult.success > 0 ? 'success' : 'error'"
        :title="importResult.success > 0 ? '导入完成' : '导入失败'"
      >
        <template #sub-title>
          <div class="result-stats">
            <p>总数: {{ importResult.total }}</p>
            <p style="color: #67c23a">成功: {{ importResult.success }}</p>
            <p style="color: #f56c6c" v-if="importResult.failed > 0">失败: {{ importResult.failed }}</p>
            <p style="color: #e6a23c" v-if="importResult.skipped > 0">跳过: {{ importResult.skipped }}</p>
          </div>
          <div v-if="importResult.errors && importResult.errors.length > 0" class="error-list">
            <p>错误信息：</p>
            <ul>
              <li v-for="(error, index) in importResult.errors" :key="index">{{ error }}</li>
            </ul>
          </div>
        </template>
      </el-result>

      <div class="dialog-footer">
        <el-button type="primary" @click="closeDialog">完成</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const dialogVisible = ref(false)
const step = ref(1) // 1: 选择站点, 2: 预览, 3: 结果
const supportedSites = ref([])
const selectedSite = ref('')
const previewData = ref({ total: 0, subscriptions: [] })
const importResult = ref({})
const importing = ref(false)
const defaultAvatar = '/default-avatar.png'

// 站点配置
const siteConfig = {
  bilibili: { name: 'Bilibili', icon: '/icons/bilibili.svg' },
  youtube: { name: 'YouTube', icon: '/icons/youtube.svg' },
  pornhub: { name: 'Pornhub', icon: '/icons/pornhub.svg' },
  javdb: { name: 'JavDB', icon: '/icons/javdb.svg' }
}

const getSiteName = (site) => siteConfig[site]?.name || site
const getSiteIcon = (site) => siteConfig[site]?.icon || '/icons/default.svg'

// 打开对话框
const open = async () => {
  dialogVisible.value = true
  step.value = 1
  selectedSite.value = ''
  await loadSupportedSites()
}

// 加载支持的站点
const loadSupportedSites = async () => {
  try {
    const res = await api.get('/api/subscription/import/sites')
    if (res.code === 0) {
      supportedSites.value = res.data.sites
    }
  } catch (error) {
    ElMessage.error('加载站点列表失败')
  }
}

// 预览订阅
const previewSubscriptions = async () => {
  if (!selectedSite.value) return
  
  try {
    ElMessage.info('正在获取订阅列表...')
    const res = await api.get(`/api/subscription/import/${selectedSite.value}/preview`)
    if (res.code === 0) {
      previewData.value = res.data
      step.value = 2
    } else {
      ElMessage.error(res.msg || '预览失败')
    }
  } catch (error) {
    ElMessage.error('预览失败: ' + error.message)
  }
}

// 确认导入
const confirmImport = async () => {
  if (!selectedSite.value) return
  
  importing.value = true
  try {
    ElMessage.info('正在导入订阅...')
    const res = await api.post(`/api/subscription/import/${selectedSite.value}`)
    if (res.code === 0) {
      importResult.value = res.data
      step.value = 3
      ElMessage.success('导入完成！')
    } else {
      ElMessage.error(res.msg || '导入失败')
    }
  } catch (error) {
    ElMessage.error('导入失败: ' + error.message)
  } finally {
    importing.value = false
  }
}

// 关闭对话框
const closeDialog = () => {
  dialogVisible.value = false
  // 刷新订阅列表
  emit('imported')
}

defineExpose({ open })
</script>

<style scoped>
.site-selection {
  padding: 20px;
}

.site-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin: 20px 0;
}

.site-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.site-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.2);
}

.site-card.active {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.site-card img {
  width: 48px;
  height: 48px;
  margin-bottom: 10px;
}

.preview-section {
  padding: 20px;
}

.preview-header {
  margin-bottom: 20px;
}

.subscription-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.subscription-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  transition: all 0.2s;
}

.subscription-item:hover {
  background-color: #f5f7fa;
}

.subscription-item .avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  margin-right: 12px;
  object-fit: cover;
}

.subscription-item .info {
  flex: 1;
}

.subscription-item .name {
  font-weight: 500;
  margin-bottom: 4px;
}

.subscription-item .url {
  font-size: 12px;
  color: #909399;
}

.result-section {
  padding: 20px;
}

.result-stats {
  font-size: 16px;
  margin-top: 20px;
}

.result-stats p {
  margin: 8px 0;
}

.error-list {
  margin-top: 20px;
  text-align: left;
  color: #f56c6c;
}

.error-list ul {
  list-style: none;
  padding: 0;
}

.error-list li {
  margin: 4px 0;
  font-size: 14px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}
</style>
```

### 2. 在订阅列表页面使用

```vue
<template>
  <div class="subscription-list-page">
    <div class="header">
      <h1>我的订阅</h1>
      <el-button type="primary" @click="openImportDialog">
        <el-icon><Upload /></el-icon>
        导入订阅
      </el-button>
    </div>

    <!-- 订阅列表 -->
    <div class="subscriptions">
      <!-- ... -->
    </div>

    <!-- 导入对话框 -->
    <ImportSubscriptionDialog ref="importDialogRef" @imported="loadSubscriptions" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import ImportSubscriptionDialog from '@/components/ImportSubscriptionDialog.vue'

const importDialogRef = ref()

const openImportDialog = () => {
  importDialogRef.value.open()
}

const loadSubscriptions = () => {
  // 刷新订阅列表
}
</script>
```

---

## 移动端适配

对于移动端，建议使用底部抽屉（Bottom Sheet）代替对话框：

```vue
<van-action-sheet v-model:show="showSheet" title="导入订阅">
  <!-- 站点选择 -->
  <van-grid :column-num="2">
    <van-grid-item
      v-for="site in supportedSites"
      :key="site"
      :text="getSiteName(site)"
      @click="selectSite(site)"
    >
      <template #icon>
        <img :src="getSiteIcon(site)" style="width: 40px; height: 40px" />
      </template>
    </van-grid-item>
  </van-grid>
</van-action-sheet>
```

---

## 交互体验优化建议

1. **加载状态**
   - 预览时显示骨架屏
   - 导入时显示进度条

2. **错误处理**
   - 清晰的错误提示
   - 支持重试机制

3. **成功反馈**
   - 动画效果
   - 自动跳转到新导入的订阅

4. **批量操作**
   - 支持选择性导入（取消勾选不需要的）
   - 支持同时导入多个站点

5. **缓存优化**
   - 预览结果临时缓存
   - 避免重复请求

---

## 使用截图参考

```
┌─────────────────────────────────┐
│  导入订阅                       │
├─────────────────────────────────┤
│                                 │
│  选择要导入的站点：             │
│                                 │
│  ┌────┐  ┌────┐  ┌────┐  ┌────┐│
│  │ B  │  │ Y  │  │ P  │  │ J  ││
│  │站  │  │油  │  │网  │  │影  ││
│  └────┘  └────┘  └────┘  └────┘│
│                                 │
│          [取消]  [预览订阅]     │
└─────────────────────────────────┘

↓

┌─────────────────────────────────┐
│  预览订阅列表                   │
├─────────────────────────────────┤
│  找到 120 个订阅，显示前 50 个   │
│                                 │
│  ┌───────────────────────────┐ │
│  │ 👤 UP主名称              │ │
│  │    space.bilibili.com/... │ │
│  ├───────────────────────────┤ │
│  │ 👤 UP主名称2             │ │
│  │    space.bilibili.com/... │ │
│  └───────────────────────────┘ │
│                                 │
│      [返回]  [确认导入(120)]    │
└─────────────────────────────────┘

↓

┌─────────────────────────────────┐
│  ✓ 导入完成                     │
├─────────────────────────────────┤
│                                 │
│  总数: 120                      │
│  成功: 115 ✓                   │
│  失败: 2 ✗                     │
│  跳过: 3 (已存在)              │
│                                 │
│            [完成]               │
└─────────────────────────────────┘
```
