<template>
  <div 
    ref="container"
    class="virtual-list-container"
    @scroll.passive="handleScroll"
  >
    <div 
      class="scroll-phantom" 
      :style="{ height: totalHeight + 'px' }"
    ></div>

      <transition-group 
        name="terminal-stagger"
        tag="div"
        class="visible-items"
        :style="itemStyle"
      >
        <div
          v-for="item in visibleItems"
          :key="item[keyField]"
          class="list-item"
        >
          <slot 
            name="item" 
            :item="item"
            :index="item._index"
            :row="item._row"
            :column="item._column"
          ></slot>
        </div>
      </transition-group>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue';

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  itemSize: {
    type: Number,
    default: 50
  },
  keyField: {
    type: String,
    default: 'id'
  },
  buffer: {
    type: Number,
    default: 5
  },
  gridItems: {
    type: Number,
    default: 1
  },
  prerender: {
    type: Number,
    default: 0
  },
  bufferMode: {
    type: String,
    default: 'px',
    validator: (v) => ['px', 'rows', 'auto'].includes(v)
  },
  rangeChangeThrottleMs: {
    type: Number,
    default: 0
  },
  bottomPadding: {
    type: Number,
    default: 0
  },
});

const emit = defineEmits(['scroll', 'range-change', 'reach-start', 'reach-end']);

const container = ref(null);
const scrollTop = ref(0);
const containerHeight = ref(0);

const MAX_SCROLL_POSITIONS = 50;
const scrollPositions = ref(new Map());
const instanceId = ref(null);
const resizeObserver = ref(null);
const rangeThrottleState = { last: 0, timer: null, lastArgs: null };

const saveScrollPosition = (id, position) => {
  if (scrollPositions.value.size >= MAX_SCROLL_POSITIONS) {
    const firstKey = scrollPositions.value.keys().next().value;
    scrollPositions.value.delete(firstKey);
  }
  scrollPositions.value.set(id, position);
};

const restoreScrollPosition = () => {
  if (instanceId.value && scrollPositions.value.has(instanceId.value)) {
    const targetPos = scrollPositions.value.get(instanceId.value);
    scrollToOffset(targetPos);
  }
};

const columnCount = computed(() => Math.max(1, props.gridItems));
const rowHeight = computed(() => Math.max(1, Math.floor(props.itemSize || 0)));
const rowCount = computed(() => Math.ceil(props.items.length / columnCount.value));

const itemStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: `repeat(${columnCount.value}, minmax(0, 1fr))`,
  gridAutoRows: `${rowHeight.value}px`,
  width: '100%',
  transform: `translateY(${offset.value}px)`,
}));

const bufferRows = computed(() => {
  if (props.bufferMode === 'rows') return Math.max(0, Math.ceil(props.buffer));
  const bufferPx = props.bufferMode === 'auto' && props.buffer <= 50
    ? props.buffer * rowHeight.value
    : props.buffer;
  return Math.max(0, Math.ceil(bufferPx / rowHeight.value));
});

const prerenderRows = computed(() => {
  if (!props.prerender) return 0;
  return Math.ceil(props.prerender / columnCount.value);
});

const range = computed(() => {
  if (rowCount.value === 0) return { startRow: 0, endRow: 0, startIndex: 0, endIndex: 0 };

  const safeScrollTop = Math.max(0, scrollTop.value);
  const firstVisibleRow = Math.floor(safeScrollTop / rowHeight.value);
  const viewportRows = Math.max(1, Math.ceil(containerHeight.value / rowHeight.value));
  const startRow = Math.max(0, firstVisibleRow - bufferRows.value);
  let endRow = Math.min(rowCount.value, firstVisibleRow + viewportRows + bufferRows.value + prerenderRows.value);

  if (endRow <= startRow) endRow = Math.min(rowCount.value, startRow + 1);

  const startIndex = startRow * columnCount.value;
  const endIndex = Math.min(props.items.length, endRow * columnCount.value);

  return { startRow, endRow, startIndex, endIndex };
});

const visibleItems = computed(() => {
  const { startIndex, endIndex } = range.value;
  return props.items.slice(startIndex, endIndex).map((item, i) => {
    const realIndex = startIndex + i;
    return {
      ...item,
      _index: realIndex,
      _row: Math.floor(realIndex / columnCount.value),
      _column: realIndex % columnCount.value
    };
  });
});

const totalHeight = computed(() => {
  return rowCount.value * rowHeight.value + props.bottomPadding;
});

const offset = computed(() => range.value.startRow * rowHeight.value);
const maxScrollTop = computed(() => Math.max(0, totalHeight.value - containerHeight.value));

const emitRangeChange = (r) => {
  const now = performance.now();
  if (props.rangeChangeThrottleMs > 0) {
    rangeThrottleState.lastArgs = r;
    if (!rangeThrottleState.timer) {
      const elapsed = now - rangeThrottleState.last;
      const wait = Math.max(0, props.rangeChangeThrottleMs - elapsed);
      rangeThrottleState.timer = setTimeout(() => {
        rangeThrottleState.timer = null;
        rangeThrottleState.last = performance.now();
        const args = rangeThrottleState.lastArgs;
        emit('range-change', { start: args.startIndex, end: args.endIndex, startRow: args.startRow, endRow: args.endRow });
      }, wait);
    }
  } else {
    emit('range-change', { start: r.startIndex, end: r.endIndex, startRow: r.startRow, endRow: r.endRow });
  }
};

const updateContainerHeight = () => {
  containerHeight.value = container.value?.clientHeight || 0;
};

const observeContainer = () => {
  if (resizeObserver.value || !container.value) return;
  resizeObserver.value = new ResizeObserver(() => {
    updateContainerHeight();
    clampScrollTop();
  });
  resizeObserver.value.observe(container.value);
};

const clampScrollTop = () => {
  if (!container.value) return;
  const clamped = Math.max(0, Math.min(container.value.scrollTop, maxScrollTop.value));
  if (clamped !== container.value.scrollTop) {
    container.value.scrollTop = clamped;
  }
  scrollTop.value = clamped;
};

const handleScroll = () => {
  if (!container.value) return;

  scrollTop.value = container.value.scrollTop;
  saveScrollPosition(instanceId.value, scrollTop.value);

  emit('scroll', {
    target: container.value,
    scrollTop: scrollTop.value
  });

  if (scrollTop.value <= 0) emit('reach-start');
  const nearEnd = scrollTop.value + containerHeight.value >= totalHeight.value - 1;
  if (nearEnd) emit('reach-end');
};

const scrollToOffset = (offsetPx) => {
  if (!container.value) return;
  const nextOffset = Math.max(0, Math.min(offsetPx, maxScrollTop.value));
  container.value.scrollTop = nextOffset;
  scrollTop.value = nextOffset;
  saveScrollPosition(instanceId.value, nextOffset);
};

const scrollToIndex = (index, align = 'start') => {
  const clamped = Math.max(0, Math.min(index, props.items.length - 1));
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

onMounted(() => {
  instanceId.value = Symbol('virtual-list-instance');
  observeContainer();
  nextTick(() => {
    updateContainerHeight();
    restoreScrollPosition();
    clampScrollTop();
  });
});

onActivated(() => {
  updateContainerHeight();
  restoreScrollPosition();
});

onBeforeUnmount(() => {
  scrollPositions.value.delete(instanceId.value);
  if (resizeObserver.value) {
    resizeObserver.value.disconnect();
    resizeObserver.value = null;
  }
  if (rangeThrottleState.timer) clearTimeout(rangeThrottleState.timer);
});

watch(() => props.items, (newItems, oldItems) => {
  const oldLen = oldItems?.length || 0;
  const newLen = newItems?.length || 0;
  let appended = false;

  if (oldLen > 0 && newLen >= oldLen) {
    const key = props.keyField || 'id';
    appended = true;
    for (let i = 0; i < oldLen; i++) {
      if (!newItems[i] || newItems[i][key] !== oldItems[i][key]) {
        appended = false;
        break;
      }
    }
  }

  if (!appended) {
    scrollToOffset(0);
  } else {
    nextTick(() => {
      updateContainerHeight();
      clampScrollTop();
    });
  }
});

watch(
  () => [columnCount.value, rowHeight.value],
  (_, oldValue) => {
    if (!oldValue) return;
    const [oldColumnCount, oldRowHeight] = oldValue;
    const anchorRow = Math.floor(scrollTop.value / oldRowHeight);
    const anchorIndex = Math.min(props.items.length - 1, anchorRow * oldColumnCount);
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

watch(range, (r) => {
  emitRangeChange(r);
}, { immediate: true });

defineExpose({ scrollToOffset, scrollToIndex, reset, container, range, totalHeight });
</script>

<style scoped>
.virtual-list-container {
  position: relative;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
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
}

.list-item {
  will-change: transform;
  min-width: 0;
  min-height: 0;
  height: 100%;
  list-style: none;
}

.list-item::marker {
  content: '';
}

.terminal-stagger-enter-active {
  transition: all 0.5s cubic-bezier(0.19, 1, 0.22, 1);
}

.terminal-stagger-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.98);
}

.terminal-stagger-move {
  transition: transform 0.4s ease;
}
</style>
