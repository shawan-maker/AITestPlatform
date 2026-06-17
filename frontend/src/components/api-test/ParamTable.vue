<template>
  <div class="param-table-wrapper">
    <el-table :data="tableData" border size="default" empty-text="">
      <el-table-column
        v-for="(col, colIdx) in columns"
        :key="col.prop"
        :prop="col.prop"
        :label="col.label"
        :min-width="col.minWidth || 150"
      >
        <template #default="{ row, $index }">
          <template v-if="$index < tableData.length - 1">
            <el-select v-if="col.type === 'select'" v-model="row[col.prop]" size="default" style="width:100%">
              <el-option v-for="opt in col.options" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
            <el-input v-else v-model="row[col.prop]" size="default" :placeholder="col.placeholder || ''" />
          </template>
          <span v-else-if="colIdx === 0" class="add-param-link" @click="addRow">{{ addLabel }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="t('page.apiCases.operation')" width="60" align="center">
        <template #default="{ $index }">
          <el-button v-if="$index < tableData.length - 1" link type="danger" size="default" :icon="Close" @click="removeRow($index)" />
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Close } from '@element-plus/icons-vue'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  columns: {
    type: Array,
    default: () => [
      { prop: 'name', label: '参数名', minWidth: 150 },
      { prop: 'value', label: '参数值', minWidth: 200 },
      { prop: 'desc', label: '说明', minWidth: 140 },
    ],
  },
  addLabel: { type: String, default: '' },
  emptyRow: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue'])

const tableData = computed(() => {
  var data = props.modelValue || []
  // 确保最后有一行空行用于添加
  if (!data.length || Object.values(data[data.length - 1]).some(function (v) { return v !== '' && v !== undefined && v !== null })) {
    var empty = props.emptyRow || {}
    var row = {}
    props.columns.forEach(function (c) { row[c.prop] = empty[c.prop] || '' })
    return [...data, row]
  }
  return data
})

function addRow() {
  var empty = props.emptyRow || {}
  var row = {}
  props.columns.forEach(function (c) { row[c.prop] = empty[c.prop] || '' })
  var newData = [...props.modelValue, row]
  emit('update:modelValue', newData)
}

function removeRow(index) {
  var newData = props.modelValue.filter(function (_, i) { return i !== index })
  emit('update:modelValue', newData)
}
</script>

<style scoped lang="scss">
.param-table-wrapper {
  padding: 0 0 8px;
}

.add-param-link {
  color: var(--el-color-primary);
  cursor: pointer;
  font-size: var(--el-font-size-base);

  &:hover {
    text-decoration: underline;
  }
}
</style>
