<template>
  <el-select
    :model-value="modelValue"
    filterable
    clearable
    :placeholder="t('page.functional.selectTargetCatalog')"
    style="width: 100%"
    @change="$emit('update:modelValue', $event)"
  >
    <el-option
      v-for="c in flatNodes"
      :key="c.id"
      :label="c.name"
      :value="c.id"
    />
  </el-select>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  catalogNodes: { type: Array, default: () => [] },
  modelValue: { type: [Number, String, null], default: null },
})

defineEmits(['update:modelValue'])
const { t } = useI18n()

const flatNodes = ref([])

function walk(nodes) {
  nodes.forEach((n) => {
    flatNodes.value.push(n)
    if (n.children?.length) walk(n.children)
  })
}

watch(
  () => props.catalogNodes,
  (val) => {
    flatNodes.value = []
    if (val?.length) walk(val)
  },
  { immediate: true },
)
</script>
