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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { DialogClose, DialogRoot, DialogTrigger, DropdownMenuRoot, DropdownMenuTrigger, PopoverRoot, PopoverTrigger, TooltipRoot, TooltipTrigger } from 'reka-ui'
import AppIcon from '@/shared/icons/AppIcon.vue'
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
  font-size: var(--app-text-2xl);
  font-weight: 700;
  margin: 0 0 var(--space-2);
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
  font-size: var(--app-text-lg);
  font-weight: 700;
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
