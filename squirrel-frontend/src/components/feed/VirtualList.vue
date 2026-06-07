<template>
  <div
    ref="container"
    class="virtual-list-container"
    @scroll.passive="onScroll"
  >
    <div
      class="scroll-phantom"
      :style="{ height: totalHeight + 'px' }"
    ></div>

    <div
      class="visible-items"
      :style="itemStyle"
    >
    <div
      v-for="entry in visibleItems"
      :key="entry.item[keyField || 'id']"
      class="list-item"
    >
        <slot
          name="item"
          :item="entry.item"
          :index="entry.index"
          :row="entry.row"
          :column="entry.column"
        ></slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue';

const MAX_SCROLL_POSITIONS = 50;
const scrollPositions = new Map();

const props = defineProps<{
  items?: unknown[]
  itemSize?: number
  keyField?: string
  buffer?: number
  gridItems?: number
  prerender?: number
  bufferMode?: 'px' | 'rows' | 'auto'
  rangeChangeThrottleMs?: number
  bottomPadding?: number
  cacheKey?: string
}>()

const emit = defineEmits(['scroll', 'range-change', 'reach-start', 'reach-end']);

const container = ref<HTMLElement | null>(null);
const scrollTop = ref(0);
const containerHeight = ref(typeof window !== 'undefined' ? window.innerHeight : 1000); 

const itemsRef = shallowRef<unknown[]>(props.items ?? []);

const instanceId = ref(Symbol('virtual-list-instance'));
let resizeObserver: ResizeObserver | null = null;
let rangeThrottleTimer: ReturnType<typeof setTimeout> | null = null;
let rangeThrottleLast = 0;

const stopObservingContainer = () => {
  if (!resizeObserver) return;
  resizeObserver.disconnect();
  resizeObserver = null;
};

const getScrollCacheKey = () => {
  return props.cacheKey || instanceId.value;
};

const saveScrollPosition = (position: number) => {
  const key = getScrollCacheKey();
  if (!key) {
    return;
  }

  if (scrollPositions.size >= MAX_SCROLL_POSITIONS && !scrollPositions.has(key)) {
    const firstKey = scrollPositions.keys().next().value;
    scrollPositions.delete(firstKey);
  }

  scrollPositions.set(key, position);
};

const restoreScrollPosition = () => {
  const key = getScrollCacheKey();
  if (!key || !scrollPositions.has(key)) {
    return;
  }

  const targetPos = scrollPositions.get(key) ?? 0;
  scrollToOffset(targetPos);
};

const columnCount = computed(() => Math.max(1, props.gridItems || 1));
const rowHeight = computed(() => Math.max(1, Math.floor(props.itemSize || 300)));
const rowCount = computed(() => Math.ceil((itemsRef.value ?? []).length / columnCount.value));

const itemStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: `repeat(${columnCount.value}, minmax(0, 1fr))`,
  gridAutoRows: `${rowHeight.value}px`,
  width: '100%',
  transform: `translateY(${offset.value}px)`,
}));

const bufferRows = computed(() => {
  const b = props.buffer ?? 0;
  if (props.bufferMode === 'rows') return Math.max(0, Math.ceil(b));
  const bufferPx = props.bufferMode === 'auto' && b <= 50
    ? b * rowHeight.value
    : b;
  return Math.max(0, Math.ceil(bufferPx / rowHeight.value));
});

const prerenderRows = computed(() => {
  if (!props.prerender) return 0;
  return Math.ceil(props.prerender / columnCount.value);
});

const range = computed(() => {
  const items = itemsRef.value ?? [];
  const len = items.length;
  if (len === 0) return { startRow: 0, endRow: 0, startIndex: 0, endIndex: 0 };

  const safeScrollTop = Math.max(0, scrollTop.value);
  const firstVisibleRow = Math.floor(safeScrollTop / rowHeight.value);
  const viewportRows = Math.max(1, Math.ceil(containerHeight.value / rowHeight.value));
  const startRow = Math.max(0, firstVisibleRow - bufferRows.value);
  let endRow = Math.min(rowCount.value, firstVisibleRow + viewportRows + bufferRows.value + prerenderRows.value);

  if (endRow <= startRow) endRow = Math.min(rowCount.value, startRow + 1);

  const startIndex = startRow * columnCount.value;
  const endIndex = Math.min(len, endRow * columnCount.value);

  return { startRow, endRow, startIndex, endIndex };
});

const visibleItems = computed(() => {
  const { startIndex, endIndex } = range.value;
  const items = itemsRef.value ?? [];
  const result: { item: any; index: number; row: number; column: number }[] = [];
  const cols = columnCount.value;
  for (let i = startIndex; i < endIndex; i++) {
    const item = items[i];
    if (item) {
      result.push({
        item,
        index: i,
        row: Math.floor(i / cols),
        column: i % cols
      });
    }
  }
  return result;
});

const totalHeight = computed(() => {
  return rowCount.value * rowHeight.value + (props.bottomPadding ?? 0);
});

const offset = computed(() => range.value.startRow * rowHeight.value);
const maxScrollTop = computed(() => Math.max(0, totalHeight.value - containerHeight.value));

const emitRangeChange = () => {
  const now = performance.now();
  if ((props.rangeChangeThrottleMs ?? 0) > 0) {
    if (rangeThrottleTimer) return;
    const elapsed = now - rangeThrottleLast;
    const wait = Math.max(0, (props.rangeChangeThrottleMs ?? 0) - elapsed);
    rangeThrottleTimer = setTimeout(() => {
      rangeThrottleTimer = null;
      rangeThrottleLast = performance.now();
      const r = range.value;
      emit('range-change', { start: r.startIndex, end: r.endIndex, startRow: r.startRow, endRow: r.endRow });
    }, wait);
  } else {
    const r = range.value;
    emit('range-change', { start: r.startIndex, end: r.endIndex, startRow: r.startRow, endRow: r.endRow });
  }
};

const updateContainerHeight = () => {
  containerHeight.value = container.value?.clientHeight || 0;
};

const observeContainer = () => {
  if (resizeObserver || !container.value) return;
  resizeObserver = new ResizeObserver(() => {
    updateContainerHeight();
    clampScrollTop();
  });
  resizeObserver.observe(container.value);
};

const clampScrollTop = () => {
  if (!container.value) return;
  const clamped = Math.max(0, Math.min(container.value.scrollTop, maxScrollTop.value));
  if (clamped !== container.value.scrollTop) {
    container.value.scrollTop = clamped;
  }
  scrollTop.value = clamped;
};

const onScroll = () => {
  if (!container.value) return;
  const st = container.value.scrollTop;
  scrollTop.value = st;
  saveScrollPosition(st);

  emit('scroll', {
    target: container.value,
    scrollTop: st
  });

  if (st <= 0) emit('reach-start');
  if (st + containerHeight.value >= totalHeight.value - 1) emit('reach-end');
};

const scrollToOffset = (offsetPx: number) => {
  if (!container.value) return;
  const nextOffset = Math.max(0, Math.min(offsetPx, maxScrollTop.value));
  container.value.scrollTop = nextOffset;
  scrollTop.value = nextOffset;
  saveScrollPosition(nextOffset);
};

const scrollToIndex = (index: number, align: string = 'start') => {
  const clamped = Math.max(0, Math.min(index, (itemsRef.value ?? []).length - 1));
  const row = Math.floor(clamped / columnCount.value);
  const base = row * rowHeight.value;
  let target = base;
  if (align === 'center') target = base - containerHeight.value / 2 + rowHeight.value / 2;
  if (align === 'end') target = base - containerHeight.value + rowHeight.value;
  scrollToOffset(target);
};

const reset = () => {
  scrollToOffset(0);
};

const isItemsEqual = (a: any[], b: any[]) => {
  if (a === b) return true;
  if (!a || !b) return false;
  if (a.length !== b.length) return false;
  const key = props.keyField || 'id';
  for (let i = 0; i < a.length; i++) {
    const av = a[i];
    const bv = b[i];
    if (av === bv) continue;
    if (!av || !bv) return false;
    if (av[key] !== bv[key]) return false;
  }
  return true;
};

watch(
  () => props.items,
  (newItems: any[] | undefined) => {
    const oldItems = itemsRef.value ?? [];
    const newLen = newItems ? newItems.length : 0;
    const oldLen = oldItems ? oldItems.length : 0;

    const appended = oldLen > 0 && newLen > oldLen && isItemsEqual(oldItems.slice(0, oldLen), (newItems ?? []).slice(0, oldLen));
    itemsRef.value = newItems || [];

    if (!appended) {
      scrollToOffset(0);
    } else {
      nextTick(() => {
        updateContainerHeight();
        clampScrollTop();
      });
    }
  },
  { immediate: false }
);

watch(
  () => [columnCount.value, rowHeight.value],
  ([newCols, newRowH], [oldCols, oldRowH]) => {
    const anchorRow = Math.floor(scrollTop.value / oldRowH);
    const anchorIndex = Math.min((itemsRef.value ?? []).length - 1, anchorRow * oldCols);
    nextTick(() => {
      updateContainerHeight();
      if (anchorIndex >= 0) {
        scrollToIndex(anchorIndex);
      } else {
        clampScrollTop();
      }
    });
  }
);

watch(totalHeight, () => {
  nextTick(() => {
    updateContainerHeight();
    clampScrollTop();
  });
});

watch(range, () => {
  emitRangeChange();
}, { immediate: true });

onMounted(() => {
  observeContainer();
  nextTick(() => {
    updateContainerHeight();
    restoreScrollPosition();
    clampScrollTop();
  });
});

onActivated(() => {
  nextTick(() => {
    observeContainer();
    updateContainerHeight();
    restoreScrollPosition();
    clampScrollTop();
  });
});

onDeactivated(() => {
  stopObservingContainer();
});

onBeforeUnmount(() => {
  if (!props.cacheKey) {
    scrollPositions.delete(instanceId.value);
  }
  stopObservingContainer();
  if (rangeThrottleTimer) {
    clearTimeout(rangeThrottleTimer);
    rangeThrottleTimer = null;
  }
});

defineExpose({ scrollToOffset, scrollToIndex, reset, container, range, totalHeight });
</script>

<style scoped>
.virtual-list-container {
  position: relative;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-y: contain;
  overflow-anchor: none;
}

.scroll-phantom {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  z-index: -1;
}

.visible-items {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  will-change: transform;
  overflow-anchor: none;
}

.list-item {
  min-width: 0;
  min-height: 0;
  height: 100%;
  list-style: none;
}

.list-item::marker {
  content: '';
}

</style>
