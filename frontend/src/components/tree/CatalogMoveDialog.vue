<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle || t('page.apiCases.moveCatalog')"
    width="420px"
    destroy-on-close
    @closed="onClosed"
  >
    <p class="move-hint">{{ hint || t('page.apiCases.moveCatalogPrompt') }}</p>
    <el-tree-select
      v-model="targetParentId"
      :data="treeOptions"
      :props="{ label: 'name', value: 'id', children: 'children' }"
      check-strictly
      filterable
      clearable
      :placeholder="t('page.apiCases.moveCatalogPrompt')"
      style="width: 100%"
    />
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="confirm">{{ t('common.confirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  catalogNodes: { type: Array, default: () => [] },
  excludeCatalogId: { type: Number, default: null },
  hint: { type: String, default: '' },
  dialogTitle: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const { t } = useI18n()
const targetParentId = ref(null)

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

function filterExcluded(nodes, excludeId) {
  if (!excludeId) return nodes
  const result = []
  for (const node of nodes) {
    if (node.id === excludeId) continue
    const children = node.children?.length ? filterExcluded(node.children, excludeId) : []
    result.push({ ...node, children })
  }
  return result
}

const treeOptions = computed(() => filterExcluded(props.catalogNodes, props.excludeCatalogId))

watch(
  () => props.modelValue,
  (open) => {
    if (open) targetParentId.value = null
  },
)

function onClosed() {
  targetParentId.value = null
}

function confirm() {
  emit('confirm', targetParentId.value ?? null)
}
</script>

<style scoped>
.move-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
