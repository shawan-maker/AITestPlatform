<template>
  <!-- v2-Q1: 白名单字段：name(接口名称)、catalog(接口目录)、method、path -->
  <el-drawer v-model="visible" :title="isEdit ? t('page.apiCases.editInterface') : t('page.apiCases.createInterface')" size="33%">
    <el-form :model="form" label-width="100px">
      <el-form-item :label="t('page.apiCases.interfaceName')" required>
        <el-input v-model="form.name" placeholder="请输入接口名称" maxlength="255" show-word-limit />
      </el-form-item>
      <el-form-item :label="t('page.apiCases.interfaceCatalog')" v-if="!isEdit">
        <el-tree-select
          v-model="form.catalogId"
          :data="catalogOptions"
          :props="{ label: 'name', value: 'id', children: 'children' }"
          placeholder="请选择接口目录"
          check-strictly
          :render-after-expand="false"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item :label="t('page.apiCases.method')" required>
        <el-select v-model="form.method" style="width: 100%">
          <el-option v-for="m in HTTP_METHODS" :key="m" :label="m" :value="m" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.apiCases.path')" required>
        <el-input v-model="form.path" placeholder="/api/v1/example" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="saving" @click="submit">{{ t('common.save') }}</el-button>
    </template>
  </el-drawer>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { createInterface, updateInterface, getApiCatalogTree } from '@/api/apiTest'
import { HTTP_METHODS } from '@/utils/constants'
import { useProjectScope } from '@/composables/useProjectScope'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  catalogId: { type: Number, default: null },
  interfaceData: { type: Object, default: null },
  isCopy: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'saved'])
const { t } = useI18n()
const { withProjectParams } = useProjectScope()

const saving = ref(false)
const catalogOptions = ref([])
const form = reactive({ name: '', method: 'GET', path: '', catalogId: null })

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.interfaceData?.id && !props.isCopy)

async function loadCatalogTree() {
  var params = withProjectParams()
  if (!params) return
  try {
    var res = await getApiCatalogTree(params)
    catalogOptions.value = res.data.data?.items ?? res.data.data ?? []
  } catch (e) {
    console.error('加载目录树失败:', e)
  }
}

watch(() => props.modelValue, (open) => {
  if (!open) return
  loadCatalogTree()
  if (props.interfaceData && !props.isCopy) {
    form.name = props.interfaceData.summary || props.interfaceData.name || ''
    form.method = props.interfaceData.method ?? 'GET'
    form.path = props.interfaceData.path ?? ''
    form.catalogId = props.interfaceData.catalog_id ?? props.catalogId
  } else if (props.interfaceData && props.isCopy) {
    var origName = props.interfaceData.summary || props.interfaceData.name || ''
    form.name = origName ? origName + '_copy01' : ''
    form.method = props.interfaceData.method ?? 'GET'
    form.path = props.interfaceData.path ?? ''
    form.catalogId = props.interfaceData.catalog_id ?? props.catalogId
  } else {
    form.name = ''
    form.method = 'GET'
    form.path = ''
    form.catalogId = props.catalogId
  }
})

async function submit() {
  if (!form.name?.trim()) {
    ElMessage.warning(t('page.apiCases.interfaceName') + t('validation.required'))
    return
  }
  if (!form.path?.trim()) {
    ElMessage.warning(t('page.apiCases.path') + ' ' + t('validation.required'))
    return
  }
  var catId = isEdit.value ? props.catalogId : form.catalogId
  if (!catId) {
    ElMessage.warning(t('page.apiCases.selectCatalog'))
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await updateInterface(props.interfaceData.id, {
        name: form.name,
        method: form.method,
        path: form.path,
      })
    } else {
      const projParams = withProjectParams() || {}
      await createInterface(
        { name: form.name, method: form.method, path: form.path, summary: form.name.trim(), catalog_id: catId, ...projParams }
      )
    }
    ElMessage.success(t('common.saved'))
    emit('saved')
    visible.value = false
  } finally {
    saving.value = false
  }
}
</script>
