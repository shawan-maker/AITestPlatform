<template>
  <el-tree-select
    v-model="innerValue"
    :data="treeData"
    :props="{ label: 'name', value: 'id', children: 'children' }"
    :placeholder="placeholder || t('page.functional.catalog')"
    check-strictly
    filterable
    clearable
    style="width: 100%"
  />
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getApiCatalogTree } from '@/api/apiTest'
import { useProjectScope } from '@/composables/useProjectScope'

const props = defineProps({
  modelValue: { type: [Number, null], default: null },
  placeholder: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()
const { withProjectParams } = useProjectScope()

const treeData = ref([])

const innerValue = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

async function loadTree() {
  const params = withProjectParams()
  if (!params) {
    treeData.value = []
    return
  }
  const res = await getApiCatalogTree(params)
  treeData.value = res.data.data?.items ?? res.data.data ?? []
}

onMounted(loadTree)
watch(() => withProjectParams()?.project_id, loadTree)
</script>
