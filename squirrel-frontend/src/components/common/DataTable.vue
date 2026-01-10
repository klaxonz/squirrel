<template>
  <Card class="overflow-hidden">
    <!-- 表头 -->
    <div
      v-if="$slots.header"
      class="px-4 py-2.5 border-b border-border-primary flex items-center justify-between"
    >
      <slot name="header" />
    </div>

    <!-- 表格容器 -->
    <div class="overflow-x-auto scrollbar">
      <table class="w-full text-sm">
        <!-- 表头 -->
        <thead>
          <tr class="text-xs text-text-tertiary border-b border-border-primary">
            <th
              v-for="column in columns"
              :key="column.key"
              :class="[
                'text-left px-4 py-2 font-medium',
                column.align === 'right' && 'text-right',
                column.align === 'center' && 'text-center'
              ]"
            >
              {{ column.label }}
            </th>
          </tr>
        </thead>

        <!-- 表体 -->
        <tbody>
          <tr
            v-for="(row, index) in data"
            :key="getRowKey(row, index)"
            class="border-b border-border-primary hover:bg-bg-elevated/50 transition-colors"
          >
            <td
              v-for="column in columns"
              :key="column.key"
              :class="[
                'px-4 py-2.5',
                column.align === 'right' && 'text-right',
                column.align === 'center' && 'text-center',
                column.class && column.class
              ]"
            >
              <slot
                :name="`column-${column.key}`"
                :row="row"
                :value="getCellValue(row, column)"
                :index="index"
              >
                {{ formatCellValue(getCellValue(row, column), column) }}
              </slot>
            </td>
          </tr>

          <!-- 空状态 -->
          <tr v-if="!data || data.length === 0">
            <td
              :colspan="columns.length"
              class="text-center text-text-muted py-8 text-sm"
            >
              <slot name="empty">
                暂无数据
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </Card>
</template>

<script setup>
const props = defineProps({
  columns: {
    type: Array,
    required: true,
    validator: (columns) => {
      return columns.every(col =>
        col.key && col.label &&
        ['left', 'center', 'right'].includes(col.align || 'left')
      )
    }
  },
  data: {
    type: Array,
    default: () => []
  },
  rowKey: {
    type: String,
    default: 'id'
  }
})

const getRowKey = (row, index) => {
  return row[props.rowKey] || index
}

const getCellValue = (row, column) => {
  if (typeof column.key === 'function') {
    return column.key(row)
  }
  return row[column.key]
}

const formatCellValue = (value, column) => {
  if (column.formatter) {
    return column.formatter(value)
  }
  return value || '-'
}
</script>
