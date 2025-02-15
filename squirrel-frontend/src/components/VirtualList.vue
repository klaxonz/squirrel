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
        v-for="item in visibleItems"
        :key="item[keyField]"
        ref="items"
        class="list-item3"
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';

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
  }
});

const container = ref(null);
const items = ref([]);
const sizes = ref({});
const scrollTop = ref(0);
const heights = ref([]);
const resizeObserver = ref(null);

// 网格布局计算
const columnCount = computed(() => Math.max(1, props.gridItems));
const rowHeights = ref([]);

// 计算可见项
const visibleItems = computed(() => {
  const startRow = Math.floor(findNearestItemIndex(scrollTop.value) / columnCount.value);
  const endRow = Math.ceil(findNearestItemIndex(scrollTop.value + containerHeight.value) / columnCount.value);
  
  const startIndex = Math.max(0, (startRow - props.buffer) * columnCount.value);
  const endIndex = Math.min(
    props.items.length, 
    (endRow + props.buffer + 1) * columnCount.value
  );

  return props.items.slice(startIndex, endIndex).map((item, i) => ({
    ...item,
    _index: startIndex + i,
    _row: Math.floor((startIndex + i) / columnCount.value),
    _column: (startIndex + i) % columnCount.value
  }));
});

// 总高度计算
const totalHeight = computed(() => {
  const rowCount = Math.ceil(props.items.length / columnCount.value);
  return Array.from({ length: rowCount }).reduce((acc, _, row) => {
    return acc + (rowHeights.value[row] || props.itemSecondarySize);
  }, 0);
});

// 当前偏移量
const offset = computed(() => {
  const startRow = visibleItems.value[0]?._row || 0;
  return Array.from({ length: startRow }).reduce((acc, _, row) => {
    return acc + (rowHeights.value[row] || props.itemSecondarySize);
  }, 0);
});

// 容器高度
const containerHeight = computed(() => 
  container.value?.clientHeight || 0
);

// 获取项尺寸
const getItemSize = (index) => {
  if (typeof props.itemSize === 'function') {
    return props.itemSize(props.items[index], index);
  }
  return props.itemSize;
};

// 二分查找最近项
const findNearestItemIndex = (scrollTop) => {
  let low = 0;
  let high = props.items.length;
  let mid;
  let currentTop = 0;

  while (low < high) {
    mid = low + Math.floor((high - low) / 2);
    currentTop = heights.value[mid] || 0;
    
    if (currentTop < scrollTop) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  return Math.max(0, low - 1);
};

// 处理滚动事件
const handleScroll = () => {
  scrollTop.value = container.value.scrollTop;
  updateHeights();
};

// 更新高度缓存
const updateHeights = () => {
  requestAnimationFrame(() => {
    const newRowHeights = [...rowHeights.value];
    items.value.forEach((el, i) => {
      const index = visibleItems.value[i]._index;
      const row = Math.floor(index / columnCount.value);
      const height = el.clientHeight;
      
      if (!newRowHeights[row] || height > newRowHeights[row]) {
        newRowHeights[row] = height;
      }
    });
    rowHeights.value = newRowHeights;
  });
};

// 初始化高度缓存
const initHeights = () => {
  heights.value = props.items.map((_, i) => getItemSize(i));
};

// 观察尺寸变化
const observeResize = () => {
  if (resizeObserver.value) return;

  resizeObserver.value = new ResizeObserver(entries => {
    entries.forEach(entry => {
      if (entry.target === container.value) {
        updateHeights();
      } else {
        const index = [...items.value].indexOf(entry.target);
        if (index > -1) {
          const itemIndex = visibleItems.value[index]._index;
          heights.value[itemIndex] = entry.contentRect.height;
        }
      }
    });
  });

  items.value.forEach(el => resizeObserver.value.observe(el));
  if (container.value) {
    resizeObserver.value.observe(container.value);
  }
};

// 添加样式计算
const itemStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: `repeat(auto-fill, minmax(${props.itemSecondarySize}px, 1fr))`,
  gap: '8px',
  width: '100%',
  padding: '0 8px'
}));

watch(() => props.items, () => {
  initHeights();
  requestAnimationFrame(updateHeights);
}, { deep: true });

onMounted(() => {
  initHeights();
  observeResize();
});

onUnmounted(() => {
  if (resizeObserver.value) {
    resizeObserver.value.disconnect();
  }
});
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

.list-item3 {
  will-change: transform;
}
</style> 