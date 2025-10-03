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
    <div 
      class="visible-items"
      :style="{ 
        transform: `translateY(${offset}px)`,
        ...itemStyle
      }"
    >
      <div
        v-for="(item, i) in visibleItems"
        :key="item[keyField]"
        :ref="el => setItemRef(el, i)"
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
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onActivated, onBeforeUnmount, nextTick } from 'vue';

// ==================== Props 配置 ====================
const props = defineProps({
  items: {
    type: Array,
    required: true
  },
  itemSize: {
    type: [Number, Function],
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
  itemSecondarySize: {
    type: Number,
    default: 300
  },
  prerender: {
    type: Number,
    default: 0
  },
  bufferMode: {
    type: String,
    default: 'px', // 'px' | 'rows' | 'auto'
    validator: (v) => ['px', 'rows', 'auto'].includes(v)
  },
  anchorMode: {
    type: String,
    default: 'row', // 'row' | 'element'
    validator: (v) => ['row', 'element'].includes(v)
  },
  anchorThresholdPx: {
    type: Number,
    default: 1.5
  },
  rangeChangeThrottleMs: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits(['scroll', 'range-change', 'reach-start', 'reach-end']);

// ==================== 基础状态 ====================
const container = ref(null);
const itemEls = ref([]);
const scrollTop = ref(0);
const currentScrollTop = ref(0);
const suppressScroll = ref(false);

// ==================== 滚动位置管理 ====================
const MAX_SCROLL_POSITIONS = 50; // 限制 Map 大小，防止内存泄漏
const scrollPositions = ref(new Map());
const instanceId = ref(null);

const saveScrollPosition = (id, position) => {
  // 限制 Map 大小，移除最旧的条目
  if (scrollPositions.value.size >= MAX_SCROLL_POSITIONS) {
    const firstKey = scrollPositions.value.keys().next().value;
    scrollPositions.value.delete(firstKey);
  }
  scrollPositions.value.set(id, position);
};

const restoreScrollPosition = () => {
  if (instanceId.value && scrollPositions.value.has(instanceId.value)) {
    const targetPos = scrollPositions.value.get(instanceId.value);
    container.value.scrollTop = targetPos;
    scrollTop.value = targetPos;
    currentScrollTop.value = targetPos;
    requestAnimationFrame(() => {
      container.value.scrollTop = targetPos;
      updateHeights();
    });
  }
};

// ==================== 网格布局计算 ====================
const columnCount = computed(() => Math.max(1, props.gridItems));

const itemStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: `repeat(${columnCount.value}, 1fr)`,
  width: '100%',
}));

// ==================== 高度管理 ====================
const rowHeights = ref([]);
const updateHeightsTimeout = ref(null);

// 估算行高（优先使用固定 itemSize，其次使用平均行高，最后回退 secondarySize）
const defaultRowHeight = computed(() => {
  if (typeof props.itemSize === 'number') return props.itemSize;
  if (rowHeights.value.length > 0) return averageRowHeight.value;
  return props.itemSecondarySize;
});

// 平均行高计算
const averageRowHeight = computed(() => {
  if (rowHeights.value.length === 0) return props.itemSecondarySize;
  const validHeights = rowHeights.value.filter(h => h > 0);
  return Math.max(50, validHeights.reduce((a, b) => a + b, 0) / validHeights.length) || props.itemSecondarySize;
});

// 缓冲区像素计算
const bufferPxComputed = computed(() => {
  if (props.bufferMode === 'px') return props.buffer;
  if (props.bufferMode === 'rows') return props.buffer * averageRowHeight.value;
  return props.buffer > 50 ? props.buffer : props.buffer * averageRowHeight.value;
});

// ==================== 工具函数 ====================
// 累计高度到某一行（不含该行）
const calculateCumulativeHeight = (heights, upToRow, fallback) => {
  let sum = 0;
  for (let r = 0; r < upToRow; r++) sum += heights[r] || fallback;
  return sum;
};

// 滚动位置校正（含阈值与抖动抑制）
const applyScrollAdjustment = (delta) => {
  if (!container.value) return;
  if (Math.abs(delta) <= props.anchorThresholdPx) return;
  suppressScroll.value = true;
  container.value.scrollTop = Math.max(0, container.value.scrollTop + delta);
  scrollTop.value = container.value.scrollTop;
  currentScrollTop.value = scrollTop.value;
  requestAnimationFrame(() => { suppressScroll.value = false; });
};

// ==================== 可见范围计算 ====================
const containerHeight = computed(() => {
  return container.value?.clientHeight || 0
});

// 行偏移计算
const rowOffsets = computed(() => {
  const count = Math.ceil(props.items.length / columnCount.value);
  const offsets = new Array(count);
  let acc = 0;
  for (let r = 0; r < count; r++) {
    offsets[r] = acc;
    acc += rowHeights.value[r] || defaultRowHeight.value;
  }
  return offsets;
});

// 二分查找起始行
const findStartRow = (scrollTopVal) => {
  const offsets = rowOffsets.value;
  if (offsets.length === 0) return 0;
  let low = 0, high = offsets.length - 1, ans = 0;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (offsets[mid] <= scrollTopVal) {
      ans = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  return ans;
};

// 二分查找结束行
const findEndRowByLimit = (limitPx) => {
  const offsets = rowOffsets.value;
  let low = 0, high = offsets.length; // upper_bound
  while (low < high) {
    const mid = (low + high) >> 1;
    if (offsets[mid] < limitPx) low = mid + 1; else high = mid;
  }
  return low;
};

// 可见范围计算
const range = computed(() => {
  const rowCount = Math.ceil(props.items.length / columnCount.value);
  if (rowCount === 0) return { startRow: 0, endRow: 0, startIndex: 0, endIndex: 0, offsetPx: 0 };
  
  const bufferPx = bufferPxComputed.value;
  const st = Math.max(0, currentScrollTop.value);
  const startRow = Math.max(0, findStartRow(st - bufferPx));
  const endLimit = st + containerHeight.value + bufferPx;
  let endRow = findEndRowByLimit(endLimit);
  
  // 额外预渲染若干行
  if (props.prerender && props.prerender > 0) {
    const extraRows = Math.ceil(props.prerender / Math.max(1, columnCount.value));
    endRow = Math.min(rowCount, endRow + extraRows);
  }
  
  // 至少包含一行
  if (endRow <= startRow) endRow = Math.min(rowCount, startRow + 1);
  
  const startIndex = startRow * columnCount.value;
  const endIndex = Math.min(props.items.length, endRow * columnCount.value);
  const offsetPx = rowOffsets.value[startRow] || 0;
  
  return { startRow, endRow, startIndex, endIndex, offsetPx };
});

// 可见项计算
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

// 总高度计算
const totalHeight = computed(() => {
  const rowCount = Math.ceil(props.items.length / columnCount.value);
  return Array.from({ length: rowCount }).reduce((acc, _, row) => {
    return acc + (rowHeights.value[row] || defaultRowHeight.value);
  }, 0);
});

// 当前偏移量
const offset = computed(() => {
  const off = range.value.offsetPx || 0;
  const maxOff = Math.max(0, totalHeight.value - containerHeight.value);
  return Math.min(Math.max(0, off), maxOff);
});

// ==================== 观察器管理 ====================
const resizeObserver = ref(null);
const observedElements = ref(new Set());

// 设置元素引用并注册观察器
const setItemRef = (el, i) => {
  const prevEl = itemEls.value[i];
  if (prevEl && observedElements.value.has(prevEl) && el !== prevEl) {
    if (resizeObserver.value) resizeObserver.value.unobserve(prevEl);
    observedElements.value.delete(prevEl);
  }
  if (el) {
    itemEls.value[i] = el;
    if (resizeObserver.value && !observedElements.value.has(el)) {
      resizeObserver.value.observe(el);
      observedElements.value.add(el);
    }
  } else {
    itemEls.value[i] = null;
  }
};

// 更新已渲染元素的观察器
const updateItemObservers = () => {
  if (!resizeObserver.value) return;
  const nextSet = new Set(itemEls.value.filter(Boolean));

  // 观察新增元素
  nextSet.forEach(el => {
    if (!observedElements.value.has(el)) {
      resizeObserver.value.observe(el);
    }
  });

  // 取消观察已移除元素
  observedElements.value.forEach(el => {
    if (!nextSet.has(el)) {
      resizeObserver.value.unobserve(el);
    }
  });

  observedElements.value = nextSet;
};

// 初始化尺寸观察器
const observeResize = () => {
  if (resizeObserver.value) return;

  resizeObserver.value = new ResizeObserver(entries => {
    entries.forEach(entry => {
      if (entry.target === container.value) {
        updateHeights();
      } else {
        // 列表项尺寸变化，触发行高更新
        updateHeights();
      }
    });
  });

  updateItemObservers();
  if (container.value) {
    resizeObserver.value.observe(container.value);
  }
};

// ==================== 高度更新逻辑 ====================
let pendingHeightRaf = null;

const updateHeights = () => {
  if (pendingHeightRaf) return;
  pendingHeightRaf = requestAnimationFrame(() => {
    pendingHeightRaf = null;
    const prevRowHeights = rowHeights.value;
    const startRowBefore = range.value.startRow;
    
    // 计算更新前偏移
    const prevOffsetBefore = calculateCumulativeHeight(prevRowHeights, startRowBefore, defaultRowHeight.value);

    const newRowHeights = [...prevRowHeights];
    itemEls.value.forEach((el, i) => {
      if (!el || !visibleItems.value[i]) return;
      const index = visibleItems.value[i]._index;
      const row = Math.floor(index / columnCount.value);
      const height = el.clientHeight;
      if (!newRowHeights[row] || height > newRowHeights[row]) {
        newRowHeights[row] = height;
      }
    });
    rowHeights.value = newRowHeights;

    // 计算更新后偏移并做锚定修正，避免抖动
    const newOffsetBefore = calculateCumulativeHeight(newRowHeights, startRowBefore, defaultRowHeight.value);
    const delta = newOffsetBefore - prevOffsetBefore;
    
    if (container.value) {
      let applyDelta = 0;
      if (props.anchorMode === 'element') {
        // 选择第一个可见元素作为锚定元素
        const firstEl = itemEls.value.find(Boolean);
        if (firstEl) {
          const beforeTop = firstEl.getBoundingClientRect().top;
          // 强制同步 reflow 之后再取一次 top
          firstEl.offsetHeight;
          const afterTop = firstEl.getBoundingClientRect().top;
          applyDelta = beforeTop - afterTop;
        } else {
          applyDelta = delta;
        }
      } else {
        applyDelta = delta;
      }
      applyScrollAdjustment(applyDelta);
    }
  });
};

// ==================== 事件处理 ====================
// 带节流的 range-change 事件发射
const rangeThrottleState = { last: 0, timer: null, lastArgs: null };

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

// 滚动事件处理
const handleScroll = () => {
  if (!container.value) return;
  
  scrollTop.value = container.value.scrollTop;
  currentScrollTop.value = scrollTop.value;
  if (suppressScroll.value) {
    return;
  }
  
  saveScrollPosition(instanceId.value, scrollTop.value);

  // 向下兼容：提供与原有使用一致的 target 字段
  emit('scroll', { 
    target: container.value,
    scrollTop: scrollTop.value
  });
  
  if (scrollTop.value <= 0) emit('reach-start');
  const nearEnd = scrollTop.value + containerHeight.value >= totalHeight.value - 1;
  if (nearEnd) emit('reach-end');

  // 使用更精确的防抖时间（100ms）
  if (!updateHeightsTimeout.value) {
    updateHeightsTimeout.value = setTimeout(() => {
      updateHeights();
      updateHeightsTimeout.value = null;
    }, 100);
  }
};

// ==================== 生命周期钩子 ====================
onMounted(() => {
  instanceId.value = Symbol('virtual-list-instance');
  observeResize();
  nextTick(() => {
    currentScrollTop.value = container.value?.scrollTop || 0;
    restoreScrollPosition();
    updateItemObservers();
    updateHeights();
  });
});

onActivated(() => {
  restoreScrollPosition();
  // 组件在 keep-alive 场景下被激活时，重新测量以避免隐藏期尺寸为 0 导致的空白
  nextTick(() => {
    updateItemObservers();
    updateHeights();
  });
});

onBeforeUnmount(() => {
  scrollPositions.value.delete(instanceId.value);
  if (resizeObserver.value) {
    resizeObserver.value.disconnect();
    resizeObserver.value = null;
  }
  if (updateHeightsTimeout.value) {
    clearTimeout(updateHeightsTimeout.value);
    updateHeightsTimeout.value = null;
  }
});

// ==================== 数据变化监听 ====================
// 数据源变更时：若为尾部追加则保留已测量行高，否则重置
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
    // 完全清理旧的引用和观察器
    itemEls.value.forEach(el => {
      if (el && resizeObserver.value) {
        resizeObserver.value.unobserve(el);
      }
    });
    itemEls.value = [];
    observedElements.value.clear();
    rowHeights.value = [];
    
    // 当数据源发生替换（非尾部追加）时，重置滚动，避免切换标签后出现顶部空白
    if (container.value) {
      container.value.scrollTop = 0;
    }
    currentScrollTop.value = 0;
    scrollTop.value = 0;
  }
  
  requestAnimationFrame(() => {
    updateItemObservers();
    updateHeights();
  });
});

// 列数变化通常意味着布局变化（窗口/容器尺寸变化），需要丢弃旧的行高并重新测量
watch(() => columnCount.value, () => {
  rowHeights.value = [];
  requestAnimationFrame(() => {
    updateItemObservers();
    updateHeights();
  });
});

// 当行范围变化：合并更新与事件发射
watch(range, (r) => {
  requestAnimationFrame(() => {
    updateItemObservers();
    updateHeights();
  });
  emitRangeChange(r);
});

// ==================== 对外暴露方法 ====================
const scrollToOffset = (offsetPx) => {
  if (!container.value) return;
  container.value.scrollTop = Math.max(0, offsetPx);
  handleScroll();
};

const scrollToIndex = (index, align = 'start') => {
  const clamped = Math.max(0, Math.min(index, props.items.length - 1));
  const row = Math.floor(clamped / columnCount.value);
  const base = rowOffsets.value[row] ?? row * averageRowHeight.value;
  let target = base;
  if (align === 'center') target = base - containerHeight.value / 2;
  if (align === 'end') target = base - containerHeight.value + (rowHeights.value[row] || props.itemSecondarySize);
  scrollToOffset(target);
};

const reset = () => {
  rowHeights.value = [];
  itemEls.value = [];
  currentScrollTop.value = 0;
  scrollTop.value = 0;
  if (container.value) container.value.scrollTop = 0;
  updateHeights();
};

defineExpose({ scrollToOffset, scrollToIndex, reset, container, range, totalHeight });
</script>

<style scoped>
.virtual-list-container {
  position: relative;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge */
}

.virtual-list-container::-webkit-scrollbar {
  display: none; /* Chrome/Safari */
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
}
</style> 