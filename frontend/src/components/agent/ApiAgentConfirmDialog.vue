<template>
  <el-dialog :close-on-click-modal="false" :model-value="modelValue" :title="t('page.agent.confirmPreRun')" width="520px" @update:model-value="$emit('update:modelValue', $event)">
    <el-form label-width="auto">
      <el-form-item v-if="!interfaceId" :label="t('page.functional.catalog')" required>
        <el-select v-model="catalogId" filterable style="width: 100%">
          <el-option v-for="c in flatCatalogs" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.apiCases.selectEnv')" required>
        <EnvironmentSelect v-model="environmentId" />
      </el-form-item>
      <el-form-item :label="t('page.agent.selectedCases')">
        <span>{{ defaultIndexes.length }}</span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" :disabled="!canSubmit" @click="submit">{{ t('common.confirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  catalogs: { type: Array, default: () => [] },
  defaultIndexes: { type: Array, default: () => [] },
  interfaceId: { type: Number, default: null },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])

const { t } = useI18n()
const catalogId = ref(null)
const environmentId = ref(null)

const flatCatalogs = computed(() => {
  const out = []
  function walk(nodes) {
    nodes.forEach((n) => { out.push(n); if (n.children) walk(n.children) })
  }
  walk(props.catalogs)
  return out
})

const canSubmit = computed(() => {
  if (!environmentId.value || !props.defaultIndexes.length) return false
  if (props.interfaceId) return true
  return Boolean(catalogId.value)
})

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      catalogId.value = flatCatalogs.value[0]?.id ?? null
      environmentId.value = null
    }
  },
)

function submit() {
  if (!canSubmit.value) return
  emit('submit', {
    environment_id: environmentId.value,
    catalog_id: props.interfaceId ? undefined : catalogId.value,
    interface_id: props.interfaceId || undefined,
    selected_indexes: [...props.defaultIndexes],
  })
}
</script>
