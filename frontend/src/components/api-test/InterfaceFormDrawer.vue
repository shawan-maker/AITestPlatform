<template>
  <!-- v2-Q1: 白名单仅3字段：name(接口名称)、method、path -->
  <el-drawer v-model="visible" :title="isEdit ? t('page.apiCases.editInterface') : t('page.apiCases.createInterface')" size="420px">
    <el-form :model="form" label-width="100px">
      <el-form-item :label="t('page.apiCases.interfaceName') || '接口名称'" required>
        <el-input v-model="form.name" placeholder="请输入接口名称" maxlength="255" show-word-limit />
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
import { createInterface, updateInterface } from '@/api/apiTest'
import { HTTP_METHODS } from '@/utils/constants'
import { useProjectScope } from '@/composables/useProjectScope'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  catalogId: { type: Number, default: null },
  interfaceData: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])
const { t } = useI18n()
const { withProjectParams } = useProjectScope()

const saving = ref(false)
// v2-Q1: 表单仅3个字段 — name(映射到后端summary)、method、path
const form = reactive({ name: '', method: 'GET', path: '' })

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.interfaceData?.id)

watch(() => props.modelValue, (open) => {
  if (!open) return
  if (props.interfaceData) {
    // v2-Q1: name 映射到 summary 字段
    form.name = props.interfaceData.summary || props.interfaceData.name || ''
    form.method = props.interfaceData.method ?? 'GET'
    form.path = props.interfaceData.path ?? ''
  } else {
    form.name = ''
    form.method = 'GET'
    form.path = ''
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
  var catId = props.catalogId
  if (!catId) {
    ElMessage.warning(t('page.apiCases.selectCatalog'))
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      // v2-Q1: PATCH仅传name/method/path三字段
      await updateInterface(props.interfaceData.id, {
        name: form.name,
        method: form.method,
        path: form.path,
      })
    } else {
      const params = withProjectParams()
      // 创建时仍需要完整参数（summary从name传入）
      await createInterface(
        { ...form, summary: form.name.trim(), catalog_id: catId },
        params
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
