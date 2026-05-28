<template>
  <el-dialog :model-value="modelValue" :title="t('page.agent.saveDialog')" width="480px" @update:model-value="$emit('update:modelValue', $event)">
    <el-form label-width="100px">
      <el-form-item :label="t('page.functional.catalog')" required>
        <el-select v-model="catalogId" filterable style="width: 100%">
          <el-option v-for="c in flatCatalogs" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.agent.selectedCases')">
        <span>{{ selectedCount }} / {{ caseCount }}</span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" :disabled="!catalogId" @click="submit">{{ t('common.save') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  catalogs: { type: Array, default: () => [] },
  caseCount: { type: Number, default: 0 },
  defaultIndexes: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])

const { t } = useI18n()
const catalogId = ref(null)

const flatCatalogs = computed(() => {
  const out = []
  function walk(nodes) {
    nodes.forEach((n) => { out.push(n); if (n.children) walk(n.children) })
  }
  walk(props.catalogs)
  return out
})

const selectedCount = computed(() => props.defaultIndexes.length)

watch(
  () => props.modelValue,
  (open) => {
    if (open) catalogId.value = flatCatalogs.value[0]?.id ?? null
  },
)

function submit() {
  if (!catalogId.value || !props.defaultIndexes.length) return
  emit('submit', {
    catalog_id: catalogId.value,
    case_indexes: [...props.defaultIndexes],
  })
}
</script>
