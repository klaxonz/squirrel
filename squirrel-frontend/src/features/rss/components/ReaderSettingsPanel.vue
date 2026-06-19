<template>
  <div
    v-if="visible"
    class="absolute right-0 top-full z-50 mt-1.5 w-48 rounded-xl border border-border/30 bg-popover text-popover-foreground p-3 shadow-[0_4px_16px_rgba(0,0,0,0.04)] dark:shadow-[0_4px_24px_rgba(0,0,0,0.4)] space-y-3 animate-fade-in"
  >
    <div class="space-y-1">
      <span class="text-[9px] font-bold text-muted-foreground uppercase tracking-wider block">排版字体</span>
      <div class="grid grid-cols-2 gap-1 bg-accent/20 p-0.5 rounded-lg border border-border/5">
        <button
          @click="select('sans')"
          class="py-1 text-[10px] font-semibold rounded-md transition-all text-center cursor-pointer"
          :class="fontFamily === 'sans' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
          title="极简现代 (Inter)"
        >Inter</button>
        <button
          @click="select('outfit')"
          class="py-1 text-[10px] font-semibold rounded-md transition-all text-center cursor-pointer"
          :class="fontFamily === 'outfit' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
          title="优雅圆润 (Outfit)"
        >Outfit</button>
        <button
          @click="select('serif')"
          class="py-1 text-[10px] font-semibold rounded-md transition-all text-center font-serif cursor-pointer"
          :class="fontFamily === 'serif' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
          title="经典衬线 (Georgia)"
        >Georgia</button>
        <button
          @click="select('lora')"
          class="py-1 text-[10px] font-semibold rounded-md transition-all text-center font-serif cursor-pointer"
          :class="fontFamily === 'lora' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
          title="人文阅读 (Lora)"
        >Lora</button>
      </div>
    </div>

    <div class="space-y-1">
      <div class="flex items-center justify-between">
        <span class="text-[9px] font-bold text-muted-foreground uppercase tracking-wider block">字号大小</span>
        <span class="text-[10px] font-semibold tabular-nums text-foreground/80">{{ fontSize }}px</span>
      </div>
      <div class="flex items-center gap-1">
        <button
          @click="changeSize(-1)"
          class="h-7 w-7 rounded-lg border border-border/50 bg-accent/25 hover:bg-accent/40 flex items-center justify-center text-xs font-bold transition-all text-muted-foreground hover:text-foreground cursor-pointer flex-1"
          :disabled="fontSize <= 12"
        >A-</button>
        <button
          @click="changeSize(1)"
          class="h-7 w-7 rounded-lg border border-border/50 bg-accent/25 hover:bg-accent/40 flex items-center justify-center text-xs font-bold transition-all text-muted-foreground hover:text-foreground cursor-pointer flex-1"
          :disabled="fontSize >= 24"
        >A+</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  visible: boolean
  fontFamily: string
  fontSize: number
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'update:fontFamily': [value: string]
  'update:fontSize': [value: number]
  save: []
}>()

function select(family: string) {
  emit('update:fontFamily', family)
  emit('save')
}

function changeSize(delta: number) {
  const newSize = props.fontSize + delta
  if (newSize >= 12 && newSize <= 24) {
    emit('update:fontSize', newSize)
    emit('save')
  }
}
</script>
