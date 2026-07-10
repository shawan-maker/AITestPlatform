<template>
  <el-dialog :close-on-click-modal="false" v-model="visible" :title="t('page.env.variables.move')" width="520px">
    <el-form label-width="auto">
      <el-form-item :label="t('page.env.variables.targetCatalog')">
        <el-tree-select
          v-model="targetCatalogId"
          :data="treeData"
          :props="{ label: 'name', value: 'id', children: 'children' }"
          :render-after-expand="false"
          check-strictly
          :placeholder="t('page.env.variables.rootCatalog')"
          clearable
          style="width: 100%"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.confirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { updateEnvironment } from '@/api/environment'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  environmentId: { type: Number, default: null },
  envName: { type: String, default: '' },
  currentCatalogId: { type: Number, default: null },
  catalogTree: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'moved'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const targetCatalogId = ref(null)
const loading = ref(false)

const treeData = computed(() => {
  const root = { id: 0, name: t('page.env.variables.rootCatalog'), children: props.catalogTree }
  return [root]
})

watch(visible, (v) => {
  if (v) {
    targetCatalogId.value = props.currentCatalogId ?? 0
  }
})

async function submit() {
  if (targetCatalogId.value === (props.currentCatalogId ?? 0)) {
    visible.value = false
    return
  }
  loading.value = true
  try {
    await updateEnvironment(props.environmentId, {
      catalog_id: targetCatalogId.value || 0,
    })
    ElMessage.success(t('page.env.variables.moveSuccess'))
    emit('moved')
    visible.value = false
  } finally {
    loading.value = false
  }
}
</script>
