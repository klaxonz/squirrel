<template>
  <div class="ui-gallery">
    <header class="ui-gallery__header">
      <h1>UI 组件画廊</h1>
      <p>
        shared/ui 全量预览 — 仅 dev 构建注册（<code>/dev/ui</code>）。
        新组件先在这里验证形态，再进入业务页面。体系约定见
        <code>docs/ui-system-consolidation-plan.md</code> 与 ADR-0004。
      </p>
    </header>

    <section class="ui-gallery__section">
      <h2>Button</h2>
      <div class="ui-gallery__row">
        <Button>default</Button>
        <Button variant="secondary">secondary</Button>
        <Button variant="outline">outline</Button>
        <Button variant="ghost">ghost</Button>
        <Button variant="destructive">destructive</Button>
        <Button variant="contrast">contrast</Button>
      </div>
      <div class="ui-gallery__row">
        <Button size="sm">sm</Button>
        <Button>default</Button>
        <Button size="lg">lg</Button>
        <Button :loading="true">loading</Button>
        <Button disabled>disabled</Button>
        <Button rounded>rounded</Button>
      </div>
    </section>

    <section class="ui-gallery__section">
      <h2>IconButton</h2>
      <div class="ui-gallery__row">
        <IconButton label="设置">
          <AppIcon name="settingsPanel" class="h-4 w-4" />
        </IconButton>
        <IconButton label="删除" variant="destructive">
          <AppIcon name="trash" class="h-4 w-4" />
        </IconButton>
        <IconButton label="刷新" variant="outline" size="sm">
          <AppIcon name="refresh" class="h-4 w-4" />
        </IconButton>
      </div>
    </section>

    <section class="ui-gallery__section">
      <h2>Form controls</h2>
      <div class="ui-gallery__row">
        <Input v-model="inputValue" placeholder="Input" />
        <Input v-model="inputValue" size="lg" placeholder="Input lg" />
        <Textarea v-model="textareaValue" placeholder="Textarea" />
      </div>
      <div class="ui-gallery__row">
        <label class="ui-gallery__inline">
          <Checkbox v-model="checkboxValue" /> Checkbox
        </label>
        <label class="ui-gallery__inline">
          <Switch v-model="switchValue" /> Switch
        </label>
        <Select
          v-model="selectValue"
          :options="[
            { label: '选项 A', value: 'a' },
            { label: '选项 B', value: 'b' },
          ]"
          placeholder="Select"
        />
      </div>
    </section>

    <section class="ui-gallery__section">
      <h2>Badge / Alert</h2>
      <div class="ui-gallery__row">
        <Badge>default</Badge>
        <Badge variant="secondary">secondary</Badge>
        <Badge variant="success">success</Badge>
        <Badge variant="warning">warning</Badge>
        <Badge variant="error">error</Badge>
        <Badge variant="muted">muted</Badge>
        <Badge variant="outline">outline</Badge>
      </div>
      <div class="ui-gallery__stack">
        <Alert>default alert</Alert>
        <Alert variant="info">info alert</Alert>
        <Alert variant="success">success alert</Alert>
        <Alert variant="warning">warning alert</Alert>
        <Alert variant="destructive">destructive alert</Alert>
      </div>
    </section>

    <section class="ui-gallery__section">
      <h2>Tabs</h2>
      <TabsRoot default-value="tab-a">
        <TabsList>
          <TabsTrigger value="tab-a">标签 A</TabsTrigger>
          <TabsTrigger value="tab-b">标签 B</TabsTrigger>
          <TabsTrigger value="tab-c" disabled>禁用</TabsTrigger>
        </TabsList>
        <TabsContent value="tab-a" class="ui-gallery__panel">内容 A</TabsContent>
        <TabsContent value="tab-b" class="ui-gallery__panel">内容 B</TabsContent>
      </TabsRoot>
    </section>

    <section class="ui-gallery__section">
      <h2>Overlays</h2>
      <div class="ui-gallery__row">
        <DialogRoot v-model:open="dialogOpen">
          <DialogTrigger as-child>
            <Button variant="secondary">Dialog</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>对话框标题</DialogTitle>
              <DialogDescription>基于 reka-ui DialogRoot 的模态对话框。</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <DialogClose as-child>
                <Button variant="secondary">关闭</Button>
              </DialogClose>
            </DialogFooter>
          </DialogContent>
        </DialogRoot>

        <PopoverRoot v-model:open="popoverOpen">
          <PopoverTrigger as-child>
            <Button variant="secondary">Popover</Button>
          </PopoverTrigger>
          <PopoverContent>
            <p class="ui-gallery__panel">PopoverContent（sq-popover）</p>
          </PopoverContent>
        </PopoverRoot>

        <DropdownMenuRoot>
          <DropdownMenuTrigger as-child>
            <Button variant="secondary">DropdownMenu</Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem @select.prevent>
              <AppIcon name="bolt" class="h-4 w-4" />
              操作项
            </DropdownMenuItem>
            <DropdownMenuItem danger @select.prevent>
              <AppIcon name="trash" class="h-4 w-4" />
              危险操作
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled>禁用项</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenuRoot>

        <TooltipProvider :delay-duration="200">
          <TooltipRoot>
            <TooltipTrigger as-child>
              <Button variant="ghost">Tooltip</Button>
            </TooltipTrigger>
            <TooltipContent>倒置墨色提示条</TooltipContent>
          </TooltipRoot>
        </TooltipProvider>
      </div>
    </section>

    <section class="ui-gallery__section">
      <h2>Loading / Skeleton</h2>
      <div class="ui-gallery__row">
        <Spinner size="sm" />
        <Spinner />
        <Spinner size="lg" muted />
        <BounceDots />
      </div>
      <div class="ui-gallery__stack">
        <Skeleton width="18rem" height="1rem" shimmer />
        <SkeletonText :lines="3" />
      </div>
    </section>

    <section class="ui-gallery__section">
      <h2>Type scale</h2>
      <p class="ui-gallery__note">
        正文走平台系统字体，标题与数字走展示字体；11px eyebrow 用于区块眉题。
        切换浅色/暗色后逐项对照，两套主题都应完整可读。
      </p>
      <div class="ui-gallery__stack">
        <span class="app-eyebrow">Eyebrow · 区块标签</span>
        <p class="ui-gallery__type ui-gallery__type--3xl">页面标题 24 / 650</p>
        <p class="ui-gallery__type ui-gallery__type--2xl">区块标题 22 / 650</p>
        <p class="ui-gallery__type ui-gallery__type--lg">列表标题 16 / 600</p>
        <p class="ui-gallery__type ui-gallery__type--base">正文 14 / 400 · 中文与 English 混排的阅读密度</p>
        <p class="ui-gallery__type ui-gallery__type--meta">元信息 12 / 500 · 频道 · 2 小时前</p>
        <p class="ui-gallery__type ui-gallery__type--numeric">128,904 · 04:32 · 2026-10-23</p>
      </div>
    </section>

    <section class="ui-gallery__section">
      <h2>Radii</h2>
      <div class="ui-gallery__row">
        <div v-for="radius in radii" :key="radius.label" class="ui-gallery__radius">
          <span class="ui-gallery__radius-chip" :style="{ borderRadius: radius.value }" />
          <span>{{ radius.label }}</span>
        </div>
      </div>
    </section>

    <section class="ui-gallery__section">
      <h2>Cards & lists</h2>
      <div class="ui-gallery__recipe-grid">
        <article class="app-card ui-gallery__card">
          <span class="app-eyebrow">app-card</span>
          <strong>静态面板</strong>
          <p>白底、1px hairline、16px 圆角，无阴影。用于设置分组与内容容器。</p>
        </article>
        <article class="app-card app-card--interactive ui-gallery__card">
          <span class="app-eyebrow">app-card--interactive</span>
          <strong>可点击卡片</strong>
          <p>hover / focus-within 时边框加深，不位移、不投影。</p>
        </article>
      </div>

      <div class="app-card ui-gallery__list" v-hover-fill>
        <div
          v-for="row in listRows"
          :key="row.title"
          class="app-list-row"
          data-hover-fill-item
        >
          <span class="ui-gallery__row-dot" />
          <div class="ui-gallery__row-copy">
            <strong>{{ row.title }}</strong>
            <span>{{ row.meta }}</span>
          </div>
          <span class="ui-gallery__row-value">{{ row.value }}</span>
        </div>
      </div>
      <p class="ui-gallery__note">app-list-row · 相邻行 hairline 分隔，行高 56px。</p>

      <div class="app-card ui-gallery__table">
        <div class="app-table-row ui-gallery__table-head">
          <span>名称</span><span>站点</span><span>状态</span><span>更新时间</span>
        </div>
        <div v-for="row in tableRows" :key="row.name" class="app-table-row">
          <strong>{{ row.name }}</strong>
          <span>{{ row.site }}</span>
          <span class="ui-gallery__status"><i />{{ row.status }}</span>
          <span>{{ row.updated }}</span>
        </div>
      </div>
      <p class="ui-gallery__note">app-table-row · 44px 行高，用于设置、日志与定时任务。</p>
    </section>

    <section class="ui-gallery__section">
      <h2>Media frame</h2>
      <div class="ui-gallery__recipe-grid">
        <div class="ui-gallery__stack">
          <MediaFrame class="ui-gallery__media" duration="12:34">
            <div class="ui-gallery__media-fill" />
          </MediaFrame>
          <span class="ui-gallery__note">时长徽标 · 16:9 · 10px 圆角</span>
        </div>
        <div class="ui-gallery__stack">
          <MediaFrame class="ui-gallery__media" duration="04:32" :progress="0.42" progress-label="示例播放进度">
            <div class="ui-gallery__media-fill ui-gallery__media-fill--alt" />
          </MediaFrame>
          <span class="ui-gallery__note">播放进度 · 已观看 42%</span>
        </div>
      </div>
    </section>

    <section class="ui-gallery__section">
      <h2>Shared hover fill</h2>
      <p class="ui-gallery__note">
        一个可移动的背景层在相邻项之间跳转。仅鼠标生效；键盘聚焦保留各自的
        focus ring；减少动效模式下退化为普通 hover。
      </p>
      <nav class="ui-gallery__hover-scope" aria-label="HoverFill 示例" v-hover-fill>
        <button
          v-for="item in hoverItems"
          :key="item"
          type="button"
          class="ui-gallery__hover-item"
          data-hover-fill-item
        >
          {{ item }}
        </button>
      </nav>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { DialogClose, DialogRoot, DialogTrigger, DropdownMenuRoot, DropdownMenuTrigger, PopoverRoot, PopoverTrigger, TooltipRoot, TooltipTrigger } from 'reka-ui'
import AppIcon from '@/shared/icons/AppIcon.vue'
import MediaFrame from '@/shared/components/layout/MediaFrame.vue'
import { Button, IconButton } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import { Checkbox } from '@/shared/ui/checkbox'
import { Switch } from '@/shared/ui/switch'
import { Select } from '@/shared/ui/select'
import { Badge } from '@/shared/ui/badge'
import { Alert } from '@/shared/ui/alert'
import { DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/dialog'
import { PopoverContent } from '@/shared/ui/popover'
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/shared/ui/dropdown-menu'
import { TooltipContent, TooltipProvider } from '@/shared/ui/tooltip'
import { TabsContent, TabsList, TabsRoot, TabsTrigger } from '@/shared/ui/tabs'
import { BounceDots, Skeleton, SkeletonText, Spinner } from '@/shared/ui/skeleton'

const inputValue = ref('')
const textareaValue = ref('')
const checkboxValue = ref(false)
const switchValue = ref(true)
const selectValue = ref('')
const dialogOpen = ref(false)
const popoverOpen = ref(false)

const radii = [
  { label: 'sm · 6', value: 'var(--radius-sm)' },
  { label: 'md · 8', value: 'var(--radius-md)' },
  { label: 'lg · 10', value: 'var(--radius-lg)' },
  { label: 'xl · 12', value: 'var(--radius-xl)' },
  { label: '2xl · 16', value: 'var(--radius-2xl)' },
  { label: 'pill', value: 'var(--radius-pill)' },
]

const listRows = [
  { title: '设计系统的单一来源', meta: '示例频道 · 今天 09:12', value: '12:04' },
  { title: '动效不是装饰，而是解释结构', meta: '示例频道 · 昨天', value: '08:37' },
  { title: '空状态、错误与键盘路径都属于设计', meta: '示例频道 · 2 天前', value: '21:56' },
]

const tableRows = [
  { name: '示例站点', site: 'bilibili', status: '运行中', updated: '10 分钟前' },
  { name: '备用站点', site: 'youtube', status: '待同步', updated: '2 小时前' },
]

const hoverItems = ['全部', '未读', '已收藏', '稍后观看']
</script>

<style scoped>
.ui-gallery {
  max-width: 60rem;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  color: hsl(var(--foreground));
}

.ui-gallery__header h1 {
  margin: 0 0 var(--space-2);
  font-family: var(--font-display);
  font-size: var(--app-text-2xl);
  font-weight: 650;
  letter-spacing: -0.02em;
}

.ui-gallery__header p {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  line-height: 1.6;
}

.ui-gallery__header code {
  font-family: var(--font-mono);
  font-size: var(--app-text-xs);
  background: hsl(var(--muted) / 0.5);
  border-radius: var(--radius-sm);
  padding: 0.125rem 0.375rem;
}

.ui-gallery__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  border-top: 1px solid hsl(var(--border) / 0.4);
  padding-top: var(--space-4);
}

.ui-gallery__section h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--app-text-lg);
  font-weight: 650;
  letter-spacing: -0.01em;
}

.ui-gallery__note {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  line-height: 1.6;
}

.ui-gallery__type {
  margin: 0;
  color: hsl(var(--foreground));
}

.ui-gallery__type--3xl {
  font-family: var(--font-display);
  font-size: var(--app-text-3xl);
  font-weight: 650;
  letter-spacing: -0.02em;
}

.ui-gallery__type--2xl {
  font-family: var(--font-display);
  font-size: var(--app-text-2xl);
  font-weight: 650;
  letter-spacing: -0.02em;
}

.ui-gallery__type--lg {
  font-size: var(--app-text-lg);
  font-weight: 600;
}

.ui-gallery__type--base {
  font-size: var(--app-text-base);
  line-height: var(--app-leading-body);
}

.ui-gallery__type--meta {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  font-weight: 500;
}

.ui-gallery__type--numeric {
  color: hsl(var(--muted-foreground));
  font-family: var(--font-numeric);
  font-size: var(--app-text-sm);
  font-variant-numeric: tabular-nums;
}

.ui-gallery__radius {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
}

.ui-gallery__radius-chip {
  width: 2rem;
  height: 2rem;
  border: 1px solid var(--app-surface-border);
  background: hsl(var(--card));
}

.ui-gallery__recipe-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: var(--space-4);
}

.ui-gallery__card {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: var(--space-4);
}

.ui-gallery__card strong {
  font-size: var(--app-text-base);
  font-weight: 600;
}

.ui-gallery__card p {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
  line-height: 1.55;
}

.ui-gallery__list,
.ui-gallery__table {
  overflow: hidden;
  padding: 0;
}

.ui-gallery__list .app-list-row {
  padding-inline: var(--space-4);
}

.ui-gallery__row-dot {
  width: 0.375rem;
  height: 0.375rem;
  flex: none;
  border-radius: var(--radius-pill);
  background: hsl(var(--muted-foreground) / 0.45);
}

.ui-gallery__row-copy {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.15rem;
}

.ui-gallery__row-copy strong {
  overflow: hidden;
  font-size: var(--app-text-base);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ui-gallery__row-copy span {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
}

.ui-gallery__row-value {
  flex: none;
  color: hsl(var(--muted-foreground));
  font-family: var(--font-numeric);
  font-size: var(--app-text-sm);
  font-variant-numeric: tabular-nums;
}

.ui-gallery__table .app-table-row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) 0.8fr 0.8fr 0.9fr;
  align-items: center;
  gap: var(--space-3);
  padding-inline: var(--space-4);
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
}

.ui-gallery__table .app-table-row strong {
  color: hsl(var(--foreground));
  font-weight: 600;
}

.ui-gallery__table-head {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.ui-gallery__status {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.ui-gallery__status i {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: var(--radius-pill);
  background: hsl(var(--muted-foreground) / 0.5);
}

.ui-gallery__media {
  width: 100%;
}

.ui-gallery__media-fill {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, hsl(0 0% 72%), hsl(0 0% 46%));
}

.ui-gallery__media-fill--alt {
  background: linear-gradient(135deg, hsl(0 0% 58%), hsl(0 0% 32%));
}

.ui-gallery__hover-scope {
  display: flex;
  max-width: 24rem;
  flex-direction: column;
  gap: 2px;
  padding: 0.25rem;
  border: 1px solid var(--app-surface-border);
  border-radius: var(--radius-xl);
  background: hsl(var(--card));
}

.ui-gallery__hover-item {
  display: flex;
  min-height: 2.25rem;
  align-items: center;
  border: 0;
  border-radius: var(--radius-md);
  padding: 0 var(--space-3);
  background: transparent;
  color: hsl(var(--foreground));
  font: inherit;
  font-size: var(--app-text-base);
  text-align: left;
  cursor: pointer;
}

.ui-gallery__hover-item:focus-visible {
  outline: 2px solid hsl(var(--ring) / 0.8);
  outline-offset: -2px;
}

.ui-gallery__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}

.ui-gallery__stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: 34rem;
}

.ui-gallery__inline {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--app-text-base);
}

.ui-gallery__panel {
  margin: 0;
  padding: var(--space-3);
  font-size: var(--app-text-base);
  color: hsl(var(--muted-foreground));
}
</style>
